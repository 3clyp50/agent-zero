from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import inspect
import json
from typing import Any, AsyncIterator, Iterator, Optional

from litellm import acompletion, aresponses, completion, responses

from helpers import images


ChatChunk = dict[str, str]


class TransportMode(Enum):
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"


class TransportRecovery(Enum):
    RAISE = "raise"
    RETRY_RESPONSES = "retry_responses"
    FALLBACK_TO_CHAT = "fallback_to_chat"


CHAT_COMPLETIONS_ALIASES = {
    "chat",
    "chat_completion",
    "chat_completions",
    "completion",
    "completions",
}
RESPONSES_ALIASES = {"", "auto", "default", "response", "responses", "responses_api"}
RESPONSES_REASONING_EFFORTS = {"minimal", "low", "medium", "high"}
RESPONSES_REASONING_FALLBACK_EFFORT = "high"
NO_REASONING_EFFORT_ALIASES = {"", "0", "false", "none", "no", "off", "disabled"}


@dataclass
class TransportPolicy:
    mode: TransportMode
    allow_fallback: bool = True
    retried_reasoning: bool = False
    fallback_error: Exception | None = None

    @classmethod
    def from_kwargs(cls, kwargs: dict[str, Any]) -> "TransportPolicy":
        mode = cls._pop_mode(kwargs)
        allow_fallback = _coerce_bool(
            kwargs.pop("a0_responses_fallback", True), default=True
        )
        return cls(mode=mode, allow_fallback=allow_fallback)

    @staticmethod
    def _pop_mode(kwargs: dict[str, Any]) -> TransportMode:
        value = str(kwargs.pop("a0_api_mode", "responses") or "").lower().strip()
        if value in CHAT_COMPLETIONS_ALIASES:
            return TransportMode.CHAT_COMPLETIONS
        if value in RESPONSES_ALIASES:
            return TransportMode.RESPONSES
        return TransportMode.RESPONSES

    @property
    def using_responses(self) -> bool:
        return self.mode is TransportMode.RESPONSES

    def recover(self, exc: Exception, *, got_any_chunk: bool) -> TransportRecovery:
        if not self.using_responses or got_any_chunk:
            return TransportRecovery.RAISE
        if not self.retried_reasoning and _is_responses_reasoning_effort_error(exc):
            self.retried_reasoning = True
            return TransportRecovery.RETRY_RESPONSES
        if self.allow_fallback and _is_responses_not_supported_error(exc):
            self.mode = TransportMode.CHAT_COMPLETIONS
            self.fallback_error = exc
            return TransportRecovery.FALLBACK_TO_CHAT
        return TransportRecovery.RAISE


