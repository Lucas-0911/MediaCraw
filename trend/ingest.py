# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, Optional

from trend.extract import ProductMention, extract_int, extract_mentions, extract_play_count
from trend.llm_extract import llm_guess_product
from trend.store import TrendStore

INTENT_RE = re.compile(
    r"(想买|求链接|多少钱|下单|同款|链接|怎么买|mua|giá|link shop|order|add to cart)",
    re.IGNORECASE,
)


def comment_is_intent(text: str) -> bool:
    return bool(INTENT_RE.search(text or ""))


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def ingest_aweme(platform: str, aweme_item: Dict, saved: Optional[Dict] = None) -> None:
    saved = saved or {}
    mentions = extract_mentions(aweme_item, saved)
    if not mentions:
        guessed = await llm_guess_product(saved.get("desc") or aweme_item.get("desc") or "")
        if guessed:
            mentions = [guessed]
    if not mentions:
        return

    store = TrendStore()
    play_count = extract_play_count(aweme_item, saved)
    stats = aweme_item.get("statistics") or {}
    like_count = extract_int(saved, "liked_count") or extract_int(stats, "digg_count", "like_count")
    comment_count = extract_int(saved, "comment_count") or extract_int(stats, "comment_count")
    share_count = extract_int(saved, "share_count") or extract_int(stats, "share_count")
    industry = saved.get("source_keyword") or ""

    for mention in mentions:
        await store.upsert_product(
            product_key=mention.product_key,
            name=mention.name,
            product_id=mention.product_id,
            identity_type=mention.identity_type,
            industry=industry,
        )
        await store.upsert_video(
            {
                "aweme_id": str(saved.get("aweme_id") or aweme_item.get("aweme_id") or ""),
                "platform": platform,
                "product_key": mention.product_key,
                "creator_hash": saved.get("creator_hash") or "",
                "play_count": play_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "share_count": share_count,
                "create_time": _to_int(saved.get("create_time") or aweme_item.get("create_time")),
                "url": saved.get("aweme_url") or "",
                "download_url": saved.get("video_download_url") or "",
                "desc": saved.get("desc") or aweme_item.get("desc") or "",
                "source_keyword": industry,
            }
        )


async def ingest_comment(platform: str, aweme_id: str, comment_item: Dict, saved: Optional[Dict] = None) -> None:
    saved = saved or {}
    content = saved.get("content") or comment_item.get("text") or comment_item.get("content") or ""
    comment_id = str(saved.get("comment_id") or comment_item.get("cid") or "")
    if not comment_id:
        return
    store = TrendStore()
    await store.upsert_comment(
        {
            "comment_id": comment_id,
            "aweme_id": str(aweme_id),
            "platform": platform,
            "content": content,
            "like_count": _to_int(saved.get("like_count") or comment_item.get("digg_count")),
            "is_intent": 1 if comment_is_intent(content) else 0,
        }
    )
