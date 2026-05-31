from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
<<<<<<< Updated upstream
=======
import hashlib
>>>>>>> Stashed changes
import inspect
import json
from typing import Any, AsyncIterator, Iterator, Optional

<<<<<<< Updated upstream
from litellm import acompletion, aresponses, completion, responses

from helpers import images
=======
from litellm import (
    acompletion,
    adelete_responses,
    aresponses,
    completion,
    delete_responses,
    responses,
)

from helpers import images
from helpers.llm_result import LLMResult
>>>>>>> Stashed changes


ChatChunk = dict[str, str]


class TransportMode(Enum):
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"


class TransportRecovery(Enum):
    RAISE = "raise"
    RETRY_RESPONSES = "retry_responses"
<<<<<<< Updated upstream
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
=======
    RETRY_LOCAL_RESPONSES = "retry_local_responses"
    FALLBACK_TO_CHAT = "fallback_to_chat"


RESPONSES_REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
}
RESPONSES_REASONING_FALLBACK_EFFORT = "high"
NO_REASONING_EFFORT_ALIASES = {"", "0", "false", "no", "off", "disabled"}
RESPONSES_UNSUPPORTED_CACHE: set[str] = set()
RESPONSES_STATE_UNSUPPORTED_CACHE: set[str] = set()
RESPONSES_BUILTIN_UNSUPPORTED_CACHE: dict[str, set[str]] = {}
OPENAI_RESPONSES_EXTRA_BODY_PARAMS = {
    "context_management",
    "prompt_cache_retention",
}
RESPONSES_STATE_PROVIDER = "provider"
RESPONSES_STATE_LOCAL = "local"
RESPONSES_STATE_OFF = "off"
RESPONSES_STATES = {
    RESPONSES_STATE_PROVIDER,
    RESPONSES_STATE_LOCAL,
    RESPONSES_STATE_OFF,
}
>>>>>>> Stashed changes


@dataclass
class TransportPolicy:
    mode: TransportMode
<<<<<<< Updated upstream
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
=======
    retried_reasoning: bool = False
    fallback_error: Exception | None = None
    state_fallback_error: Exception | None = None
    cache_key: str = ""
    state: str = RESPONSES_STATE_PROVIDER

    @classmethod
    def from_request(
        cls,
        model: str,
        kwargs: dict[str, Any],
        messages: list[dict[str, Any]] | None = None,
    ) -> "TransportPolicy":
        _drop_legacy_transport_kwargs(kwargs)
        cache_key = _responses_cache_key(model, kwargs)
        state = _normalize_responses_state(kwargs.get("responses_state"))
        if state == RESPONSES_STATE_PROVIDER and cache_key in RESPONSES_STATE_UNSUPPORTED_CACHE:
            kwargs["responses_state"] = RESPONSES_STATE_LOCAL
            state = RESPONSES_STATE_LOCAL
        _filter_unsupported_builtin_tools(kwargs, cache_key)
        if _should_preserve_cache_control_on_chat(model, kwargs, messages or []):
            return cls(
                mode=TransportMode.CHAT_COMPLETIONS,
                cache_key=cache_key,
                state=RESPONSES_STATE_OFF,
            )
        if cache_key in RESPONSES_UNSUPPORTED_CACHE:
            return cls(
                mode=TransportMode.CHAT_COMPLETIONS,
                fallback_error=RuntimeError("Responses API previously failed"),
                cache_key=cache_key,
                state=RESPONSES_STATE_OFF,
            )
        return cls(mode=TransportMode.RESPONSES, cache_key=cache_key, state=state)
>>>>>>> Stashed changes

    @property
    def using_responses(self) -> bool:
        return self.mode is TransportMode.RESPONSES

    def recover(self, exc: Exception, *, got_any_chunk: bool) -> TransportRecovery:
        if not self.using_responses or got_any_chunk:
            return TransportRecovery.RAISE
        if not self.retried_reasoning and _is_responses_reasoning_effort_error(exc):
            self.retried_reasoning = True
            return TransportRecovery.RETRY_RESPONSES
