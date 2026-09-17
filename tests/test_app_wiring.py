# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from agent.core.loop import AgentLoop
from agent.tools.crawl_platform import CrawlPlatformTool
from agent.tools.search_crawl_results import SearchCrawlResultsTool
from app.wiring import build_agent_loop, build_telegram_handler, build_tool_registry
from channels.telegram.adapter import TelegramAgentHandler
from channels.telegram.contracts import TelegramMessageResponse, TelegramUpdate, TelegramUser


class _Legacy:
    async def handle(self, update):
        return TelegramMessageResponse(text="legacy")


class _Resolver:
    async def resolve(self, update):
        return TelegramUser(user_id="u1", authenticated=True, license="active")


def test_tool_registry_exposes_search_and_crawl():
    registry = build_tool_registry()
    assert registry.get(SearchCrawlResultsTool.name) is not None
    assert registry.get(CrawlPlatformTool.name) is not None


def test_wiring_builds_telegram_handler_without_memory():
    loop = build_agent_loop()
    assert isinstance(loop, AgentLoop)
    handler = build_telegram_handler(_Legacy(), _Resolver(), agent_loop=loop)
    assert isinstance(handler, TelegramAgentHandler)
