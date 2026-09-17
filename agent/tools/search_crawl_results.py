# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Read-only search tool backed by the crawl-result application service."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent.core.contracts import AgentContext, ToolResult, ToolResultStatus
from services.crawl_result_service import CrawlResultService


class SearchCrawlResultsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu", "tiktok"]
    keyword: str = Field(min_length=1, max_length=256)
    limit: int = Field(default=20, ge=1, le=100)


class SearchCrawlResultsTool:
    name = "search_crawl_results"
    description = "Search existing persisted crawl results. It never starts a crawler."
    required_permission = "crawl_results:read"
    input_model = SearchCrawlResultsInput

    def __init__(self, service: CrawlResultService) -> None:
        self._service = service

    async def execute(
        self, arguments: SearchCrawlResultsInput, context: AgentContext
    ) -> ToolResult:
        records = await self._service.search(
            platform=arguments.platform,
            keyword=arguments.keyword,
            limit=arguments.limit,
        )
        status = ToolResultStatus.OK if records else ToolResultStatus.EMPTY
        return ToolResult(
            tool_call_id="",  # ToolExecutor binds this to the LLM call identity.
            tool_name=self.name,
            status=status,
            data={
                "platform": arguments.platform,
                "keyword": arguments.keyword,
                "records": records,
                "count": len(records),
            },
        )
