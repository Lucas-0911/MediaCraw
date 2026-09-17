# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Bounded orchestration loop; it owns no crawler or storage business logic."""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Set

from config import agent_config
from tools import utils

from .contracts import (
    AgentContext,
    AgentHistoryMessage,
    AgentResponse,
    AgentResponseStatus,
    ToolCall,
    ToolResult,
)
from .executor import ToolExecutor
from .llm import AgentLLM
from agent.memory.contracts import AgentMemory, AgentMessageRecord, AgentShortTermState
from agent.memory.errors import AgentMemoryError, AgentMemoryLockTimeout, AgentMemoryUnavailable
from .registry import ToolRegistry

_SAFE_ERROR_ANSWER = "The request could not be completed safely."
_BUSY_ANSWER = "The previous message is still being processed. Please try again."


class AgentLoop:
    def __init__(
        self,
        llm: AgentLLM,
        registry: ToolRegistry,
        *,
        max_steps: int = agent_config.MAX_AGENT_STEPS,
        per_tool_timeout_seconds: float = agent_config.AGENT_TOOL_TIMEOUT_SECONDS,
        request_timeout_seconds: float = agent_config.AGENT_REQUEST_TIMEOUT_SECONDS,
        memory: Optional[AgentMemory] = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if per_tool_timeout_seconds <= 0 or request_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")
        self._llm = llm
        self._registry = registry
        self._max_steps = max_steps
        self._request_timeout_seconds = request_timeout_seconds
        self._executor = ToolExecutor(registry, per_tool_timeout_seconds)
        self._memory = memory

    async def run(self, context: AgentContext) -> AgentResponse:
        try:
            coro = self._run_with_memory(context) if self._memory is not None else self._run(context)
            return await asyncio.wait_for(coro, timeout=self._request_timeout_seconds)
        except asyncio.TimeoutError:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.TIMEOUT,
                answer="The request timed out before a verified answer was available.",
            )
        except AgentMemoryLockTimeout:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.ERROR,
                answer=_BUSY_ANSWER,
                error="conversation_busy",
            )
        except AgentMemoryError:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.ERROR,
                answer=_SAFE_ERROR_ANSWER,
                error="memory_unavailable",
            )
        except Exception:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.ERROR,
                answer=_SAFE_ERROR_ANSWER,
            )

    async def _run_with_memory(self, context: AgentContext) -> AgentResponse:
        memory = self._memory
        assert memory is not None
        user_id = context.user_id or context.actor_id
        if not user_id:
            raise AgentMemoryUnavailable("conversation requires a user identity")

        conversation = await memory.get_or_create_conversation(
            user_id=user_id,
            channel=context.channel,
            telegram_chat_id=context.telegram_chat_id,
        )
        context = context.model_copy(update={"conversation_id": conversation.id})

        acquired = await memory.acquire_lock(conversation.id)
        if not acquired:
            raise AgentMemoryLockTimeout("conversation is already being processed")

        try:
            context = await self._restore_short_term_state(memory, context)
            user_message = await memory.save_user_message(conversation.id, context.message)
            history = await memory.get_recent_messages(conversation.id)
            context = context.model_copy(update={"history": self._prior_history(history)})
            response = await self._run(context, user_message_id=user_message.id)
            await self._persist_assistant(memory, conversation.id, response)
            await self._persist_short_term_state(memory, context, response)
            return response
        finally:
            await memory.release_lock(conversation.id)

    async def _run(self, context: AgentContext, user_message_id: Optional[str] = None) -> AgentResponse:
        results: list[ToolResult] = []
        seen_calls: Set[str] = set()
        for step in range(1, self._max_steps + 1):
            response = await self._llm.respond(context, self._registry.definitions(), results)
            if response.final_answer:
                latest = results[-1] if results else None
                return AgentResponse(
                    request_id=context.request_id,
                    status=AgentResponseStatus.ANSWERED,
                    answer=response.final_answer,
                    tool_results=results,
                    steps=step,
                    data=latest.data if latest else None,
                    job_id=latest.job_id if latest else None,
                    requires_confirmation=latest.requires_confirmation if latest else False,
                    error=latest.error_code if latest else None,
                )
            executed = await asyncio.gather(
                *[
                    self._execute_and_record(call, context, seen_calls, user_message_id)
                    for call in response.tool_calls
                ]
            )
            results.extend(executed)

        return AgentResponse(
            request_id=context.request_id,
            status=AgentResponseStatus.MAX_STEPS,
            answer="I could not complete a verified answer within the allowed tool steps.",
            tool_results=results,
            steps=self._max_steps,
            data=results[-1].data if results else None,
            job_id=results[-1].job_id if results else None,
            error=results[-1].error_code if results else None,
        )

    async def _execute_and_record(
        self,
        call: ToolCall,
        context: AgentContext,
        seen_calls: Set[str],
        user_message_id: Optional[str],
    ) -> ToolResult:
        record_id: Optional[str] = None
        started = time.monotonic()
        if self._memory is not None and context.conversation_id:
            try:
                record = await self._memory.start_tool_call(
                    context.conversation_id,
                    call.name,
                    call.arguments,
                    user_message_id,
                )
                record_id = record.id
            except Exception:
                utils.logger.warning("agent tool-call start persistence failed for %s", call.name)
        result = await self._executor.execute(call, context, seen_calls)
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        if self._memory is not None and record_id:
            try:
                await self._memory.complete_tool_call(record_id, result, latency_ms=latency_ms)
            except Exception:
                utils.logger.warning("agent tool-call completion persistence failed for %s", call.name)
        return result

    @staticmethod
    async def _restore_short_term_state(memory: AgentMemory, context: AgentContext) -> AgentContext:
        state = await memory.get_short_term_state(context.conversation_id or "")
        if state is None:
            return context
        updates = {}
        if state.current_job_id:
            updates["current_job_id"] = state.current_job_id
        if state.current_idea_ids:
            updates["current_idea_ids"] = state.current_idea_ids
        if state.current_video_job_id:
            updates["current_video_job_id"] = state.current_video_job_id
        return context.model_copy(update=updates) if updates else context

    @staticmethod
    async def _persist_assistant(memory: AgentMemory, conversation_id: str, response: AgentResponse) -> None:
        try:
            await memory.save_assistant_message(conversation_id, response.answer)
        except Exception:
            utils.logger.warning("agent assistant message persistence failed for %s", conversation_id)

    @staticmethod
    async def _persist_short_term_state(
        memory: AgentMemory, context: AgentContext, response: AgentResponse
    ) -> None:
        if not context.conversation_id:
            return
        try:
            await memory.save_short_term_state(
                context.conversation_id,
                AgentShortTermState(
                    current_job_id=response.job_id or context.current_job_id,
                    current_idea_ids=context.current_idea_ids,
                    current_video_job_id=context.current_video_job_id,
                    last_activity=int(time.time() * 1000),
                ),
            )
        except Exception:
            utils.logger.warning("agent short-term state persistence failed for %s", context.conversation_id)

    @staticmethod
    def _prior_history(messages: list[AgentMessageRecord]) -> list[AgentHistoryMessage]:
        prior = messages[:-1] if messages and messages[-1].role.value == "user" else messages
        return [
            AgentHistoryMessage(role=item.role.value, content=item.content, created_at=item.created_at)
            for item in prior
            if item.role.value in ("user", "assistant")
        ]
