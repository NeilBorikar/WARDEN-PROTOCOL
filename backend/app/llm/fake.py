"""Scripted (fake) LLM client for deterministic testing.

WHY:
- Section 7: Tests must work without live LLM calls.
- Section 9 Phase 3: "scripted happy path end to end."
- FakeLLMClient returns pre-programmed responses in sequence,
  enabling fully deterministic negotiation replays.
"""

from __future__ import annotations

import logging
from typing import Any

from app.llm.client import (
    LLMMessage,
    LLMResponse,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class FakeLLMClient:
    """Returns pre-scripted responses in sequence.

    WHY: Enables deterministic unit and integration tests without
    network calls or API keys. Each call pops the next scripted response.
    If the script is exhausted, returns a fallback "stop" response (P4).
    """

    def __init__(self, scripted_responses: list[LLMResponse] | None = None) -> None:
        self._responses: list[LLMResponse] = list(scripted_responses or [])
        self._call_index: int = 0
        self._total_tokens: int = 0
        self.call_log: list[list[LLMMessage]] = []

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens

    @property
    def calls_made(self) -> int:
        return self._call_index

    def add_response(self, response: LLMResponse) -> None:
        """Append a scripted response to the queue."""
        self._responses.append(response)

    def add_text_response(self, text: str, model: str = "fake-model") -> None:
        """Convenience: add a simple text-only response."""
        self._responses.append(
            LLMResponse(
                content=text,
                tool_calls=[],
                prompt_tokens=10,
                completion_tokens=len(text.split()),
                model=model,
                finish_reason="stop",
            )
        )

    def add_tool_call_response(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        call_id: str = "call-1",
        model: str = "fake-model",
    ) -> None:
        """Convenience: add a tool call response."""
        self._responses.append(
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        tool_name=tool_name,
                        arguments=arguments,
                        call_id=call_id,
                    )
                ],
                prompt_tokens=10,
                completion_tokens=5,
                model=model,
                finish_reason="tool_calls",
            )
        )

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Return the next scripted response, or a fallback if exhausted."""
        self.call_log.append(list(messages))

        if self._call_index < len(self._responses):
            response = self._responses[self._call_index]
        else:
            logger.warning(
                "FakeLLMClient exhausted at call %d, returning fallback stop",
                self._call_index,
            )
            response = LLMResponse(
                content="[FakeLLM: no more scripted responses]",
                tool_calls=[],
                prompt_tokens=0,
                completion_tokens=0,
                model="fake-exhausted",
                finish_reason="stop",
            )

        self._call_index += 1
        self._total_tokens += response.total_tokens
        return response

    def reset(self) -> None:
        """Reset state for a fresh test scenario."""
        self._call_index = 0
        self._total_tokens = 0
        self.call_log.clear()
