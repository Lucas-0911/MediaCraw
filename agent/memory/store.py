# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""SQLAlchemy persistence for Agent conversations, messages and tool calls."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.agent_session import create_agent_tables
from database.agent_models import AgentConversation, AgentMessage, AgentToolCall
from tools.time_util import get_current_timestamp

from .contracts import (
    AgentConversationRecord,
    AgentMessageRecord,
    AgentMessageRole,
    AgentToolCallRecord,
    AgentToolCallStatus,
)
from .errors import AgentMemoryUnavailable


class SqlAgentMemoryStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create_schema(self) -> None:
        await create_agent_tables(self._engine)

    async def get_or_create_conversation(
        self, *, user_id: str, channel: str, telegram_chat_id: str
    ) -> AgentConversationRecord:
        try:
            async with self._session() as session:
                existing = await self._find_conversation(session, user_id, channel, telegram_chat_id)
                if existing:
                    return self._conversation_record(existing)
                now = get_current_timestamp()
                row = AgentConversation(
                    id=str(uuid4()),
                    user_id=user_id,
                    channel=channel,
                    telegram_chat_id=telegram_chat_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    existing = await self._find_conversation(session, user_id, channel, telegram_chat_id)
                    if existing is None:
                        raise AgentMemoryUnavailable("conversation create raced and lookup failed")
                    return self._conversation_record(existing)
                return self._conversation_record(row)
        except AgentMemoryUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("conversation store unavailable") from exc

    async def get_conversation(self, conversation_id: str) -> Optional[AgentConversationRecord]:
        try:
            async with self._session() as session:
                row = await session.get(AgentConversation, conversation_id)
                return self._conversation_record(row) if row else None
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("conversation store unavailable") from exc

    async def save_message(
        self, conversation_id: str, role: AgentMessageRole, content: str
    ) -> AgentMessageRecord:
        try:
            async with self._session() as session:
                conversation = await session.get(AgentConversation, conversation_id)
                if conversation is None:
                    raise AgentMemoryUnavailable("conversation not found")
                created_at = await self._next_created_at(session, AgentMessage, conversation_id)
                row = AgentMessage(
                    id=str(uuid4()),
                    conversation_id=conversation_id,
                    role=role.value,
                    content=content,
                    created_at=created_at,
                )
                conversation.updated_at = created_at
                session.add(row)
                await session.flush()
                return self._message_record(row)
        except AgentMemoryUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("message store unavailable") from exc

    async def get_recent_messages(self, conversation_id: str, limit: int) -> list[AgentMessageRecord]:
        try:
            async with self._session() as session:
                stmt = (
                    select(AgentMessage)
                    .where(AgentMessage.conversation_id == conversation_id)
                    .order_by(AgentMessage.created_at.desc(), AgentMessage.id.desc())
                    .limit(limit)
                )
                rows = list((await session.execute(stmt)).scalars().all())
                rows.reverse()
                return [self._message_record(row) for row in rows]
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("message store unavailable") from exc

    async def start_tool_call(
        self,
        conversation_id: str,
        tool_name: str,
        arguments_json: str,
        message_id: Optional[str],
    ) -> AgentToolCallRecord:
        try:
            async with self._session() as session:
                if await session.get(AgentConversation, conversation_id) is None:
                    raise AgentMemoryUnavailable("conversation not found")
                created_at = await self._next_created_at(session, AgentToolCall, conversation_id)
                row = AgentToolCall(
                    id=str(uuid4()),
                    conversation_id=conversation_id,
                    message_id=message_id,
                    tool_name=tool_name,
                    arguments_json=arguments_json,
                    result_json=None,
                    status=AgentToolCallStatus.RUNNING.value,
                    latency_ms=None,
                    created_at=created_at,
                )
                session.add(row)
                await session.flush()
                return self._tool_call_record(row)
        except AgentMemoryUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("tool-call store unavailable") from exc

    async def list_tool_calls(self, conversation_id: str) -> list[AgentToolCallRecord]:
        try:
            async with self._session() as session:
                stmt = (
                    select(AgentToolCall)
                    .where(AgentToolCall.conversation_id == conversation_id)
                    .order_by(AgentToolCall.created_at.asc(), AgentToolCall.id.asc())
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [self._tool_call_record(row) for row in rows]
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("tool-call store unavailable") from exc

    async def complete_tool_call(
        self,
        tool_call_id: str,
        result_json: str,
        status: AgentToolCallStatus,
        latency_ms: int,
    ) -> AgentToolCallRecord:
        try:
            async with self._session() as session:
                row = await session.get(AgentToolCall, tool_call_id)
                if row is None:
                    raise AgentMemoryUnavailable("tool call not found")
                row.result_json = result_json
                row.status = status.value
                row.latency_ms = latency_ms
                await session.flush()
                return self._tool_call_record(row)
        except AgentMemoryUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise AgentMemoryUnavailable("tool-call store unavailable") from exc

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @staticmethod
    async def _find_conversation(
        session: AsyncSession, user_id: str, channel: str, telegram_chat_id: str
    ) -> Optional[AgentConversation]:
        stmt = select(AgentConversation).where(
            AgentConversation.user_id == user_id,
            AgentConversation.channel == channel,
            AgentConversation.telegram_chat_id == telegram_chat_id,
        )
        return (await session.execute(stmt)).scalars().first()

    @staticmethod
    async def _next_created_at(session: AsyncSession, model, conversation_id: str) -> int:
        stmt = select(func.max(model.created_at)).where(model.conversation_id == conversation_id)
        last = (await session.execute(stmt)).scalar()
        now = get_current_timestamp()
        if last is not None and last >= now:
            return int(last) + 1
        return now

    @staticmethod
    def _conversation_record(row: AgentConversation) -> AgentConversationRecord:
        return AgentConversationRecord(
            id=row.id,
            user_id=row.user_id,
            channel=row.channel,
            telegram_chat_id=row.telegram_chat_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _message_record(row: AgentMessage) -> AgentMessageRecord:
        return AgentMessageRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            role=AgentMessageRole(row.role),
            content=row.content,
            created_at=row.created_at,
        )

    @staticmethod
    def _tool_call_record(row: AgentToolCall) -> AgentToolCallRecord:
        return AgentToolCallRecord(
            id=row.id,
            conversation_id=row.conversation_id,
            message_id=row.message_id,
            tool_name=row.tool_name,
            arguments_json=row.arguments_json,
            result_json=row.result_json,
            status=AgentToolCallStatus(row.status),
            latency_ms=row.latency_ms,
            created_at=row.created_at,
        )
