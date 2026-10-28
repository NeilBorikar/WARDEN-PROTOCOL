"""OpenAI-compatible LLM client with per-role model configuration.

WHY:
- Section 7: "Agents use tool-calling through LLMClient with per-role model config."
- Each role (buyer, seller, attacker, verifier) can use different model providers/names.
- Per-call token caps and per-run budget enforcement prevent runaway spend.
- Protocol class enables FakeLLMClient and CassetteClient for deterministic testing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCall:
    """A structured tool call extracted from an LLM response."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass(frozen=True)
class LLMMessage:
    """A single message in a chat conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM completion call."""

    content: str
    tool_calls: list[ToolCall]
    prompt_tokens: int
    completion_tokens: int
    model: str
    finish_reason: str  # "stop", "tool_calls", "length"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass(frozen=True)
class ToolDefinition:
    """Schema for a callable tool exposed to the LLM."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class ModelConfig:
    """Per-role model configuration loaded from environment.

    WHY: Section 7 says "buyer, seller, attacker, verifier use separate settings
    so different vendors can be used."
    """

    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model_name: str = "gpt-4o-mini"
    max_tokens_per_call: int = 4096
    temperature: float = 0.0  # Deterministic for safety-critical decisions


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM clients, enabling fake and cassette implementations."""

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a chat completion request and return the response."""
        ...

    @property
    def total_tokens_used(self) -> int:
        """Total tokens consumed across all calls in this session."""
        ...


class OpenAICompatibleClient:
    """Production LLM client using httpx against any OpenAI-compatible API.

    WHY: Supports OpenAI, Azure, local models (Ollama, vLLM) via base_url swap.
    Token tracking enables per-run budget enforcement.
    """

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self._total_tokens: int = 0

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Execute chat completion via httpx (lazy import to avoid hard dep in tests)."""
        import httpx

        effective_max = min(
            max_tokens or self.config.max_tokens_per_call,
            self.config.max_tokens_per_call,
        )

        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": self._format_messages(messages),
            "max_tokens": effective_max,
            "temperature": self.config.temperature,
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()

        return self._parse_response(body)

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessage list to OpenAI API format."""
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.call_id,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": _safe_json_dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(entry)
        return formatted

    def _parse_response(self, body: dict[str, Any]) -> LLMResponse:
        """Parse OpenAI-compatible response into LLMResponse."""
        choice = body["choices"][0]
        message = choice["message"]
        usage = body.get("usage", {})

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        self._total_tokens += prompt_tokens + completion_tokens

        tool_calls: list[ToolCall] = []
        raw_tool_calls = message.get("tool_calls", [])
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    tool_name=func.get("name", ""),
                    arguments=_safe_json_loads(func.get("arguments", "{}")),
                    call_id=tc.get("id", ""),
                )
            )

        return LLMResponse(
            content=message.get("content", "") or "",
            tool_calls=tool_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=body.get("model", self.config.model_name),
            finish_reason=choice.get("finish_reason", "stop"),
        )


def _safe_json_dumps(data: dict[str, Any]) -> str:
    """Serialize dict to JSON string, handling edge cases."""
    import json

    return json.dumps(data, ensure_ascii=False)


def _safe_json_loads(text: str) -> dict[str, Any]:
    """Parse JSON string safely, returning empty dict on failure (P4: fail closed)."""
    import json

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        return {"_raw": result}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse tool call arguments: %s", text[:200])
        return {"_raw": text}
