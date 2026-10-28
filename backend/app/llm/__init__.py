"""LLM client abstraction - OpenAI-compatible, per-role model config.

Exports the protocol and all implementations (production, fake, cassette).
"""

from app.llm.cassette import CassetteLLMClient
from app.llm.client import (
    LLMClient,
    LLMMessage,
    LLMResponse,
    ModelConfig,
    OpenAICompatibleClient,
    ToolCall,
    ToolDefinition,
)
from app.llm.fake import FakeLLMClient

__all__ = [
    "CassetteLLMClient",
    "FakeLLMClient",
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "ModelConfig",
    "OpenAICompatibleClient",
    "ToolCall",
    "ToolDefinition",
]
