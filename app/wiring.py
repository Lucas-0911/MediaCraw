# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Wire AgentLoop, tools, memory, and the Telegram adapter. No crawler logic lives here."""
from __future__ import annotations

from agent.core.llm import OpenAICompatibleAgentLLM
from agent.core.loop import AgentLoop
from agent.core.registry import ToolRegistry
from agent.memory import AgentMemoryService, create_agent_memory
from agent.tools.crawl_platform import CrawlPlatformTool
from agent.tools.search_crawl_results import SearchCrawlResultsTool
from channels.telegram.adapter import LegacyCommandHandler, TelegramAgentHandler
from channels.telegram.auth import TelegramUserResolver
from services.crawl_result_service import CrawlResultService
from services.crawler_job_service import CrawlerJobService
from services.crawler_manager import crawler_manager


def build_tool_registry(
    crawl_results: CrawlResultService | None = None,
    crawler_jobs: CrawlerJobService | None = None,
) -> ToolRegistry:
    results = crawl_results or CrawlResultService()
    jobs = crawler_jobs or CrawlerJobService(crawler_manager)
    return ToolRegistry(
        [
            SearchCrawlResultsTool(results),
            CrawlPlatformTool(jobs),
        ]
    )


async def build_memory() -> AgentMemoryService:
    return await create_agent_memory()


def build_agent_loop(
    registry: ToolRegistry | None = None,
    memory: AgentMemoryService | None = None,
    llm: OpenAICompatibleAgentLLM | None = None,
) -> AgentLoop:
    return AgentLoop(
        llm or OpenAICompatibleAgentLLM(),
        registry or build_tool_registry(),
        memory=memory,
    )


def build_telegram_handler(
    command_handler: LegacyCommandHandler,
    user_resolver: TelegramUserResolver,
    agent_loop: AgentLoop | None = None,
    memory: AgentMemoryService | None = None,
) -> TelegramAgentHandler:
    loop = agent_loop or build_agent_loop(memory=memory)
    return TelegramAgentHandler(command_handler, user_resolver, loop)
