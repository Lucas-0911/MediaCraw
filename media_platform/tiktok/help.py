# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""TikTok (Vietnam / international) URL helpers. Guest-friendly public pages."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote, urlparse

from model.m_tiktok import CreatorUrlInfo, VideoUrlInfo


VIDEO_ID_RE = re.compile(r"/video/(\d+)")
AT_USER_RE = re.compile(r"tiktok\.com/@([^/?#]+)", re.I)
SHORT_HOSTS = {"vm.tiktok.com", "vt.tiktok.com", "www.vm.tiktok.com", "www.vt.tiktok.com"}


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("empty TikTok video URL")

    if raw.isdigit():
        return VideoUrlInfo(aweme_id=raw, url_type="id")

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or "").lower()
    if host in SHORT_HOSTS:
        return VideoUrlInfo(aweme_id=raw, unique_id="", url_type="short")

    match = VIDEO_ID_RE.search(raw)
    if not match:
        raise ValueError(f"cannot parse TikTok video id from: {raw}")

    user_match = AT_USER_RE.search(raw)
    unique_id = unquote(user_match.group(1)) if user_match else ""
    return VideoUrlInfo(aweme_id=match.group(1), unique_id=unique_id, url_type="normal")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    raw = (url or "").strip().lstrip("@")
    if not raw:
        raise ValueError("empty TikTok creator URL")

    if "tiktok.com" not in raw and "/" not in raw:
        return CreatorUrlInfo(unique_id=raw)

    if "://" not in raw:
        raw = f"https://{raw}"
    match = AT_USER_RE.search(raw)
    if not match:
        raise ValueError(f"cannot parse TikTok creator from: {raw}")
    return CreatorUrlInfo(unique_id=unquote(match.group(1)))


def _as_play_url(video: Dict[str, Any]) -> str:
    play = video.get("playAddr") or video.get("downloadAddr") or video.get("play_addr") or ""
    if isinstance(play, dict):
        urls = play.get("url_list") or []
        return urls[-1] if urls else ""
    return str(play or "")


def _as_cover_url(video: Dict[str, Any]) -> str:
    cover = video.get("cover") or video.get("originCover") or video.get("dynamicCover") or ""
    if isinstance(cover, dict):
        urls = cover.get("url_list") or []
        return urls[0] if urls else ""
    return str(cover or "")


def normalize_tiktok_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map TikTok itemStruct / search item to a Douyin-like dict for store layer."""
    if not isinstance(item, dict):
        return None
    nested = item.get("item") or item.get("itemStruct")
    if isinstance(nested, dict) and (nested.get("id") or nested.get("aweme_id")):
        item = nested

    aweme_id = str(item.get("id") or item.get("aweme_id") or "")
    if not aweme_id:
        return None

    author = item.get("author") or {}
    stats = item.get("stats") or item.get("statistics") or {}
    video = item.get("video") or {}
    unique_id = str(author.get("uniqueId") or author.get("unique_id") or "")

    return {
        "aweme_id": aweme_id,
        "aweme_type": "video",
        "desc": item.get("desc") or "",
        "create_time": int(item.get("createTime") or item.get("create_time") or 0),
        "author": {
            "uid": str(author.get("id") or author.get("uid") or unique_id),
            "nickname": author.get("nickname") or unique_id,
            "unique_id": unique_id,
        },
        "statistics": {
            "digg_count": stats.get("diggCount") or stats.get("digg_count") or 0,
            "comment_count": stats.get("commentCount") or stats.get("comment_count") or 0,
            "share_count": stats.get("shareCount") or stats.get("share_count") or 0,
            "collect_count": stats.get("collectCount") or stats.get("collect_count") or 0,
            "play_count": stats.get("playCount") or stats.get("play_count") or 0,
        },
        "video": {
            "play_addr": {"url_list": [_as_play_url(video)] if _as_play_url(video) else []},
            "cover": _as_cover_url(video),
        },
        "unique_id": unique_id,
    }


def collect_items_from_search_json(payload: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return items

    for key in ("item_list", "itemList"):
        raw = payload.get(key) or []
        if isinstance(raw, list):
            items.extend(raw)

    data = payload.get("data")
    if isinstance(data, list):
        items.extend(data)

    return [n for n in (normalize_tiktok_item(i) for i in items) if n]


def walk_for_item_structs(obj: Any, acc: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if acc is None:
        acc = []
    stack = [obj]
    seen_ids = set()
    while stack:
        cur = stack.pop()
        marker = id(cur)
        if marker in seen_ids:
            continue
        seen_ids.add(marker)
        if isinstance(cur, dict):
            if cur.get("id") and isinstance(cur.get("author"), dict) and "video" in cur:
                normalized = normalize_tiktok_item(cur)
                if normalized:
                    acc.append(normalized)
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return acc


def parse_universal_data(raw: Optional[str]) -> List[Dict[str, Any]]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return walk_for_item_structs(payload)


def normalize_comment(comment: Dict[str, Any], aweme_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(comment, dict):
        return None
    cid = str(comment.get("cid") or comment.get("comment_id") or comment.get("id") or "")
    if not cid:
        return None
    user = comment.get("user") or comment.get("userInfo") or {}
    return {
        "aweme_id": str(comment.get("aweme_id") or aweme_id),
        "cid": cid,
        "text": comment.get("text") or comment.get("share_info", {}).get("desc") or "",
        "create_time": int(comment.get("create_time") or comment.get("createTime") or 0),
        "digg_count": comment.get("digg_count") or comment.get("diggCount") or comment.get("likeCount") or 0,
        "reply_comment_total": comment.get("reply_comment_total") or comment.get("replyCommentTotal") or 0,
        "reply_id": str(comment.get("reply_id") or comment.get("replyId") or "0"),
        "user": {
            "uid": str(user.get("uid") or user.get("id") or ""),
            "nickname": user.get("nickname") or user.get("uniqueId") or "",
        },
    }


def collect_comments_from_json(payload: Any, aweme_id: str) -> List[Dict[str, Any]]:
    comments: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return comments
    raw_list: Iterable = payload.get("comments") or payload.get("comment_list") or []
    if isinstance(raw_list, list):
        for row in raw_list:
            normalized = normalize_comment(row, aweme_id)
            if normalized:
                comments.append(normalized)
    return comments
