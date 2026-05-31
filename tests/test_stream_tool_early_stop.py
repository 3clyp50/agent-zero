import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import models
from helpers import extract_tools
from helpers import litellm_transport
<<<<<<< Updated upstream
=======


@pytest.fixture(autouse=True)
def _clear_transport_capability_cache():
    litellm_transport.clear_transport_capability_cache()
>>>>>>> Stashed changes


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
<<<<<<< Updated upstream
=======
            {"type": "response.created"},
>>>>>>> Stashed changes
            _response_event(
                '{"tool_name":"response","tool_args":{"text":"hello"}} trailing text'
            ),
            _response_event(" unreachable"),
        ]
    )

    async def fake_aresponses(*args, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["input"] == ""
<<<<<<< Updated upstream
        assert kwargs["store"] is False
=======
        assert kwargs["store"] is True
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    assert stream.index == 1
=======
    assert stream.index == 2
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
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
=======
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
    response, reasoning = await wrapper.unified_call(
        messages=[],
        response_callback=response_callback,
    )

    assert response == "fallback"
    assert reasoning == ""
    assert calls == ["responses", "chat", "chat"]


@pytest.mark.asyncio
async def test_unified_call_preserves_cache_control_with_chat_for_non_native_responses(
    monkeypatch,
):
    calls: list[str] = []

    async def fake_aresponses(*args, **kwargs):
        calls.append("responses")
        raise AssertionError("cache_control should keep Anthropic-family calls on chat")

    async def fake_acompletion(*args, **kwargs):
        calls.append("chat")
        assert kwargs["stream"] is True
        assert kwargs["messages"][0]["cache_control"] == {"type": "ephemeral"}
        assert kwargs["messages"][-1]["cache_control"] == {"type": "ephemeral"}
        assert "drop_params" not in kwargs
        return _AsyncChunkStream([_chunk("cached")])

    async def fake_rate_limiter(*args, **kwargs):
        return None

    monkeypatch.setattr(litellm_transport, "aresponses", fake_aresponses)
    monkeypatch.setattr(litellm_transport, "acompletion", fake_acompletion)
    monkeypatch.setattr(models, "apply_rate_limiter", fake_rate_limiter)

    wrapper = models.LiteLLMChatWrapper(
        model="claude-sonnet-4-5",
        provider="anthropic",
        model_config=None,
    )

    async def response_callback(chunk: str, full: str):
        return None

    response, reasoning = await wrapper.unified_call(
        messages=[
            SystemMessage(content="static instructions"),
            HumanMessage(content="question"),
            AIMessage(content="previous answer"),
        ],
        response_callback=response_callback,
        explicit_caching=True,
    )

    assert response == "cached"
    assert reasoning == ""
    assert calls == ["chat"]

>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
    assert request["store"] is False
=======
    assert request["store"] is True
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
    assert request["reasoning"] == {"effort": "high"}
=======
    assert request["reasoning"] == {"effort": "none"}
>>>>>>> Stashed changes
    assert "tools" not in request
    assert "tool_choice" not in request
    assert "parallel_tool_calls" not in request

<<<<<<< Updated upstream
=======
    request = litellm_transport.ResponsesTransport.from_chat(
        [],
        {"reasoning": {"effort": "xhigh"}},
    )

    assert request["reasoning"] == {"effort": "xhigh"}

    request = litellm_transport.ResponsesTransport.from_chat(
        [],
        {"reasoning_effort": "off"},
    )

    assert "reasoning" not in request


def test_responses_request_adds_openai_prompt_cache_key_for_static_prefix():
    request = litellm_transport.ResponsesTransport.from_chat(
        [
            {"role": "system", "content": "stable system prompt"},
            {"role": "user", "content": "dynamic question"},
        ],
        {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup",
                        "description": "Search",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        },
        model="openai/gpt-5.4",
    )

    assert request["prompt_cache_key"].startswith("a0-")
    assert len(request["prompt_cache_key"]) == 35
    assert "stable system prompt" not in request["prompt_cache_key"]

    request_again = litellm_transport.ResponsesTransport.from_chat(
        [
            {"role": "system", "content": "stable system prompt"},
            {"role": "user", "content": "different dynamic question"},
        ],
        {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup",
                        "description": "Search",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        },
        model="openai/gpt-5.4",
    )

    assert request_again["prompt_cache_key"] == request["prompt_cache_key"]


def test_responses_request_respects_explicit_prompt_cache_and_retention():
    request = litellm_transport.ResponsesTransport.from_chat(
        [{"role": "system", "content": "stable system prompt"}],
        {
            "prompt_cache_key": "user-provided-key",
            "prompt_cache_retention": "24h",
            "extra_body": {"prompt_cache_retention": "in_memory"},
        },
        model="openai/gpt-5.4",
    )

    assert request["prompt_cache_key"] == "user-provided-key"
    assert "prompt_cache_retention" not in request
    assert request["extra_body"]["prompt_cache_retention"] == "in_memory"


def test_responses_request_does_not_add_openai_cache_key_to_custom_api_base():
    request = litellm_transport.ResponsesTransport.from_chat(
        [{"role": "system", "content": "stable system prompt"}],
        {"api_base": "https://llm.agent-zero.ai/v1"},
        model="openai/gpt-5.4",
    )

    assert "prompt_cache_key" not in request

>>>>>>> Stashed changes

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


<<<<<<< Updated upstream
=======
def test_cache_control_policy_keeps_native_responses_first():
    messages = [
        {
            "role": "system",
            "content": "static instructions",
            "cache_control": {"type": "ephemeral"},
        }
    ]

    openai_policy = litellm_transport.TransportPolicy.from_request(
        "openai/gpt-5.4",
        {},
        messages=messages,
    )
    anthropic_policy = litellm_transport.TransportPolicy.from_request(
        "anthropic/claude-sonnet-4-5",
        {},
        messages=messages,
    )

    assert openai_policy.mode is litellm_transport.TransportMode.RESPONSES
    assert anthropic_policy.mode is litellm_transport.TransportMode.CHAT_COMPLETIONS


>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
def test_responses_stream_parser_accumulates_function_call_arguments():
    parser = litellm_transport.ResponsesEventParser()

    assert parser.parse(
        {
            "type": "response.output_item.added",
            "output_index": 0,
            "item": {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_1",
                "name": "lookup",
                "arguments": "",
            },
        }
    ) == {"reasoning_delta": "", "response_delta": ""}
    assert parser.parse(
        {
            "type": "response.function_call_arguments.delta",
            "item_id": "fc_1",
            "output_index": 0,
            "delta": '{"q":',
        }
    ) == {"reasoning_delta": "", "response_delta": ""}

    parsed = parser.parse(
        {
            "type": "response.function_call_arguments.done",
            "item_id": "fc_1",
            "output_index": 0,
            "name": "lookup",
            "arguments": '{"q":"a0"}',
        }
    )

    assert extract_tools.json_parse_dirty(parsed["response_delta"]) == {
        "tool_name": "lookup",
        "tool_args": {"q": "a0"},
    }
    assert parser.parse(
        {
            "type": "response.output_item.done",
            "output_index": 0,
            "item": {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_1",
                "name": "lookup",
                "arguments": '{"q":"a0"}',
            },
        }
    ) == {"reasoning_delta": "", "response_delta": ""}


def test_responses_stream_parser_uses_completed_response_when_no_deltas_arrive():
    parser = litellm_transport.ResponsesEventParser()

    parsed = parser.parse(
        {
            "type": "response.completed",
            "response": {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "done"}],
                    }
                ]
            },
        }
    )

    assert parsed == {"reasoning_delta": "", "response_delta": "done"}


def test_responses_stream_parser_handles_refusal_and_failed_events():
    parser = litellm_transport.ResponsesEventParser()

    assert parser.parse(
        {"type": "response.refusal.delta", "delta": "no"}
    ) == {"reasoning_delta": "", "response_delta": "no"}

    with pytest.raises(RuntimeError, match="policy"):
        parser.parse(
            {
                "type": "response.failed",
                "response": {"error": {"message": "policy"}},
            }
        )


>>>>>>> Stashed changes
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
