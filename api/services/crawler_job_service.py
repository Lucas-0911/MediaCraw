# -*- coding: utf-8 -*-
"""Application-service adapter around the existing CrawlerManager process."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from api.schemas.crawler import CrawlerStartRequest, CrawlerTypeEnum, PlatformEnum
from api.services.crawler_manager import CrawlerManager


@dataclass(frozen=True)
class CrawlJob:
    job_id: str
    status: str


class CrawlerJobService:
    """Starts the existing managed subprocess; it does not implement a crawler."""

    def __init__(self, manager: CrawlerManager) -> None:
        self._manager = manager
        self._current_job_id: str | None = None

    async def start_keyword_crawl(self, platform: str, keyword: str, limit: int) -> CrawlJob:
        if self._manager.process and self._manager.process.poll() is None:
            return CrawlJob(job_id=self._current_job_id or "active-crawler", status="running")

        request = CrawlerStartRequest(
            platform=PlatformEnum(platform),
            crawler_type=CrawlerTypeEnum.SEARCH,
            keywords=keyword,
            max_notes_count=limit,
        )
        started = await self._manager.start(request)
        if not started:
            return CrawlJob(job_id="", status="failed")
        self._current_job_id = uuid4().hex[:12]
        return CrawlJob(job_id=self._current_job_id, status="accepted")
