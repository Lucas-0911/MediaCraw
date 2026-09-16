# -*- coding: utf-8 -*-
"""Validated contracts shared by the Agent Loop, LLM client and tools."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SECRET_MARKERS = ("secret", "token", "api_key", "apikey", "cookie", "password", "authorization")


class ToolResultStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    INVALID = "invalid"
    TIMEOUT = "timeout"
    ERROR = "error"
    DENIED = "denied"


class AgentContext(BaseModel):
    """Safe, channel-neutral request context; it intentionally has no memory."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    channel: str = Field(default="internal", min_length=1, max_length=32)
    actor_id: Optional[str] = Field(default=None, max_length=256)
    user_id: Optional[str] = Field(default=None, max_length=256)
    telegram_chat_id: Optional[str] = Field(default=None, max_length=256)
    conversation_id: Optional[str] = Field(default=None, max_length=256)
    message: str = Field(min_length=1, max_length=8_000)
    locale: Optional[str] = Field(default=None, max_length=32)
    authenticated: bool = False
    license: Optional[str] = Field(default=None, max_length=64)
    permissions: Set[str] = Field(default_factory=set)
    quota_remaining: Optional[int] = Field(default=None, ge=0)
    current_job_id: Optional[str] = Field(default=None, max_length=128)
    current_idea_ids: List[str] = Field(default_factory=list, max_length=100)
    current_video_job_id: Optional[str] = Field(default=None, max_length=128)
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("metadata")
    @classmethod
    def reject_secret_metadata(cls, metadata: Dict[str, str]) -> Dict[str, str]:
        for key in metadata:
            normalized = key.lower().replace("-", "_")
            if any(marker in normalized for marker in _SECRET_MARKERS):
                raise ValueError("AgentContext metadata must not contain secrets")
        return metadata


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=128)
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Structured tool output. The LLM sees only this serialized, safe result."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    tool_name: str
    status: ToolResultStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    message: Optional[str] = None
    job_id: Optional[str] = None
    requires_confirmation: bool = False


class LLMResponse(BaseModel):
    """One iteration result from the LLM provider."""

    model_config = ConfigDict(extra="forbid")

    final_answer: Optional[str] = Field(default=None, max_length=12_000)
    tool_calls: List[ToolCall] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_one_outcome(self) -> "LLMResponse":
        if not self.final_answer and not self.tool_calls:
            raise ValueError("LLM response must contain a final answer or tool calls")
        return self


class AgentResponseStatus(str, Enum):
    ANSWERED = "answered"
    MAX_STEPS = "max_steps"
    TIMEOUT = "timeout"
    ERROR = "error"


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: AgentResponseStatus
    answer: str
    tool_results: List[ToolResult] = Field(default_factory=list)
    steps: int = 0
    data: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None
    requires_confirmation: bool = False
    error: Optional[str] = None
