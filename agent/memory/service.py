# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""AgentMemory implementation: sanitizes, persists, and coordinates short-term state."""
from __future__ import annotations

from typing import Any, Dict, Optional

from agent.core.contracts import ToolResult, ToolResultStatus
from config import agent_config
from tools import utils

from .contracts import (
    AgentConversationRecord,
    AgentMessageRecord,
    AgentMessageRole,
    AgentShortTermState,
    AgentToolCallRecord,
    AgentToolCallStatus,
)
from .errors import AgentMemoryUnavailable
from .lock import ConversationLock
from .sanitizer import sanitize, sanitize_json, sanitize_text
from .state import AgentShortTermStateStore
from .store import SqlAgentMemoryStore

_TOOL_RESULT_STATUS = {
    ToolResultStatus.OK: AgentToolCallStatus.SUCCESS,
    ToolResultStatus.EMPTY: AgentToolCallStatus.SUCCESS,
    ToolResultStatus.INVALID: AgentToolCallStatus.FAILED,
    ToolResultStatus.ERROR: AgentToolCallStatus.FAILED,
    ToolResultStatus.TIMEOUT: AgentToolCallStatus.TIMEOUT,
    ToolResultStatus.DENIED: AgentToolCallStatus.DENIED,
}


class AgentMemoryService:
    def __init__(
        self,
        store: SqlAgentMemoryStore,
        state: AgentShortTermStateStore,
        lock: ConversationLock,
        max_messages: int = agent_config.AGENT_MEMORY_MAX_MESSAGES,
    ) -> None:
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        self._store = store
        self._state = state
        self._lock = lock
        self._max_messages = max_messages

    async def get_or_create_conversation(
        self,
        *,
        user_id: str,
        channel: str,
        telegram_chat_id: Optional[str] = None,
    ) -> AgentConversationRecord:
        if not user_id:
            raise AgentMemoryUnavailable("conversation requires an authenticated user_id")
        if not channel:
            raise AgentMemoryUnavailable("conversation requires a channel")
        return await self._store.get_or_create_conversation(
            user_id=user_id,
            channel=channel,
            telegram_chat_id=telegram_chat_id or "",
        )

    async def get_conversation(self, conversation_id: str) -> Optional[AgentConversationRecord]:
        return await self._store.get_conversation(conversation_id)

    async def save_user_message(self, conversation_id: str, content: str) -> AgentMessageRecord:
        return await self._store.save_message(
            conversation_id, AgentMessageRole.USER, sanitize_text(content)
        )

    async def save_assistant_message(self, conversation_id: str, content: str) -> AgentMessageRecord:
        return await self._store.save_message(
            conversation_id, AgentMessageRole.ASSISTANT, sanitize_text(content)
        )

    async def start_tool_call(
        self,
        conversation_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        message_id: Optional[str] = None,
    ) -> AgentToolCallRecord:
        return await self._store.start_tool_call(
            conversation_id,
            tool_name,
            sanitize_json(arguments),
            message_id,
        )

    async def complete_tool_call(
        self,
        tool_call_id: str,
        result: Dict[str, Any] | ToolResult,
        status: AgentToolCallStatus | None = None,
        latency_ms: int = 0,
    ) -> AgentToolCallRecord:
        if isinstance(result, ToolResult):
            payload = result.model_dump(mode="json")
            mapped = status or _TOOL_RESULT_STATUS.get(result.status, AgentToolCallStatus.FAILED)
        else:
            payload = result
            mapped = status or AgentToolCallStatus.SUCCESS
        return await self._store.complete_tool_call(
            tool_call_id,
            sanitize_json(payload),
            mapped,
            latency_ms,
        )

    async def list_tool_calls(self, conversation_id: str) -> list[AgentToolCallRecord]:
        return await self._store.list_tool_calls(conversation_id)

    async def get_recent_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> list[AgentMessageRecord]:
        capped = limit if limit is not None else self._max_messages
        if capped < 1:
            return []
        return await self._store.get_recent_messages(conversation_id, capped)

    async def get_short_term_state(self, conversation_id: str) -> Optional[AgentShortTermState]:
        return await self._state.get(conversation_id)

    async def save_short_term_state(self, conversation_id: str, state: AgentShortTermState) -> None:
        await self._state.set(conversation_id, state)

    async def acquire_lock(self, conversation_id: str) -> bool:
        try:
            return await self._lock.acquire(conversation_id)
        except Exception as exc:
            raise AgentMemoryUnavailable("conversation lock backend unavailable") from exc

    async def release_lock(self, conversation_id: str) -> None:
        try:
            await self._lock.release(conversation_id)
        except Exception:
            utils.logger.warning("agent conversation lock release failed for %s", conversation_id)
