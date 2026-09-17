# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from pathlib import Path
from typing import Any, Dict, List

import httpx

from trend.settings import get_settings
from trend.store import TrendStore


async def download_videos(videos: List[Dict[str, Any]], store: TrendStore | None = None) -> List[str]:
    settings = get_settings()
    if not settings.get("TREND_DOWNLOAD_MEDIA"):
        return []
    limit = int(settings.get("TREND_MAX_MEDIA_PER_SCAN") or 20)
    store = store or TrendStore()
    saved: List[str] = []
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for video in videos[:limit]:
            url = video.get("download_url") or ""
            if not url:
                continue
            platform = video.get("platform") or "dy"
            aweme_id = str(video.get("aweme_id") or "")
            if not aweme_id:
                continue
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
            except Exception:
                continue
            folder = Path("data") / ("douyin" if platform in ("dy", "douyin") else "tiktok") / "videos" / aweme_id
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / f"{aweme_id}.mp4"
            dest.write_bytes(resp.content)
            path = str(dest)
            await store.set_media_path(aweme_id, platform, path)
            saved.append(path)
    return saved