<<<<<<< Updated upstream
        if self.allow_fallback and _is_responses_not_supported_error(exc):
            self.mode = TransportMode.CHAT_COMPLETIONS
            self.fallback_error = exc
=======
        if (
            self.state == RESPONSES_STATE_PROVIDER
            and _is_responses_state_unsupported_error(exc)
        ):
            self.state = RESPONSES_STATE_LOCAL
            self.state_fallback_error = exc
            if self.cache_key:
                RESPONSES_STATE_UNSUPPORTED_CACHE.add(self.cache_key)
            return TransportRecovery.RETRY_LOCAL_RESPONSES
        if _is_responses_not_supported_error(exc):
            self.mode = TransportMode.CHAT_COMPLETIONS
            self.fallback_error = exc
            self.state = RESPONSES_STATE_OFF
            if self.cache_key:
                RESPONSES_UNSUPPORTED_CACHE.add(self.cache_key)
>>>>>>> Stashed changes
            return TransportRecovery.FALLBACK_TO_CHAT
        return TransportRecovery.RAISE


@dataclass
class LiteLLMTransport:
    model: str
    messages: list[dict[str, Any]]
    kwargs: dict[str, Any]
    stop: Optional[list[str]] = None
    policy: TransportPolicy = field(init=False)
<<<<<<< Updated upstream

    def __post_init__(self) -> None:
        self.kwargs = _without_stream_kwarg(dict(self.kwargs))
        self.policy = TransportPolicy.from_kwargs(self.kwargs)
=======
    last_result: LLMResult | None = field(init=False, default=None)
    last_request_state: str = field(init=False, default=RESPONSES_STATE_PROVIDER)

    def __post_init__(self) -> None:
        self.kwargs = _without_stream_kwarg(dict(self.kwargs))
        self.policy = TransportPolicy.from_request(
            self.model,
            self.kwargs,
            messages=self.messages,
        )
>>>>>>> Stashed changes

    def complete(self) -> ChatChunk:
        while True:
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
<<<<<<< Updated upstream
                    return ChatCompletionsTransport.parse(
                        completion(**self._chat_request(stream=False))
                    )
                return ResponsesTransport.parse_response(
                    responses(**self._responses_request(stream=False))
                )
=======
                    parsed = ChatCompletionsTransport.parse(
                        completion(**self._chat_request(stream=False))
                    )
                    self.last_result = LLMResult.from_chat(
                        response=parsed["response_delta"],
                        reasoning=parsed["reasoning_delta"],
                        input_items=ResponsesTransport.input_from_messages(
                            self.messages
                        ),
                        provider_model_key=self.model,
                        capability=self._capability_metadata(),
                    )
                    return parsed
                request = self._responses_request(stream=False)
                raw_response = responses(**request)
                parsed = ResponsesTransport.parse_response(raw_response)
                self.last_result = self._llm_result_from_response(
                    raw_response, request
                )
                return parsed
>>>>>>> Stashed changes
            except Exception as exc:
                if self._recover(exc, got_any_chunk=False):
                    continue
                raise

    async def acomplete(self) -> ChatChunk:
        while True:
            try:
                if self.policy.mode is TransportMode.CHAT_COMPLETIONS:
<<<<<<< Updated upstream
                    return ChatCompletionsTransport.parse(
                        await acompletion(**self._chat_request(stream=False))
                    )
                return ResponsesTransport.parse_response(
                    await aresponses(**self._responses_request(stream=False))
                )
=======
                    parsed = ChatCompletionsTransport.parse(
                        await acompletion(**self._chat_request(stream=False))
                    )
                    self.last_result = LLMResult.from_chat(
                        response=parsed["response_delta"],
                        reasoning=parsed["reasoning_delta"],
                        input_items=ResponsesTransport.input_from_messages(
                            self.messages
                        ),
                        provider_model_key=self.model,
                        capability=self._capability_metadata(),
                    )
                    return parsed
                request = self._responses_request(stream=False)
                raw_response = await aresponses(**request)
                parsed = ResponsesTransport.parse_response(raw_response)
                self.last_result = self._llm_result_from_response(
                    raw_response, request
                )
                return parsed
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                        got_any_chunk = True
                        yield ChatCompletionsTransport.parse(chunk)
                else:
                    iterator = responses(**self._responses_request(stream=True))
                    for event in iterator:
                        got_any_chunk = True
                        yield ResponsesTransport.parse_event(event)
