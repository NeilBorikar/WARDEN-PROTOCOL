"""Record/replay cassette for deterministic LLM interaction testing.

WHY:
- Section 8: "Demo mode: record/replay cassettes so the video recording is
  deterministic and works offline."
- Section 7: "Reproducible with a fixed seed and cassette replay."
- Records live LLM calls to a JSON file; replays them without network calls.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.llm.client import (
    LLMMessage,
    LLMResponse,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class CassetteLLMClient:
    """Records or replays LLM interactions from a JSON cassette file.

    Modes:
    - RECORD: wraps a real LLM client, saves all requests/responses to file.
    - REPLAY: loads a cassette file and replays responses in order.
    """

    def __init__(
        self,
        cassette_path: str | Path,
        mode: str = "replay",
        wrapped_client: Any = None,
    ) -> None:
        self._path = Path(cassette_path)
        self._mode = mode.lower()
        self._wrapped = wrapped_client
        self._entries: list[dict[str, Any]] = []
        self._replay_index: int = 0
        self._total_tokens: int = 0

        if self._mode == "replay" and self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                self._entries = json.load(f)
            logger.info("Loaded cassette with %d entries from %s", len(self._entries), self._path)
        elif self._mode == "record" and self._wrapped is None:
            raise ValueError("CassetteLLMClient in RECORD mode requires a wrapped_client.")

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Record or replay a chat completion."""
        if self._mode == "record":
            return self._record(messages, tools, max_tokens)
        return self._replay()

    def _record(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None,
        max_tokens: int | None,
    ) -> LLMResponse:
        """Forward to wrapped client and save the interaction."""
        response = self._wrapped.chat(messages, tools, max_tokens)
        self._total_tokens += response.total_tokens

        entry = {
            "messages": [_serialize_message(m) for m in messages],
            "response": _serialize_response(response),
        }
        self._entries.append(entry)
        self._save()
        return response

    def _replay(self) -> LLMResponse:
        """Return the next pre-recorded response."""
        if self._replay_index >= len(self._entries):
            logger.warning("Cassette exhausted at index %d", self._replay_index)
            return LLMResponse(
                content="[Cassette exhausted]",
                tool_calls=[],
                prompt_tokens=0,
                completion_tokens=0,
                model="cassette-exhausted",
                finish_reason="stop",
            )

        entry = self._entries[self._replay_index]
        self._replay_index += 1
        response = _deserialize_response(entry["response"])
        self._total_tokens += response.total_tokens
        return response

    def _save(self) -> None:
        """Persist cassette entries to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2, ensure_ascii=False)


def _serialize_message(msg: LLMMessage) -> dict[str, Any]:
    """Serialize an LLMMessage to a JSON-compatible dict."""
    return {
        "role": msg.role,
        "content": msg.content,
        "tool_calls": [
            {"tool_name": tc.tool_name, "arguments": tc.arguments, "call_id": tc.call_id}
            for tc in msg.tool_calls
        ],
        "tool_call_id": msg.tool_call_id,
        "name": msg.name,
    }


def _serialize_response(resp: LLMResponse) -> dict[str, Any]:
    """Serialize an LLMResponse to a JSON-compatible dict."""
    return {
        "content": resp.content,
        "tool_calls": [
            {"tool_name": tc.tool_name, "arguments": tc.arguments, "call_id": tc.call_id}
            for tc in resp.tool_calls
        ],
        "prompt_tokens": resp.prompt_tokens,
        "completion_tokens": resp.completion_tokens,
        "model": resp.model,
        "finish_reason": resp.finish_reason,
    }


def _deserialize_response(data: dict[str, Any]) -> LLMResponse:
    """Reconstruct an LLMResponse from a cassette entry."""
    tool_calls = [
        ToolCall(
            tool_name=tc["tool_name"],
            arguments=tc.get("arguments", {}),
            call_id=tc.get("call_id", ""),
        )
        for tc in data.get("tool_calls", [])
    ]
    return LLMResponse(
        content=data.get("content", ""),
        tool_calls=tool_calls,
        prompt_tokens=data.get("prompt_tokens", 0),
        completion_tokens=data.get("completion_tokens", 0),
        model=data.get("model", "cassette"),
        finish_reason=data.get("finish_reason", "stop"),
    )
