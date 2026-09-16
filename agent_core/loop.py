# -*- coding: utf-8 -*-
"""Bounded orchestration loop; it owns no crawler or storage business logic."""
from __future__ import annotations

import asyncio
from typing import Set

from config import agent_config

from .contracts import AgentContext, AgentResponse, AgentResponseStatus, ToolResult
from .executor import ToolExecutor
from .llm import AgentLLM
from .registry import ToolRegistry


class AgentLoop:
    def __init__(
        self,
        llm: AgentLLM,
        registry: ToolRegistry,
        *,
        max_steps: int = agent_config.MAX_AGENT_STEPS,
        per_tool_timeout_seconds: float = agent_config.AGENT_TOOL_TIMEOUT_SECONDS,
        request_timeout_seconds: float = agent_config.AGENT_REQUEST_TIMEOUT_SECONDS,
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

    async def run(self, context: AgentContext) -> AgentResponse:
        try:
            return await asyncio.wait_for(self._run(context), timeout=self._request_timeout_seconds)
        except asyncio.TimeoutError:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.TIMEOUT,
                answer="The request timed out before a verified answer was available.",
            )
        except Exception:
            return AgentResponse(
                request_id=context.request_id,
                status=AgentResponseStatus.ERROR,
                answer="The request could not be completed safely.",
            )

    async def _run(self, context: AgentContext) -> AgentResponse:
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
            for call in response.tool_calls:
                results.append(await self._executor.execute(call, context, seen_calls))

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