=======
                        parsed = ChatCompletionsTransport.parse(chunk)
                        if _has_chunk_delta(parsed):
                            got_any_chunk = True
                            yield parsed
                else:
                    request = self._responses_request(stream=True)
                    iterator = responses(**request)
                    parser = ResponsesEventParser()
                    for event in iterator:
                        parsed = parser.parse(event)
                        if _has_chunk_delta(parsed):
                            got_any_chunk = True
                            yield parsed
                    self.last_result = self._stream_result_from_parser(
                        parser, request
                    )
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                        got_any_chunk = True
                        yield ChatCompletionsTransport.parse(chunk)
                else:
                    iterator = await aresponses(**self._responses_request(stream=True))
                    async for event in iterator:  # type: ignore[union-attr]
                        got_any_chunk = True
                        yield ResponsesTransport.parse_event(event)
=======
                        parsed = ChatCompletionsTransport.parse(chunk)
                        if _has_chunk_delta(parsed):
                            got_any_chunk = True
                            yield parsed
                else:
                    request = self._responses_request(stream=True)
                    iterator = await aresponses(**request)
                    parser = ResponsesEventParser()
                    async for event in iterator:  # type: ignore[union-attr]
                        parsed = parser.parse(event)
                        if _has_chunk_delta(parsed):
                            got_any_chunk = True
                            yield parsed
                    self.last_result = self._stream_result_from_parser(
                        parser, request
                    )
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
        if (
            self.policy.using_responses
            and not got_any_chunk
            and self.kwargs.get("responses_builtin_tools")
            and _is_responses_builtin_tool_error(exc)
        ):
            downgraded = _builtin_tool_types(self.kwargs.get("responses_builtin_tools"))
            if downgraded:
                RESPONSES_BUILTIN_UNSUPPORTED_CACHE.setdefault(
                    self.policy.cache_key, set()
                ).update(downgraded)
                self.kwargs["_a0_responses_builtin_downgrades"] = sorted(downgraded)
                self.kwargs["responses_builtin_tools"] = []
                return True

>>>>>>> Stashed changes
        recovery = self.policy.recover(exc, got_any_chunk=got_any_chunk)
        if recovery is TransportRecovery.RETRY_RESPONSES:
            self.kwargs["reasoning"] = {
                "effort": RESPONSES_REASONING_FALLBACK_EFFORT
            }
            return True
<<<<<<< Updated upstream
=======
        if recovery is TransportRecovery.RETRY_LOCAL_RESPONSES:
            self.kwargs["responses_state"] = RESPONSES_STATE_LOCAL
            self.kwargs.pop("previous_response_id", None)
            return True
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        return {
            "model": self.model,
            "stream": stream,
            **ResponsesTransport.from_chat(self.messages, self.kwargs, stop=self.stop),
=======
        response_kwargs = ResponsesTransport.from_chat(
            self.messages,
            self.kwargs,
            stop=self.stop,
            model=self.model,
        )
        self.last_request_state = _normalize_responses_state(
            response_kwargs.pop("responses_state", self.kwargs.get("responses_state"))
        )
        return {
            "model": self.model,
            "stream": stream,
            **response_kwargs,
        }

    def _llm_result_from_response(
        self, response: Any, request: dict[str, Any]
    ) -> LLMResult:
        return LLMResult.from_response(
            response,
            input_items=_as_list(request.get("input")),
            previous_response_id=str(request.get("previous_response_id") or ""),
            provider_model_key=self.model,
            mode=TransportMode.RESPONSES.value,
            state=self.last_request_state,
            capability=self._capability_metadata(),
        )

    def _stream_result_from_parser(
        self, parser: "ResponsesEventParser", request: dict[str, Any]
    ) -> LLMResult | None:
        if parser.completed_response is None:
            return None
        return self._llm_result_from_response(parser.completed_response, request)

    def _capability_metadata(self) -> dict[str, Any]:
        return {
            "mode": self.policy.mode.value,
            "state": self.policy.state,
            "cache_key": self.policy.cache_key,
            "fallback_error": _exception_text(self.policy.fallback_error)
            if self.policy.fallback_error
            else "",
            "state_fallback_error": _exception_text(self.policy.state_fallback_error)
            if self.policy.state_fallback_error
            else "",
            "builtin_tool_downgrades": list(
                self.kwargs.get("_a0_responses_builtin_downgrades") or []
            ),
>>>>>>> Stashed changes
        }


class ChatCompletionsTransport:
    @staticmethod
    def prepare_kwargs(
        kwargs: dict[str, Any],
        fallback_error: Exception | None = None,
    ) -> dict[str, Any]:
        chat_kwargs = dict(kwargs)
<<<<<<< Updated upstream
        chat_kwargs.pop("a0_responses_fallback", None)
=======
        _drop_internal_transport_kwargs(chat_kwargs)
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    ) -> dict[str, Any]:
        request = cls.prepare_kwargs(kwargs, stop=stop)
        request["input"] = cls.input_from_messages(messages) or ""
        request.setdefault("store", False)