@dataclass
class LiteLLMTransport:
    model: str
    messages: list[dict[str, Any]]
    kwargs: dict[str, Any]
    stop: Optional[list[str]] = None
    policy: TransportPolicy = field(init=False)

    def __post_init__(self) -> None:
        self.kwargs = _without_stream_kwarg(dict(self.kwargs))
        self.policy = TransportPolicy.from_kwargs(self.kwargs)

    def complete(self) -> ChatChunk:
        while True:
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
                    return ChatCompletionsTransport.parse(
                        completion(**self._chat_request(stream=False))
                    )
                return ResponsesTransport.parse_response(
                    responses(**self._responses_request(stream=False))
                )
            except Exception as exc:
                if self._recover(exc, got_any_chunk=False):
                    continue
                raise

    async def acomplete(self) -> ChatChunk:
        while True:
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
                    return ChatCompletionsTransport.parse(
                        await acompletion(**self._chat_request(stream=False))
                    )
                return ResponsesTransport.parse_response(
                    await aresponses(**self._responses_request(stream=False))
                )
            except Exception as exc:
                if self._recover(exc, got_any_chunk=False):
                    continue
                raise

    def stream(self) -> Iterator[ChatChunk]:
        while True:
            iterator = None
            exhausted = False
            got_any_chunk = False
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
                    iterator = completion(**self._chat_request(stream=True))
                    for chunk in iterator:
                        got_any_chunk = True
                        yield ChatCompletionsTransport.parse(chunk)
                else:
                    iterator = responses(**self._responses_request(stream=True))
                    for event in iterator:
                        got_any_chunk = True
                        yield ResponsesTransport.parse_event(event)
                exhausted = True
                return
            except Exception as exc:
                if self._recover(exc, got_any_chunk=got_any_chunk):
                    continue
                raise
            finally:
                if iterator is not None and not exhausted:
                    _close_sync_stream(iterator)

    async def astream(self) -> AsyncIterator[ChatChunk]:
        while True:
            iterator = None
            exhausted = False
            got_any_chunk = False
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
                    iterator = await acompletion(**self._chat_request(stream=True))
                    async for chunk in iterator:  # type: ignore[union-attr]
                        got_any_chunk = True
                        yield ChatCompletionsTransport.parse(chunk)
                else:
                    iterator = await aresponses(**self._responses_request(stream=True))
                    async for event in iterator:  # type: ignore[union-attr]
                        got_any_chunk = True
                        yield ResponsesTransport.parse_event(event)
                exhausted = True
                return
            except Exception as exc:
                if self._recover(exc, got_any_chunk=got_any_chunk):
                    continue
                raise
            finally:
                if iterator is not None and not exhausted:
                    await _close_async_stream(iterator)

    def _recover(self, exc: Exception, *, got_any_chunk: bool) -> bool:
        recovery = self.policy.recover(exc, got_any_chunk=got_any_chunk)
        if recovery is TransportRecovery.RETRY_RESPONSES:
            self.kwargs["reasoning"] = {
                "effort": RESPONSES_REASONING_FALLBACK_EFFORT
            }
            return True
        return recovery is TransportRecovery.FALLBACK_TO_CHAT

    def _chat_request(self, *, stream: bool) -> dict[str, Any]:
        request = {
            "model": self.model,
            "messages": self.messages,
            "stream": stream,
            **ChatCompletionsTransport.prepare_kwargs(
                self.kwargs, fallback_error=self.policy.fallback_error
            ),
        }
        if self.stop is not None:
            request["stop"] = self.stop
        return request

    def _responses_request(self, *, stream: bool) -> dict[str, Any]:
        return {
            "model": self.model,
            "stream": stream,
            **ResponsesTransport.from_chat(self.messages, self.kwargs, stop=self.stop),
        }


class ChatCompletionsTransport:
    @staticmethod
    def prepare_kwargs(
        kwargs: dict[str, Any],
        fallback_error: Exception | None = None,
    ) -> dict[str, Any]:
        chat_kwargs = dict(kwargs)
        chat_kwargs.pop("a0_responses_fallback", None)
        if not _has_tools(chat_kwargs.get("tools")):
            chat_kwargs.pop("tool_choice", None)
            chat_kwargs.pop("parallel_tool_calls", None)
        if fallback_error is not None:
            chat_kwargs.setdefault("drop_params", True)
        return {key: value for key, value in chat_kwargs.items() if value is not None}

    @staticmethod
    def parse(chunk: Any) -> ChatChunk:
        choice = _first_choice(chunk)
        delta = _get_value(choice, "delta") or {}
        message = _get_value(choice, "message") or _get_value(
            _get_value(choice, "model_extra") or {}, "message"
        ) or {}
        response_delta = _get_value(delta, "content") or _get_value(
            message, "content"
        ) or ""
        reasoning_delta = _get_value(delta, "reasoning_content") or _get_value(
            message, "reasoning_content"
        ) or ""
        return {"reasoning_delta": reasoning_delta, "response_delta": response_delta}


