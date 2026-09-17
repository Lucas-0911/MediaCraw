# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

HASHTAG_RE = re.compile(r"[#＃]([^\s#＃]{2,40})")
NOISE_TAGS = {
    "fyp", "foryou", "viral", "trending", "duet", "capcut",
    "douyin", "tiktok", "推荐", "热门", "抖音", "视频",
}
PRODUCT_HINTS = ("种草", "测评", "开箱", "好物", "链接", "同款", "unbox", "review", "haolang")
SKIP_NAME_RE = re.compile(r"^[\d\W_]+$")
PUNCT_RE = re.compile(r"[^\w\u4e00-\u9fff\u00c0-\u024f]+", re.UNICODE)

PRODUCT_ID_KEYS = (
    "product_id", "productId", "promotion_id", "promotionId",
    "commodity_id", "goods_id", "item_id",
)
PRODUCT_NAME_KEYS = (
    "product_name", "productName", "title", "desc",
    "product_title", "commodity_name", "goods_name", "name",
)


@dataclass
class ProductMention:
    product_key: str
    name: str
    product_id: Optional[str] = None
    identity_type: str = "hashtag"
    source: str = "desc"


def normalize_name(raw: str) -> str:
    text = (raw or "").strip()
    for hint in PRODUCT_HINTS:
        text = text.replace(hint, " ")
    text = PUNCT_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def product_key_for(product_id: Optional[str], name: str) -> str:
    if product_id:
        return f"sku:{product_id}"
    return f"name:{normalize_name(name)}"


def _as_dict(value: Any) -> Dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _walk(obj: Any) -> Iterable[Dict]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def extract_anchor_product(aweme: Dict) -> Optional[Tuple[str, str]]:
    candidates = [
        aweme.get("anchor_info"),
        aweme.get("anchor"),
        aweme.get("commerce_info"),
        aweme.get("commerce_config"),
        aweme.get("promotion_info"),
        aweme.get("video_tag"),
    ]
    extra = aweme.get("anchor_info") or {}
    if isinstance(extra, dict):
        candidates.append(_as_dict(extra.get("extra")))
        candidates.append(_as_dict(extra.get("content")))
    for node in candidates:
        for item in _walk(node):
            pid = None
            for key in PRODUCT_ID_KEYS:
                if item.get(key):
                    pid = str(item.get(key))
                    break
            if not pid:
                continue
            name = ""
            for key in PRODUCT_NAME_KEYS:
                if item.get(key):
                    name = str(item.get(key)).strip()
                    break
            if not name:
                name = pid
            return pid, name
    return None


def extract_hashtags(aweme: Dict, desc: str = "") -> List[str]:
    tags: List[str] = []
    text = desc or aweme.get("desc") or aweme.get("title") or ""
    tags.extend(HASHTAG_RE.findall(text))
    extra = aweme.get("text_extra") or aweme.get("cha_list") or []
    if isinstance(extra, list):
        for item in extra:
            if not isinstance(item, dict):
                continue
            name = item.get("hashtag_name") or item.get("cha_name") or item.get("name")
            if name:
                tags.append(str(name))
    cleaned = []
    seen = set()
    for tag in tags:
        norm = normalize_name(tag)
        if not norm or norm in seen or norm in NOISE_TAGS or SKIP_NAME_RE.match(norm):
            continue
        if len(norm) < 2:
            continue
        seen.add(norm)
        cleaned.append(tag.strip())
    return cleaned


def extract_mentions(aweme: Dict, saved: Optional[Dict] = None) -> List[ProductMention]:
    saved = saved or {}
    desc = saved.get("desc") or aweme.get("desc") or saved.get("title") or ""
    mentions: List[ProductMention] = []

    anchor = extract_anchor_product(aweme)
    if anchor:
        pid, name = anchor
        mentions.append(
            ProductMention(
                product_key=product_key_for(pid, name),
                name=name,
                product_id=pid,
                identity_type="xiaohuangche",
                source="anchor",
            )
        )
        return mentions

    for tag in extract_hashtags(aweme, desc):
        mentions.append(
            ProductMention(
                product_key=product_key_for(None, tag),
                name=tag.strip("#＃ "),
                identity_type="hashtag",
                source="hashtag",
            )
        )
    if mentions:
        return mentions

    hinted = any(h in desc for h in PRODUCT_HINTS)
    if hinted:
        snippet = desc.strip()
        if len(snippet) > 40:
            snippet = snippet[:40]
        name = normalize_name(snippet)
        if name and len(name) >= 4:
            mentions.append(
                ProductMention(
                    product_key=product_key_for(None, name),
                    name=snippet,
                    identity_type="hint",
                    source="desc",
                )
            )
    return mentions


def extract_play_count(aweme: Dict, saved: Optional[Dict] = None) -> int:
    saved = saved or {}
    stats = aweme.get("statistics") or {}
    for source in (saved, stats, aweme):
        if not isinstance(source, dict):
            continue
        for key in ("play_count", "playCount", "aweme_play_count", "view_count", "play"):
            value = source.get(key)
            if value is None or value == "":
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return 0


def extract_int(source: Dict, *keys: str) -> int:
    for key in keys:
        value = source.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0
