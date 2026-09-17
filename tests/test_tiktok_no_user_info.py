# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""TikTok store privacy: no raw uid / unique_id / avatar in persisted dict."""
import asyncio

import pytest

import store.tiktok as ts
from database.models import TiktokAweme, TiktokAwemeComment
from tools.user_hash import anonymize_user_id, mask_nickname

FORBIDDEN_KEYS = {
    "user_id", "sec_uid", "short_user_id", "user_unique_id",
    "avatar", "user_signature", "ip_location", "unique_id",
}


def _aweme():
    return {
        "aweme_id": "7123456789012345678",
        "aweme_type": "video",
        "desc": "Phở bò Hà Nội",
        "create_time": 1700000000,
        "author": {
            "uid": "9876543210",
            "nickname": "Ẩm thực Việt",
            "unique_id": "amthuc_viet",
        },
        "statistics": {
            "digg_count": 11,
            "collect_count": 2,
            "comment_count": 3,
            "share_count": 1,
        },
        "video": {
            "play_addr": {"url_list": ["http://cdn/video.mp4"]},
            "cover": "http://cdn/cover.jpg",
        },
    }


def _comment():
    return {
        "aweme_id": "7123456789012345678",
        "cid": "cmt-1",
        "text": "muốn ăn quá",
        "create_time": 1700000001,
        "reply_id": "0",
        "reply_comment_total": 0,
        "digg_count": 2,
        "user": {"uid": "555", "nickname": "Bạn An"},
    }


class _FakeStore:
    def __init__(self):
        self.contents = []
        self.comments = []

    async def store_content(self, content_item):
        self.contents.append(dict(content_item))

    async def store_comment(self, comment_item):
        self.comments.append(dict(comment_item))


def test_tiktok_aweme_masks_user_info():
    aweme = _aweme()
    fake = _FakeStore()
    orig = ts.TiktokStoreFactory.create_store
    ts.TiktokStoreFactory.create_store = staticmethod(lambda: fake)
    try:
        asyncio.run(ts.update_tiktok_aweme(aweme))
    finally:
        ts.TiktokStoreFactory.create_store = orig

    captured = fake.contents[0]
    assert not (set(captured) & FORBIDDEN_KEYS)
    assert captured["creator_hash"] == anonymize_user_id("9876543210")
    assert captured["nickname"] == mask_nickname("Ẩm thực Việt")
    assert captured["nickname"] != "Ẩm thực Việt"
    assert captured["desc"] == "Phở bò Hà Nội"
    assert captured["cover_url"] == "http://cdn/cover.jpg"
    assert captured["video_download_url"] == "http://cdn/video.mp4"
    assert "amthuc_viet" not in str(captured.values())
    assert "9876543210" not in str(captured.values())
    TiktokAweme(**captured)


def test_tiktok_comment_masks_user_info():
    comment = _comment()
    fake = _FakeStore()
    orig = ts.TiktokStoreFactory.create_store
    ts.TiktokStoreFactory.create_store = staticmethod(lambda: fake)
    try:
        asyncio.run(ts.update_tiktok_aweme_comment("7123456789012345678", comment))
    finally:
        ts.TiktokStoreFactory.create_store = orig

    captured = fake.comments[0]
    assert not (set(captured) & FORBIDDEN_KEYS)
    assert captured["creator_hash"] == anonymize_user_id("555")
    assert captured["nickname"] == mask_nickname("Bạn An")
    assert captured["content"] == "muốn ăn quá"
    TiktokAwemeComment(**captured)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
