# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from typing import List
from urllib.parse import quote

import httpx

from trend.settings import get_settings


async def fetch_search_cn(keyword: str) -> str:
    settings = get_settings()
    if not settings.get("TREND_GOOGLE_TRENDS_ENABLED"):
        return "unknown"
    query = (keyword or "").strip()
    if not query:
        return "unknown"
    url = "https://trends.google.com/trends/api/explore"
    params = {
        "hl": "en-US",
        "tz": "-480",
        "geo": "CN",
        "q": query,
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 TrendRadar/1.0"},
            )
            if resp.status_code >= 400:
                return "unknown"
            text = resp.text
    except Exception:
        return "unknown"
    lowered = text.lower()
    if "rising" in lowered:
        return "rising"
    if "breakout" in lowered:
        return "rising"
    if query.lower() in lowered:
        return "flat"
    return "unknown"


def search_url(keyword: str) -> str:
    return f"https://trends.google.com/trends/explore?geo=CN&q={quote(keyword)}"


def classify_delta(recent: List[float], previous: List[float]) -> str:
    if not recent or not previous:
        return "unknown"
    r = sum(recent) / len(recent)
    p = sum(previous) / len(previous)
    if p <= 0:
        return "rising" if r > 0 else "unknown"
    change = (r - p) / p
    if change >= 0.15:
        return "rising"
    if change <= -0.15:
        return "falling"
    return "flat"
