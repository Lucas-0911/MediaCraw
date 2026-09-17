# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Memory DTOs and the AgentMemory port. AgentLoop depends on this, not SQL."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, ConfigDict, Field

from agent.core.contracts import ToolResult


class AgentMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AgentToolCallStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    DENIED = "DENIED"


class AgentConversationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    channel: str
    telegram_chat_id: str = ""
    created_at: int
    updated_at: int


class AgentMessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    role: AgentMessageRole
    content: str
    created_at: int


class AgentToolCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    message_id: Optional[str] = None
    tool_name: str
    arguments_json: str
    result_json: Optional[str] = None
    status: AgentToolCallStatus
    latency_ms: Optional[int] = None
    created_at: int


class AgentShortTermState(BaseModel):
    """Ephemeral per-conversation state. Redis is not the source of truth."""

    model_config = ConfigDict(extra="forbid")

    current_job_id: Optional[str] = None
    current_idea_ids: List[str] = Field(default_factory=list)
    current_video_job_id: Optional[str] = None
    last_activity: Optional[int] = None


class AgentMemory(Protocol):
    async def get_or_create_conversation(
        self,
        *,
        user_id: str,
        channel: str,
        telegram_chat_id: Optional[str] = None,
    ) -> AgentConversationRecord: ...

    async def get_conversation(self, conversation_id: str) -> Optional[AgentConversationRecord]: ...

    async def save_user_message(self, conversation_id: str, content: str) -> AgentMessageRecord: ...

    async def save_assistant_message(self, conversation_id: str, content: str) -> AgentMessageRecord: ...

    async def start_tool_call(
        self,
        conversation_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        message_id: Optional[str] = None,
    ) -> AgentToolCallRecord: ...

    async def complete_tool_call(
        self,
        tool_call_id: str,
        result: Union[Dict[str, Any], ToolResult],
        status: Optional[AgentToolCallStatus] = None,
        latency_ms: int = 0,
    ) -> AgentToolCallRecord: ...

    async def get_recent_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> List[AgentMessageRecord]: ...

    async def get_short_term_state(self, conversation_id: str) -> Optional[AgentShortTermState]: ...

    async def save_short_term_state(self, conversation_id: str, state: AgentShortTermState) -> None: ...

    async def acquire_lock(self, conversation_id: str) -> bool: ...

    async def release_lock(self, conversation_id: str) -> None: ...
