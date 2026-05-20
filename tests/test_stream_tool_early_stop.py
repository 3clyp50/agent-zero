import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import models
from helpers import extract_tools
from helpers import litellm_transport


def _chunk(content: str) -> dict:
    return {"choices": [{"delta": {"content": content}, "message": {}}]}


def _response_event(delta: str) -> dict:
    return {"type": "response.output_text.delta", "delta": delta}


class _AsyncChunkStream:
    def __init__(self, chunks: list[dict]):
        self._chunks = chunks
        self.index = 0
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self.index]
        self.index += 1
        return chunk

    async def aclose(self):
        self.closed = True


class _FailingAsyncChunkStream:
    def __init__(self, exc: Exception):
        self.exc = exc
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise self.exc

    async def aclose(self):
        self.closed = True


def test_extract_json_root_string_returns_canonical_snapshot():
    text = (
        'prefix {"tool_name":"response","tool_args":{"text":"brace } inside"}} '
        "trailing noise"
    )

    root = extract_tools.extract_json_root_string(text)

    assert root == '{"tool_name":"response","tool_args":{"text":"brace } inside"}}'
    assert extract_tools.json_parse_dirty(root)["tool_args"]["text"] == "brace } inside"
    assert extract_tools.extract_json_root_string(
        '{"tool_name":"response","tool_args":{"text":"missing"'
    ) is None
    assert extract_tools.extract_json_root_string('[{"tool_name":"response"}]') is None


@pytest.mark.asyncio
async def test_unified_call_stops_after_canonical_root_snapshot(monkeypatch):
    stream = _AsyncChunkStream(
        [
            _response_event(
                '{"tool_name":"response","tool_args":{"text":"hello"}} trailing text'
            ),
            _response_event(" unreachable"),
        ]
    )

    async def fake_aresponses(*args, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["input"] == ""
        assert kwargs["store"] is False
        return stream

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
    )

    seen: list[tuple[str, str]] = []

    async def response_callback(chunk: str, full: str):
        seen.append((chunk, full))
        snapshot = extract_tools.extract_json_root_string(full)
        if snapshot:
            return snapshot
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == '{"tool_name":"response","tool_args":{"text":"hello"}}'
    assert reasoning == ""
    assert stream.index == 1
    assert stream.closed is True
    assert len(seen) == 1
    assert seen[0][1] == '{"tool_name":"response","tool_args":{"text":"hello"}} trailing text'


@pytest.mark.asyncio
async def test_unified_call_closes_responses_stream_when_callback_raises(monkeypatch):
    stream = _AsyncChunkStream([_response_event("interrupt me")])

    class ExpectedIntervention(Exception):
        pass

    async def fake_aresponses(*args, **kwargs):
        assert kwargs["stream"] is True
        return stream

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
    )

    async def response_callback(chunk: str, full: str):
        raise ExpectedIntervention()

    with pytest.raises(ExpectedIntervention):
        await wrapper.unified_call(
            messages=[],
            response_callback=response_callback,
        )

    assert stream.closed is True


@pytest.mark.asyncio
async def test_chat_completions_escape_hatch_still_uses_acompletion(monkeypatch):
    stream = _AsyncChunkStream([_chunk("hello")])
    calls: list[str] = []

    async def fake_acompletion(*args, **kwargs):
        calls.append("chat")
        assert kwargs["stream"] is True
        assert "a0_api_mode" not in kwargs
        return stream

    async def fake_aresponses(*args, **kwargs):
        raise AssertionError("Responses path should not be used")

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="test-model",
        provider="openai",
        model_config=None,
        a0_api_mode="chat_completions",
    )

    async def response_callback(chunk: str, full: str):
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == "hello"
    assert reasoning == ""
    assert calls == ["chat"]


@pytest.mark.asyncio
async def test_unified_call_retries_responses_with_high_reasoning(monkeypatch):
    validation_error = ValueError(
        "1 validation error for ResponseCreatedEvent\n"
        "response.reasoning.effort\n"
        "Input should be 'minimal', 'low', 'medium' or 'high' "
        "[type=literal_error, input_value='none', input_type=str]"
    )
    failing_stream = _FailingAsyncChunkStream(validation_error)
    working_stream = _AsyncChunkStream([_response_event("ok")])
    calls: list[dict] = []

    async def fake_aresponses(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return failing_stream
        return working_stream

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="gpt-5.4",
        provider="openai",
        model_config=None,
    )

    async def response_callback(chunk: str, full: str):
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == "ok"
    assert reasoning == ""
    assert failing_stream.closed is True
    assert len(calls) == 2
    assert "reasoning" not in calls[0]
    assert calls[1]["reasoning"] == {"effort": "high"}


