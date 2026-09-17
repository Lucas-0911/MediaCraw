# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from typing import Dict, List

import config
from base.base_crawler import AbstractStore
from var import source_keyword_var
from tools import utils
from tools.user_hash import anonymize_user_id, mask_nickname

from ._store_impl import *
from .tiktok_store_media import *


class TiktokStoreFactory:
    STORES = {
        "csv": TiktokCsvStoreImplement,
        "db": TiktokDbStoreImplement,
        "postgres": TiktokDbStoreImplement,
        "json": TiktokJsonStoreImplement,
        "jsonl": TiktokJsonlStoreImplement,
        "sqlite": TiktokSqliteStoreImplement,
        "mongodb": TiktokMongoStoreImplement,
        "excel": TiktokExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = TiktokStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[TiktokStoreFactory.create_store] Invalid save option "
                "only supported csv or db or json or sqlite or mongodb or excel ..."
            )
        return store_class()


def _extract_content_cover_url(aweme_detail: Dict) -> str:
    video_item = aweme_detail.get("video", {}) or {}
    cover = video_item.get("cover")
    if isinstance(cover, str):
        return cover
    if isinstance(cover, dict):
        urls = cover.get("url_list") or []
        return urls[0] if urls else ""
    raw = video_item.get("raw_cover") or video_item.get("origin_cover") or {}
    if isinstance(raw, dict):
        urls = raw.get("url_list") or []
        if urls:
            return urls[-1]
    return ""


def _extract_video_download_url(aweme_detail: Dict) -> str:
    video_item = aweme_detail.get("video", {}) or {}
    play = video_item.get("play_addr") or {}
    if isinstance(play, str):
        return play
    urls = play.get("url_list") or []
    return urls[-1] if urls else ""


async def update_tiktok_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {}) or {}
    interact_info = aweme_item.get("statistics", {}) or {}
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type") or "video"),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "create_time": aweme_item.get("create_time"),
        "creator_hash": anonymize_user_id(user_info.get("uid")),
        "nickname": mask_nickname(user_info.get("nickname")),
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.tiktok.com/video/{aweme_id}",
        "cover_url": _extract_content_cover_url(aweme_item),
        "video_download_url": _extract_video_download_url(aweme_item),
        "music_download_url": "",
        "note_download_url": "",
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(
        f"[store.tiktok.update_tiktok_aweme] tiktok aweme id:{aweme_id}, title:{save_content_item.get('title')}"
    )
    await TiktokStoreFactory.create_store().store_content(content_item=save_content_item)
    try:
        from trend.ingest import ingest_aweme
        await ingest_aweme("tiktok", aweme_item, save_content_item)
    except Exception as exc:
        utils.logger.warning(f"[store.tiktok] trend ingest aweme failed: {exc}")


async def batch_update_tiktok_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_tiktok_aweme_comment(aweme_id, comment_item)


async def update_tiktok_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = str(comment_item.get("aweme_id") or aweme_id)
    if str(aweme_id) != comment_aweme_id:
        utils.logger.error(
            f"[store.tiktok.update_tiktok_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}"
        )
        return
    user_info = comment_item.get("user", {}) or {}
    comment_id = comment_item.get("cid")
    parent_comment_id = comment_item.get("reply_id", "0")
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "creator_hash": anonymize_user_id(user_info.get("uid")),
        "nickname": mask_nickname(user_info.get("nickname")),
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),
        "like_count": (comment_item.get("digg_count") if comment_item.get("digg_count") else 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "parent_comment_id": parent_comment_id,
        "pictures": "",
    }
    utils.logger.info(
        f"[store.tiktok.update_tiktok_aweme_comment] tiktok comment: {comment_id}, content: {save_comment_item.get('content')}"
    )
    await TiktokStoreFactory.create_store().store_comment(comment_item=save_comment_item)
    try:
        from trend.ingest import ingest_comment
        await ingest_comment("tiktok", aweme_id, comment_item, save_comment_item)
    except Exception as exc:
        utils.logger.warning(f"[store.tiktok] trend ingest comment failed: {exc}")


async def save_creator(user_id: str, creator: Dict):
    return


async def update_tiktok_aweme_video(aweme_id, video_content, extension_file_name):
    await TikTokVideo().store_video(
        {"aweme_id": aweme_id, "video_content": video_content, "extension_file_name": extension_file_name}
    )