class ResponsesTransport:
    @classmethod
    def from_chat(
        cls,
        messages: list[dict[str, Any]],
        kwargs: dict[str, Any],
        stop: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = cls.prepare_kwargs(kwargs, stop=stop)
        request["input"] = cls.input_from_messages(messages) or ""
        request.setdefault("store", False)
        return request

    @classmethod
    def prepare_kwargs(
        cls,
        kwargs: dict[str, Any],
        stop: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = dict(kwargs)
        request.pop("stop", None)

        max_completion_tokens = request.pop("max_completion_tokens", None)
        max_tokens = request.pop("max_tokens", None)
        if "max_output_tokens" not in request:
            request["max_output_tokens"] = max_completion_tokens or max_tokens

        reasoning_effort = request.pop("reasoning_effort", None)
        if "reasoning" in request:
            request["reasoning"] = cls.normalize_reasoning(request["reasoning"])
        elif reasoning_effort is not None:
            request["reasoning"] = cls.normalize_reasoning(reasoning_effort)

        response_format = request.pop("response_format", None)
        if response_format is not None:
            text_param, text_format = cls.text_from_response_format(response_format)
            if text_param is not None and "text" not in request:
                request["text"] = text_param
            if text_format is not None and "text_format" not in request:
                request["text_format"] = text_format

        functions = request.pop("functions", None)
        if functions and "tools" not in request:
            request["tools"] = [
                {"type": "function", **function}
                for function in functions
                if isinstance(function, dict)
            ]

        if "tools" in request:
            tools = cls.tools_from_chat(request["tools"])
            if _has_tools(tools):
                request["tools"] = tools
            else:
                request.pop("tools", None)

        function_call = request.pop("function_call", None)
        if function_call is not None and "tool_choice" not in request:
            request["tool_choice"] = cls.tool_choice_from_function_call(function_call)
        elif "tool_choice" in request:
            request["tool_choice"] = cls.tool_choice_from_chat(request["tool_choice"])

        if not _has_tools(request.get("tools")):
            request.pop("tool_choice", None)
            request.pop("parallel_tool_calls", None)

        _ = stop
        return {key: value for key, value in request.items() if value is not None}

    @classmethod
    def input_from_messages(
        cls, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        response_input: list[dict[str, Any]] = []

        for message in messages:
            role = str(message.get("role") or "user")
            content = message.get("content", "")

            if role == "tool":
                response_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": str(message.get("tool_call_id") or ""),
                        "output": _content_to_text(content),
                    }
                )
                continue

            tool_calls = message.get("tool_calls")
            if role == "assistant" and isinstance(tool_calls, list) and tool_calls:
                if _has_real_content(content):
                    response_input.append(
                        {
                            "role": "assistant",
                            "content": cls.content_from_chat(content, role=role),
                        }
                    )
                response_input.extend(cls.tool_calls_from_chat(tool_calls))
                continue

            response_input.append(
                {
                    "role": role
                    if role in {"user", "assistant", "system", "developer"}
                    else "user",
                    "content": cls.content_from_chat(content, role=role),
                }
            )

        return response_input

    @classmethod
    def content_from_chat(cls, content: Any, role: str = "user") -> Any:
        content = images.prepare_content(content)
        if not isinstance(content, list):
            return content
        return [
            converted
            for item in content
            if (converted := cls.content_part_from_chat(item, role=role)) is not None
        ]

    @staticmethod
    def content_part_from_chat(item: Any, role: str = "user") -> Any:
        if not isinstance(item, dict):
            return item

        item_type = item.get("type")
        if item_type in {"input_text", "output_text", "input_image", "input_file"}:
            return dict(item)
        if item_type == "text":
            return {
                "type": "output_text" if role == "assistant" else "input_text",
                "text": item.get("text", ""),
            }
        if item_type == "image_url":
            image_url = item.get("image_url")
            if isinstance(image_url, dict):
                url = image_url.get("url", "")
                detail = image_url.get("detail")
            else:
                url = image_url or ""
                detail = item.get("detail")
            result = {"type": "input_image", "image_url": url}
            if detail:
                result["detail"] = detail
            return result

        return dict(item)

    @staticmethod
    def tool_calls_from_chat(tool_calls: list[Any]) -> list[dict[str, Any]]:
        response_input: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get("function") or {}
            if not isinstance(function, dict):
                function = {}
            response_input.append(
                {
                    "type": "function_call",
                    "call_id": str(tool_call.get("id") or ""),
                    "id": str(tool_call.get("id") or ""),
                    "name": str(function.get("name") or tool_call.get("name") or ""),
                    "arguments": str(function.get("arguments") or ""),
                    "status": "completed",
                }
            )
        return response_input

    @staticmethod
    def tools_from_chat(tools: Any) -> Any:
        if not isinstance(tools, list):
            return tools
        response_tools: list[Any] = []
        for tool in tools:
            if not isinstance(tool, dict):
                response_tools.append(tool)
                continue
            if tool.get("type") == "function" and isinstance(
                tool.get("function"), dict
            ):
                function = tool["function"]
                response_tool = {
                    "type": "function",
                    "name": function.get("name", ""),
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {}),
                }
                if "strict" in function:
                    response_tool["strict"] = function["strict"]
                response_tools.append(response_tool)
            else:
                response_tools.append(dict(tool))
        return response_tools

    @staticmethod
    def tool_choice_from_function_call(function_call: Any) -> Any:
        if isinstance(function_call, str):
            return function_call
        if isinstance(function_call, dict) and function_call.get("name"):
            return {"type": "function", "name": function_call["name"]}
        return function_call

    @staticmethod
    def tool_choice_from_chat(tool_choice: Any) -> Any:
        if (
            isinstance(tool_choice, dict)
            and tool_choice.get("type") == "function"
            and isinstance(tool_choice.get("function"), dict)
        ):
            return {"type": "function", "name": tool_choice["function"].get("name", "")}
        return tool_choice

    @staticmethod
    def text_from_response_format(response_format: Any) -> tuple[Any, Any]:
        if isinstance(response_format, type):
            return None, response_format
        if not isinstance(response_format, dict):
            return response_format, None

        format_type = response_format.get("type")
        if format_type == "json_schema":
            schema = response_format.get("json_schema") or {}
            return (
                {
                    "format": {
                        "type": "json_schema",
                        "name": schema.get("name", "response_schema"),
                        "schema": schema.get("schema", {}),
                        "strict": schema.get("strict", False),
                    }
                },
                None,
            )
        if format_type:
            return {"format": {"type": format_type}}, None
        return response_format, None

    @staticmethod
    def normalize_reasoning(reasoning: Any) -> Any:
        if isinstance(reasoning, dict):
            normalized = dict(reasoning)
            normalized["effort"] = _normalize_reasoning_effort(
                normalized.get("effort")
            )
            return normalized
        if reasoning is None:
            return None
        return {"effort": _normalize_reasoning_effort(reasoning)}

    @classmethod
    def parse_response(cls, response: Any) -> ChatChunk:
        response_delta = cls.output_text(response)
        reasoning_delta = cls.reasoning_text(response)
        if not response_delta:
            response_delta = cls.function_calls_text(response)
        return {"reasoning_delta": reasoning_delta, "response_delta": response_delta}

    @classmethod
    def parse_event(cls, event: Any) -> ChatChunk:
        event_type = _get_value(event, "type") or ""
        response_delta = ""
        reasoning_delta = ""

        if event_type in {"response.output_text.delta", "response.text.delta"}:
            response_delta = str(_get_value(event, "delta") or "")
        elif event_type in {
            "response.reasoning_summary_text.delta",
            "response.reasoning_text.delta",
        }:
            reasoning_delta = str(_get_value(event, "delta") or "")
        elif event_type == "response.output_item.done":
            item = _get_value(event, "item")
            if _get_value(item, "type") == "function_call":
                response_delta = cls.function_call_text(item)
        elif event_type == "error":
            error = _get_value(event, "error")
            message = _get_value(error, "message") or error
            raise RuntimeError(str(message))

        return {"reasoning_delta": reasoning_delta, "response_delta": response_delta}

    @classmethod
    def output_text(cls, response: Any) -> str:
        output_text = _get_value(response, "output_text")
        if isinstance(output_text, str):
            return output_text

        pieces: list[str] = []
        for item in _as_list(_get_value(response, "output")):
            if _get_value(item, "type") != "message":
                continue
            for block in _as_list(_get_value(item, "content")):
                block_type = _get_value(block, "type")
                if block_type in {"output_text", "text"}:
                    text = _get_value(block, "text")
                    if isinstance(text, str):
                        pieces.append(text)
                elif block_type == "refusal":
                    refusal = _get_value(block, "refusal")
                    if isinstance(refusal, str):
                        pieces.append(refusal)
        return "".join(pieces)

    @staticmethod
    def reasoning_text(response: Any) -> str:
        pieces: list[str] = []
        for item in _as_list(_get_value(response, "output")):
            if _get_value(item, "type") != "reasoning":
                continue
            for block in _as_list(_get_value(item, "summary")):
                text = _get_value(block, "text") or _get_value(block, "reasoning")
                if isinstance(text, str):
                    pieces.append(text)
        return "".join(pieces)

    @classmethod
    def function_calls_text(cls, response: Any) -> str:
        calls = [
            cls.function_call_object(item)
            for item in _as_list(_get_value(response, "output"))
        ]
        calls = [call for call in calls if call]
        if not calls:
            return ""
        if len(calls) == 1:
            return json.dumps(calls[0])
        return json.dumps(
            {"tool_name": "parallel_tool_calls", "tool_args": {"calls": calls}}
        )

    @classmethod
    def function_call_text(cls, item: Any) -> str:
        call = cls.function_call_object(item)
        if not call:
            return ""
        return json.dumps(call)

    @staticmethod
    def function_call_object(item: Any) -> dict[str, Any]:
        if _get_value(item, "type") != "function_call":
            return {}
        name = _get_value(item, "name")
        if not name:
            return {}
        raw_arguments = _get_value(item, "arguments") or "{}"
        if isinstance(raw_arguments, str):
            try:
                args = json.loads(raw_arguments or "{}")
            except Exception:
                args = {"arguments": raw_arguments}
        elif isinstance(raw_arguments, dict):
            args = raw_arguments
        else:
            args = {"arguments": raw_arguments}
        if not isinstance(args, dict):
            args = {"arguments": args}
        return {
            "tool_name": str(name),
            "tool_args": args,
        }


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", "none"}:
            return False
    return bool(value)