@pytest.mark.asyncio
async def test_unified_call_falls_back_to_chat_when_responses_endpoint_missing(
    monkeypatch,
):
    calls: list[str] = []

    async def fake_aresponses(*args, **kwargs):
        calls.append("responses")
        raise RuntimeError(
            "Client error '404 Not Found' for url "
            "'https://llm.agent-zero.ai/v1/responses'"
        )

    async def fake_acompletion(*args, **kwargs):
        calls.append("chat")
        assert kwargs["stream"] is True
        assert kwargs["drop_params"] is True
        assert "tool_choice" not in kwargs
        assert "parallel_tool_calls" not in kwargs
        return _AsyncChunkStream([_chunk("fallback")])

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="claude-opus-4.7",
        provider="openai",
        model_config=None,
        tool_choice="auto",
        parallel_tool_calls=True,
    )

    async def response_callback(chunk: str, full: str):
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == "fallback"
    assert reasoning == ""
    assert calls == ["responses", "chat"]


def test_responses_request_translates_messages_and_params():
    messages = [
        {"role": "system", "content": "You are precise."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Inspect this."},
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.test/a.png"},
                },
            ],
        },
        {
            "role": "assistant",
            "content": "empty",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": '{"q":"a0"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "done"},
    ]
    kwargs = {
        "max_tokens": 42,
        "reasoning_effort": "high",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "schema": {"type": "object"},
                "strict": True,
            },
        },
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Search",
                    "parameters": {"type": "object"},
                    "strict": True,
                },
            }
        ],
    }

    request = litellm_transport.ResponsesTransport.from_chat(messages, kwargs)

    assert "instructions" not in request
    assert request["store"] is False
    assert request["max_output_tokens"] == 42
    assert request["reasoning"] == {"effort": "high"}
    assert request["text"] == {
        "format": {
            "type": "json_schema",
            "name": "answer",
            "schema": {"type": "object"},
            "strict": True,
        }
    }
    assert request["tools"] == [
        {
            "type": "function",
            "name": "lookup",
            "description": "Search",
            "parameters": {"type": "object"},
            "strict": True,
        }
    ]
    assert request["input"] == [
        {"role": "system", "content": "You are precise."},
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Inspect this."},
                {
                    "type": "input_image",
                    "image_url": "https://example.test/a.png",
                },
            ],
        },
        {
            "type": "function_call",
            "call_id": "call_1",
            "id": "call_1",
            "name": "lookup",
            "arguments": '{"q":"a0"}',
            "status": "completed",
        },
        {"type": "function_call_output", "call_id": "call_1", "output": "done"},
    ]


def test_responses_request_normalizes_reasoning_and_orphan_tool_choice():
    request = litellm_transport.ResponsesTransport.from_chat(
        [],
        {
            "reasoning_effort": "none",
            "tools": [],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        },
    )

    assert request["reasoning"] == {"effort": "high"}
    assert "tools" not in request
    assert "tool_choice" not in request
    assert "parallel_tool_calls" not in request


def test_chat_kwargs_strip_orphan_tool_choice_and_enable_fallback_drop_params():
    kwargs = litellm_transport.ChatCompletionsTransport.prepare_kwargs(
        {
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "max_tokens": 10,
        },
        fallback_error=RuntimeError("This model does not support Responses API"),
    )

    assert kwargs["max_tokens"] == 10
    assert kwargs["drop_params"] is True
    assert "tool_choice" not in kwargs
    assert "parallel_tool_calls" not in kwargs


def test_responses_fallback_does_not_mask_rate_limits():
    exc = RuntimeError(
        "RateLimitError: 429 Too Many Requests for url "
        "https://api.openai.com/v1/responses"
    )

    policy = litellm_transport.TransportPolicy(
        mode=litellm_transport.TransportMode.RESPONSES
    )

    assert (
        policy.recover(exc, got_any_chunk=False)
        is litellm_transport.TransportRecovery.RAISE
    )


def test_responses_response_parser_extracts_text_reasoning_and_function_calls():
    text_response = {
        "output": [
            {"type": "reasoning", "summary": [{"text": "because"}]},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "answer"}],
            },
        ]
    }

    parsed = litellm_transport.ResponsesTransport.parse_response(text_response)

    assert parsed == {"response_delta": "answer", "reasoning_delta": "because"}

    tool_response = {
        "output": [
            {
                "type": "function_call",
                "name": "lookup",
                "arguments": '{"q":"a0"}',
            }
        ]
    }

    parsed_tool = litellm_transport.ResponsesTransport.parse_response(tool_response)

    assert extract_tools.json_parse_dirty(parsed_tool["response_delta"]) == {
        "tool_name": "lookup",
        "tool_args": {"q": "a0"},
    }


def test_responses_response_parser_groups_parallel_function_calls():
    response = {
        "output": [
            {
                "type": "function_call",
                "name": "lookup",
                "arguments": '{"q":"a0"}',
            },
            {
                "type": "function_call",
                "name": "rank",
                "arguments": '{"limit":2}',
            },
        ]
    }

    parsed = litellm_transport.ResponsesTransport.parse_response(response)

    assert extract_tools.json_parse_dirty(parsed["response_delta"]) == {
        "tool_name": "parallel_tool_calls",
        "tool_args": {
            "calls": [
                {"tool_name": "lookup", "tool_args": {"q": "a0"}},
                {"tool_name": "rank", "tool_args": {"limit": 2}},
            ]
        },
    }
