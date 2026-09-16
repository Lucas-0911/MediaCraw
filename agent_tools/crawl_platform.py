# -*- coding: utf-8 -*-
"""Privileged crawler tool that delegates to the existing application service."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_core.contracts import AgentContext, ToolResult, ToolResultStatus
from api.services.crawler_job_service import CrawlerJobService


class CrawlPlatformInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Literal["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu", "tiktok"]
    keyword: str = Field(min_length=1, max_length=256)
    limit: int = Field(default=20, ge=1, le=100)


class CrawlPlatformTool:
    name = "crawl_platform"
    description = "Start an explicit, authorized keyword crawl as an asynchronous job."
    required_permission = "crawler:run"
    requires_quota = True
    input_model = CrawlPlatformInput

    def __init__(self, service: CrawlerJobService) -> None:
        self._service = service

    async def execute(self, arguments: CrawlPlatformInput, context: AgentContext) -> ToolResult:
        job = await self._service.start_keyword_crawl(
            platform=arguments.platform, keyword=arguments.keyword, limit=arguments.limit
        )
        if not job.job_id:
            return ToolResult(
                tool_call_id="",
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error_code="crawl_start_failed",
                message="Crawler job could not be started.",
            )
        return ToolResult(
            tool_call_id="",
            tool_name=self.name,
            status=ToolResultStatus.OK,
            data={"platform": arguments.platform, "keyword": arguments.keyword, "limit": arguments.limit},
            job_id=job.job_id,
            message=job.status,
        )