def _normalize_reasoning_effort(effort: Any) -> str:
    if isinstance(effort, str):
        normalized = effort.strip().lower()
    else:
        normalized = str(effort).strip().lower() if effort is not None else ""
    if normalized in RESPONSES_REASONING_EFFORTS:
        return normalized
    if normalized in NO_REASONING_EFFORT_ALIASES:
        return RESPONSES_REASONING_FALLBACK_EFFORT
    return RESPONSES_REASONING_FALLBACK_EFFORT


def _is_responses_reasoning_effort_error(exc: Exception) -> bool:
    text = _exception_text(exc).lower()
    return (
        "response.reasoning.effort" in text
        and "minimal" in text
        and "high" in text
        and "none" in text
    )


def _is_responses_not_supported_error(exc: Exception) -> bool:
    text = _exception_text(exc).lower()
    if any(marker in text for marker in ("429", "too many requests", "rate limit")):
        return False
    if "/v1/responses" in text and any(
        marker in text for marker in ("404", "not found")
    ):
        return True
    return any(
        marker in text
        for marker in (
            "responses api",
            "does not support responses",
            "not support responses",
            "unsupportedparamserror",
            "does not support parameters",
            "no 'tools' defined while 'tool_choice' is specified",
        )
    )


def _exception_text(exc: Exception) -> str:
    parts = [exc.__class__.__name__, str(exc)]
    cause = getattr(exc, "__cause__", None)
    context = getattr(exc, "__context__", None)
    if cause is not None:
        parts.append(str(cause))
    if context is not None and context is not cause:
        parts.append(str(context))
    return "\n".join(parts)


def _close_sync_stream(stream: Any) -> None:
    for method_name in ("close", "aclose"):
        close = getattr(stream, method_name, None)
        if close is None:
            continue
        result = close()
        if inspect.isawaitable(result):
            result.close()
        return


async def _close_async_stream(stream: Any) -> None:
    for method_name in ("aclose", "close"):
        close = getattr(stream, method_name, None)
        if close is None:
            continue
        result = close()
        if inspect.isawaitable(result):
            await result
        return


def _without_stream_kwarg(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs.pop("stream", None)
    return kwargs


def _first_choice(chunk: Any) -> Any:
    choices = _get_value(chunk, "choices") or []
    return choices[0] if choices else {}


def _get_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _has_tools(tools: Any) -> bool:
    if isinstance(tools, list):
        return bool(tools)
    return bool(tools)


def _has_real_content(content: Any) -> bool:
    if content == "empty":
        return False
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return len(content) > 0
    return content is not None


def _content_to_text(content: Any) -> str:
    content = images.prepare_content(content)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    pieces.append(text)
        return "\n".join(pieces)
    return "" if content is None else str(content)