=======
        model: str = "",
    ) -> dict[str, Any]:
        request = cls.prepare_kwargs(kwargs, stop=stop, model=model, messages=messages)
        state = _normalize_responses_state(kwargs.get("responses_state"))
        input_items = cls._select_input_items(kwargs, messages, state)
        request["input"] = input_items or ""
        cls.apply_state(request, kwargs, state=state)
        return request

    @classmethod
    def from_input(
        cls,
        input_items: list[dict[str, Any]],
        kwargs: dict[str, Any],
        stop: Optional[list[str]] = None,
        model: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        request = cls.prepare_kwargs(kwargs, stop=stop, model=model, messages=messages)
        state = _normalize_responses_state(kwargs.get("responses_state"))
        request["input"] = list(input_items or []) or ""
        cls.apply_state(request, kwargs, state=state)
>>>>>>> Stashed changes
        return request

    @classmethod
    def prepare_kwargs(
        cls,
        kwargs: dict[str, Any],
        stop: Optional[list[str]] = None,
<<<<<<< Updated upstream
    ) -> dict[str, Any]:
        request = dict(kwargs)
=======
        model: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        request = dict(kwargs)
        response_function_tools = request.pop("a0_responses_function_tools", None)
        response_builtin_tools = request.pop("responses_builtin_tools", None)
        request.pop("responses_state", None)
        request.pop("responses_delete_on_chat_delete", None)
        request.pop("responses_input_items", None)
        request.pop("responses_local_input_items", None)
        request.pop("previous_response_id", None)
        request.pop("_a0_responses_builtin_downgrades", None)
        _drop_internal_transport_kwargs(request)
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
        if "tools" in request:
            tools = cls.tools_from_chat(request["tools"])
            if _has_tools(tools):
                request["tools"] = tools
            else:
                request.pop("tools", None)
=======
        tools = cls.tools_from_chat(request.pop("tools", None))
        tools = cls.merge_response_tools(
            tools,
            response_function_tools=response_function_tools,
            response_builtin_tools=response_builtin_tools,
        )
        if _has_tools(tools):
            request["tools"] = tools
        else:
            request.pop("tools", None)
>>>>>>> Stashed changes

        function_call = request.pop("function_call", None)
        if function_call is not None and "tool_choice" not in request:
            request["tool_choice"] = cls.tool_choice_from_function_call(function_call)
        elif "tool_choice" in request:
            request["tool_choice"] = cls.tool_choice_from_chat(request["tool_choice"])

        if not _has_tools(request.get("tools")):
            request.pop("tool_choice", None)
            request.pop("parallel_tool_calls", None)

<<<<<<< Updated upstream
=======
        cls.prepare_prompt_caching(request, messages or [], model=model)

>>>>>>> Stashed changes
        _ = stop
        return {key: value for key, value in request.items() if value is not None}

    @classmethod
<<<<<<< Updated upstream
=======
    def _select_input_items(
        cls,
        kwargs: dict[str, Any],
        messages: list[dict[str, Any]],
        state: str,
    ) -> list[dict[str, Any]]:
        provider_items = kwargs.get("responses_input_items")
        local_items = kwargs.get("responses_local_input_items")
        previous_response_id = kwargs.get("previous_response_id")

        if (
            state == RESPONSES_STATE_PROVIDER
            and previous_response_id
            and isinstance(provider_items, list)
        ):
            return [dict(item) for item in provider_items if isinstance(item, dict)]

        if state == RESPONSES_STATE_LOCAL and isinstance(local_items, list):
            return [dict(item) for item in local_items if isinstance(item, dict)]

        return cls.input_from_messages(messages)

    @staticmethod
    def apply_state(
        request: dict[str, Any],
        kwargs: dict[str, Any],
        *,
        state: str,
    ) -> None:
        if state == RESPONSES_STATE_PROVIDER:
            request.setdefault("store", True)
            previous_response_id = str(kwargs.get("previous_response_id") or "")
            if previous_response_id:
                request["previous_response_id"] = previous_response_id
        elif state == RESPONSES_STATE_LOCAL:
            request.setdefault("store", False)
        else:
            request.setdefault("store", False)

    @classmethod
    def merge_response_tools(
        cls,
        tools: Any,
        *,
        response_function_tools: Any = None,
        response_builtin_tools: Any = None,
    ) -> list[Any]:
        merged: list[Any] = []
        if isinstance(tools, list):
            merged.extend(tools)
        elif tools:
            merged.append(tools)

        for source in (response_function_tools, response_builtin_tools):
            for tool in _as_list(source):
                normalized = cls.normalize_response_tool(tool)
                if normalized:
                    merged.append(normalized)
        return merged

    @staticmethod
    def normalize_response_tool(tool: Any) -> dict[str, Any] | None:
        if isinstance(tool, str):
            tool = {"type": tool}
        if not isinstance(tool, dict):
            return None
        return dict(tool)

    @staticmethod
    def prepare_prompt_caching(
        request: dict[str, Any],
        messages: list[dict[str, Any]],
        model: str = "",
    ) -> None:
        if not _is_openai_responses_cache_provider(model, request):
            return

        if "prompt_cache_key" not in request:
            prompt_cache_key = _default_prompt_cache_key(model, messages, request)
            if prompt_cache_key:
                request["prompt_cache_key"] = prompt_cache_key

        for key in OPENAI_RESPONSES_EXTRA_BODY_PARAMS:
            if key not in request:
                continue
            extra_body = request.get("extra_body")
            if not isinstance(extra_body, dict):
                extra_body = {}
            extra_body.setdefault(key, request.pop(key))
            request["extra_body"] = extra_body

    @classmethod
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            normalized["effort"] = _normalize_reasoning_effort(
                normalized.get("effort")
            )
            return normalized
        if reasoning is None:
            return None
        return {"effort": _normalize_reasoning_effort(reasoning)}
=======
            if "effort" in normalized:
                effort = _normalize_reasoning_effort(normalized.get("effort"))
                if effort is None:
                    normalized.pop("effort", None)
                else:
                    normalized["effort"] = effort
            return normalized or None
        if reasoning is None:
            return None
        effort = _normalize_reasoning_effort(reasoning)
        return {"effort": effort} if effort is not None else None
>>>>>>> Stashed changes

    @classmethod
    def parse_response(cls, response: Any) -> ChatChunk:
        response_delta = cls.output_text(response)
        reasoning_delta = cls.reasoning_text(response)
        if not response_delta:
            response_delta = cls.function_calls_text(response)
        return {"reasoning_delta": reasoning_delta, "response_delta": response_delta}

    @classmethod
    def parse_event(cls, event: Any) -> ChatChunk:
<<<<<<< Updated upstream
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
=======
        return ResponsesEventParser().parse(event)
>>>>>>> Stashed changes

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


<<<<<<< Updated upstream
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
=======
class ResponsesEventParser:
    """Stateful parser for Responses streaming events."""

    def __init__(self) -> None:
        self.function_calls: dict[str, dict[str, Any]] = {}
        self.output_index_keys: dict[str, str] = {}
        self.emitted_function_calls: set[str] = set()
        self.seen_response_delta = False
        self.seen_reasoning_delta = False
        self.completed_response: Any = None

    def parse(self, event: Any) -> ChatChunk:
        event_type = _get_value(event, "type") or ""
        response_delta = ""
        reasoning_delta = ""

        if event_type in {
            "response.output_text.delta",
            "response.refusal.delta",
            "response.text.delta",
        }:
            response_delta = str(_get_value(event, "delta") or "")
        elif event_type in {
            "response.reasoning_summary_text.delta",
            "response.reasoning_text.delta",
        }:
            reasoning_delta = str(_get_value(event, "delta") or "")
        elif event_type == "response.output_item.added":
            self._remember_function_call(_get_value(event, "item"), event)
        elif event_type == "response.function_call_arguments.delta":
            self._append_function_call_arguments(event)
        elif event_type == "response.function_call_arguments.done":
            response_delta = self._complete_function_call(event)
        elif event_type == "response.output_item.done":
            response_delta = self._complete_output_item(_get_value(event, "item"), event)
        elif event_type == "response.completed":
            response_delta, reasoning_delta = self._complete_response(event)
        elif event_type == "response.failed":
            raise RuntimeError(self._response_error_message(event))
        elif event_type == "error":
            error = _get_value(event, "error")
            message = _get_value(error, "message") or error
            raise RuntimeError(str(message))

        if response_delta:
            self.seen_response_delta = True
        if reasoning_delta:
            self.seen_reasoning_delta = True

        return {"reasoning_delta": reasoning_delta, "response_delta": response_delta}

    def _remember_function_call(self, item: Any, event: Any) -> str:
        if _get_value(item, "type") != "function_call":
            return ""
        key = self._event_key(event, item)
        if not key:
            return ""
        current = self.function_calls.get(key, {})
        merged = {**current, **_object_to_dict(item)}
        self.function_calls[key] = merged
        output_index = _get_value(event, "output_index")
        if output_index is not None:
            self.output_index_keys[str(output_index)] = key
        return key

    def _append_function_call_arguments(self, event: Any) -> None:
        key = self._event_key(event)
        if not key:
            return
        current = self.function_calls.setdefault(key, {"type": "function_call"})
        current["arguments"] = str(current.get("arguments") or "") + str(
            _get_value(event, "delta") or ""
        )

    def _complete_function_call(self, event: Any) -> str:
        key = self._event_key(event)
        if not key:
            return ""
        current = self.function_calls.setdefault(key, {"type": "function_call"})
        if _get_value(event, "arguments") is not None:
            current["arguments"] = _get_value(event, "arguments")
        if _get_value(event, "name"):
            current["name"] = _get_value(event, "name")
        return self._emit_function_call(key, current)

    def _complete_output_item(self, item: Any, event: Any) -> str:
        key = self._remember_function_call(item, event)
        if not key:
            return ""
        return self._emit_function_call(key, self.function_calls[key])

    def _complete_response(self, event: Any) -> tuple[str, str]:
        self.completed_response = _get_value(event, "response")
        if self.seen_response_delta or self.emitted_function_calls:
            return "", ""
        parsed = ResponsesTransport.parse_response(self.completed_response)
        if self.seen_reasoning_delta:
            parsed["reasoning_delta"] = ""
        return parsed["response_delta"], parsed["reasoning_delta"]

    def _emit_function_call(self, key: str, item: Any) -> str:
        if key in self.emitted_function_calls:
            return ""
        text = ResponsesTransport.function_call_text(item)
        if text:
            self.emitted_function_calls.add(key)
        return text

    def _event_key(self, event: Any, item: Any = None) -> str:
        key = _get_value(event, "item_id") or _get_value(item, "id")
        if key:
            return str(key)
        output_index = _get_value(event, "output_index")
        if output_index is not None:
            output_key = self.output_index_keys.get(str(output_index))
            if output_key:
                return output_key
            return f"output:{output_index}"
        return ""

    def _response_error_message(self, event: Any) -> str:
        response = _get_value(event, "response") or {}
        error = _get_value(response, "error") or _get_value(event, "error")
        message = _get_value(error, "message") or error
        return str(message or "Responses API request failed")


def clear_transport_capability_cache() -> None:
    RESPONSES_UNSUPPORTED_CACHE.clear()
    RESPONSES_STATE_UNSUPPORTED_CACHE.clear()
    RESPONSES_BUILTIN_UNSUPPORTED_CACHE.clear()


def delete_stored_response_ids(
    response_ids: list[str], **kwargs: Any
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    for response_id in response_ids:
        try:
            delete_responses(response_id=response_id, **kwargs)
        except Exception as exc:
            errors.append((response_id, _exception_text(exc)))
    return errors


async def adelete_stored_response_ids(
    response_ids: list[str], **kwargs: Any
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    for response_id in response_ids:
        try:
            await adelete_responses(response_id=response_id, **kwargs)
        except Exception as exc:
            errors.append((response_id, _exception_text(exc)))
    return errors


def _responses_cache_key(model: str, kwargs: dict[str, Any]) -> str:
    api_base = (
        kwargs.get("api_base")
        or kwargs.get("base_url")
        or kwargs.get("api_base_url")
        or ""
    )
    custom_provider = kwargs.get("custom_llm_provider") or ""
    return "|".join(str(part) for part in (model, custom_provider, api_base))


def _drop_legacy_transport_kwargs(kwargs: dict[str, Any]) -> None:
    # Legacy/imported transport knobs should never leak to LiteLLM.
    kwargs.pop("a0_api_mode", None)
    kwargs.pop("a0_responses_fallback", None)


def _drop_internal_transport_kwargs(kwargs: dict[str, Any]) -> None:
    _drop_legacy_transport_kwargs(kwargs)
    kwargs.pop("a0_responses_function_tools", None)
    kwargs.pop("_a0_responses_builtin_downgrades", None)
    kwargs.pop("responses_builtin_tools", None)
    kwargs.pop("responses_state", None)
    kwargs.pop("responses_delete_on_chat_delete", None)
    kwargs.pop("responses_input_items", None)
    kwargs.pop("responses_local_input_items", None)
    kwargs.pop("previous_response_id", None)


def _normalize_responses_state(value: Any) -> str:
    normalized = str(value or RESPONSES_STATE_PROVIDER).strip().lower()
    return normalized if normalized in RESPONSES_STATES else RESPONSES_STATE_PROVIDER


def _filter_unsupported_builtin_tools(kwargs: dict[str, Any], cache_key: str) -> None:
    unsupported = RESPONSES_BUILTIN_UNSUPPORTED_CACHE.get(cache_key)
    if not unsupported:
        return
    tools = kwargs.get("responses_builtin_tools")
    if not isinstance(tools, list):
        return
    filtered = []
    downgraded = []
    for tool in tools:
        tool_type = _response_tool_type(tool)
        if tool_type in unsupported:
            downgraded.append(tool_type)
            continue
        filtered.append(tool)
    if downgraded:
        kwargs["responses_builtin_tools"] = filtered
        kwargs["_a0_responses_builtin_downgrades"] = sorted(set(downgraded))


def _builtin_tool_types(tools: Any) -> set[str]:
    return {
        tool_type
        for tool in _as_list(tools)
        if (tool_type := _response_tool_type(tool))
    }


def _response_tool_type(tool: Any) -> str:
    if isinstance(tool, str):
        return tool
    if isinstance(tool, dict):
        return str(tool.get("type") or "")
    return ""


def _should_preserve_cache_control_on_chat(
    model: str,
    kwargs: dict[str, Any],
    messages: list[dict[str, Any]],
) -> bool:
    if not (_has_cache_control(messages) or _has_cache_control(kwargs.get("tools"))):
        return False
    return not _is_native_responses_provider(model, kwargs)


def _is_native_responses_provider(model: str, kwargs: dict[str, Any]) -> bool:
    api_base = str(
        kwargs.get("api_base")
        or kwargs.get("base_url")
        or kwargs.get("api_base_url")
        or ""
    ).lower()
    if "openrouter.ai" in api_base or "anthropic.com" in api_base:
        return False

    provider = str(kwargs.get("custom_llm_provider") or "").strip().lower()
    if not provider and "/" in str(model):
        provider = str(model).split("/", 1)[0].strip().lower()
    provider = provider.replace("-", "_")
    return provider in {"openai", "azure", "azure_ai", "xai"}


def _is_openai_responses_cache_provider(model: str, kwargs: dict[str, Any]) -> bool:
    api_base = str(
        kwargs.get("api_base")
        or kwargs.get("base_url")
        or kwargs.get("api_base_url")
        or ""
    ).lower()
    if api_base and "api.openai.com" not in api_base:
        return False

    provider = str(kwargs.get("custom_llm_provider") or "").strip().lower()
    if not provider and "/" in str(model):
        provider = str(model).split("/", 1)[0].strip().lower()
    if not provider and str(model):
        provider = "openai"
    provider = provider.replace("-", "_")
    return provider == "openai"


def _default_prompt_cache_key(
    model: str,
    messages: list[dict[str, Any]],
    request: dict[str, Any],
) -> str:
    material = _prompt_cache_key_material(messages, request)
    if not material:
        return ""
    digest = hashlib.sha256(
        json.dumps(
            {
                "model": model,
                "material": material,
            },
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:32]
    return f"a0-{digest}"


def _prompt_cache_key_material(
    messages: list[dict[str, Any]],
    request: dict[str, Any],
) -> dict[str, Any]:
    material: dict[str, Any] = {}

    leading_messages: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "")
        if role not in {"system", "developer"}:
            break
        leading_messages.append(
            {
                "role": role,
                "content": message.get("content"),
            }
        )
    if leading_messages:
        material["messages"] = leading_messages

    if request.get("instructions"):
        material["instructions"] = request["instructions"]
    if request.get("prompt"):
        material["prompt"] = request["prompt"]
    if request.get("tools"):
        material["tools"] = request["tools"]

    return material


def _has_cache_control(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("cache_control") is not None:
            return True
        return any(_has_cache_control(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_cache_control(item) for item in value)
    return False


def _object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        dumped = obj.model_dump()
        return dict(dumped) if isinstance(dumped, dict) else {}
    if hasattr(obj, "dict"):
        dumped = obj.dict()
        return dict(dumped) if isinstance(dumped, dict) else {}
    return {}


def _normalize_reasoning_effort(effort: Any) -> str | None:
>>>>>>> Stashed changes
    if isinstance(effort, str):
        normalized = effort.strip().lower()
    else:
        normalized = str(effort).strip().lower() if effort is not None else ""
    if normalized in RESPONSES_REASONING_EFFORTS:
        return normalized
    if normalized in NO_REASONING_EFFORT_ALIASES:
<<<<<<< Updated upstream
        return RESPONSES_REASONING_FALLBACK_EFFORT
=======
        return None
>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
def _is_responses_state_unsupported_error(exc: Exception) -> bool:
    text = _exception_text(exc).lower()
    if any(marker in text for marker in ("429", "too many requests", "rate limit")):
        return False
    if "404" in text and "/v1/responses/" in text:
        return True
    return any(
        marker in text
        for marker in (
            "previous_response_id",
            "store",
            "stored response",
            "response not found",
            "no response found",
            "does not support response storage",
            "doesn't support response storage",
            "response storage is not supported",
            "state is not supported",
        )
    )


def _is_responses_builtin_tool_error(exc: Exception) -> bool:
    text = _exception_text(exc).lower()
    if any(marker in text for marker in ("429", "too many requests", "rate limit")):
        return False
    return any(
        marker in text
        for marker in (
            "unsupported tool",
            "unsupported tools",
            "invalid tool",
            "tool type",
            "tools[",
            "web_search",
            "file_search",
            "code_interpreter",
            "image_generation",
            "computer_use_preview",
            "mcp",
        )
    )


>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
def _has_chunk_delta(chunk: ChatChunk) -> bool:
    return bool(chunk.get("response_delta") or chunk.get("reasoning_delta"))


>>>>>>> Stashed changes
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
