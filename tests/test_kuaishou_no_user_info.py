# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""
教学版回归测试：快手(kuaishou)存储链路不再持久化可定位真人的用户个人信息。

覆盖：
1. update_kuaishou_video —— mock video_item(含 author.id/name/headerUrl + photo 内容字段 + type)
   经 FakeStore 捕获，断言捕获 dict 不含禁用键(user_id/avatar/signature/ip_location/gender)、
   含 creator_hash(≠原 user_id)、nickname 脱敏(≠原文)。
2. update_ks_video_comment —— V2(snake_case) 与旧 GraphQL(camelCase) 两种 comment_item 格式各测一次。
3. test_kuaishou_store_end_to_end_sqlite —— 端到端：FakeStore 捕获真实 dict ->
   KuaishouVideo(**captured) 触发 ORM 列校验 -> 写入内存 SQLite -> 查询回读校验属性。

约束：只新建本测试文件，只读源码不改源码；不依赖网络/登录。
"""
import asyncio
import contextlib
import types

import pytest

import store.kuaishou as ks
from store.kuaishou import update_kuaishou_video, update_ks_video_comment
from tools.user_hash import anonymize_user_id, mask_nickname

# Forbidden keys must not appear in storage dicts.
# nickname may remain if the value is masked.
FORBIDDEN_KEYS = {"user_id", "avatar", "signature", "ip_location", "gender"}

# ----------------------------- mock data -----------------------------

MOCK_VIDEO_ID = "3xf8e9kq2b7w4"
MOCK_AUTHOR_ID = "ks_author_001"
MOCK_AUTHOR_NAME = "快手达人"
MOCK_CAPTION = "这是一条测试视频，教学版脱敏回归 #测试"

# Comment authors use different ids/nicknames per format for assertions
MOCK_COMMENT_V2_AUTHOR_ID = "ks_user_888"
MOCK_COMMENT_V2_AUTHOR_NAME = "快手老铁"
MOCK_COMMENT_LEGACY_AUTHOR_ID = "ks_user_777"
MOCK_COMMENT_LEGACY_AUTHOR_NAME = "快乐源泉"


def make_mock_video() -> dict:
    """video_item shaped like Kuaishou: author at top level, photo holds content fields.
    author.headerUrl must not enter the storage dict, like other forbidden fields."""
    return {
        "type": 1,
        "photo": {
            "id": MOCK_VIDEO_ID,
            "caption": MOCK_CAPTION,
            "timestamp": 1700000000000,
            "coverUrl": "https://p.kuaishou.com/cover/abc.jpg",
            "photoUrl": "https://v.kuaishou.com/play/abc.mp4",
            "realLikeCount": 12345,
            "viewCount": 67890,
        },
        "author": {
            "id": MOCK_AUTHOR_ID,
            "name": MOCK_AUTHOR_NAME,
            "headerUrl": "https://p.kuaishou.com/header/u001.jpg",
        },
    }


def make_mock_comment_v2() -> dict:
    """V2 API format: snake_case fields, comment_id is int."""
    return {
        "comment_id": 9001,
        "timestamp": 1700000001234,
        "content": "太搞笑了哈哈哈",
        "author_id": MOCK_COMMENT_V2_AUTHOR_ID,
        "author_name": MOCK_COMMENT_V2_AUTHOR_NAME,
        "headurl": "https://p.kuaishou.com/header/u888.jpg",
        "commentCount": 7,
    }


def make_mock_comment_legacy() -> dict:
    """Legacy GraphQL API format: camelCase fields."""
    return {
        "commentId": 8001,
        "timestamp": 1700000005678,
        "content": "这条评论来自旧 GraphQL 接口",
        "authorId": MOCK_COMMENT_LEGACY_AUTHOR_ID,
        "authorName": MOCK_COMMENT_LEGACY_AUTHOR_NAME,
        "headurl": "https://p.kuaishou.com/header/u777.jpg",
        "subCommentCount": 3,
    }


# ----------------------------- FakeStore capture -----------------------------


@contextlib.contextmanager
def _patch_create_store():
    """Replace KuaishouStoreFactory.create_store with a capturing FakeStore staticmethod.
    FakeStore 把 store_content/store_comment 收到的 dict 原样写入 holder.content / holder.comment。

    保存/还原走类 __dict__ 中的 staticmethod 描述符本身，避免把 staticmethod 退化为普通方法
    and pollute later tests."""
    holder = types.SimpleNamespace(content={}, comment={})

    class FakeStore:
        async def store_content(self, content_item):
            holder.content.clear()
            holder.content.update(content_item)

        async def store_comment(self, comment_item):
            holder.comment.clear()
            holder.comment.update(comment_item)

        async def store_creator(self, creator):
            pass

    orig = ks.KuaishouStoreFactory.__dict__["create_store"]
    ks.KuaishouStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        yield holder
    finally:
        ks.KuaishouStoreFactory.create_store = orig


def _assert_no_forbidden_keys(d: dict, label: str):
    hit = set(d.keys()) & FORBIDDEN_KEYS
    assert not hit, f"[{label}] 输出仍含禁用字段键: {hit}"


# ----------------------------- tests -----------------------------


def test_kuaishou_video_masks_user_info():
    """Video path: hash user_id, mask nickname, drop headerUrl and forbidden keys."""
    with _patch_create_store() as holder:
        asyncio.run(update_kuaishou_video(make_mock_video()))
    captured = holder.content

    assert captured, "FakeStore 未捕获到 content_item"
    _assert_no_forbidden_keys(captured, "kuaishou_video")
    # Avatar fields must not enter the storage dict (author.headerUrl is dropped)
    assert "headerUrl" not in captured and "avatar" not in captured

    # creator_hash exists and is not the raw user_id
    assert captured.get("creator_hash") == anonymize_user_id(MOCK_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_AUTHOR_ID
    assert captured["creator_hash"]  # 非空

    # Nickname is masked: equals mask_nickname(original) and is not the original
    assert captured.get("nickname") == mask_nickname(MOCK_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_AUTHOR_NAME
    assert "*" in captured["nickname"]

    # Content fields are kept(video_id / desc / title)
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["desc"] == MOCK_CAPTION
    assert captured["title"] == MOCK_CAPTION
    # video_type comes from video_item.type and is str()'d
    assert captured["video_type"] == "1"
    # Count fields are str()'d
    assert captured["liked_count"] == "12345"
    assert captured["viewd_count"] == "67890"


def test_kuaishou_comment_v2_masks_user_info():
    """Comment V2 (snake_case): anonymize author_id/author_name; do not store headurl."""
    with _patch_create_store() as holder:
        asyncio.run(update_ks_video_comment(MOCK_VIDEO_ID, make_mock_comment_v2()))
    captured = holder.comment

    assert captured, "FakeStore 未捕获到 comment_item"
    _assert_no_forbidden_keys(captured, "kuaishou_comment_v2")
    assert "headurl" not in captured and "avatar" not in captured

    # comment_id is converted from int to str
    assert captured["comment_id"] == "9001"
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["content"] == "太搞笑了哈哈哈"
    # V2 uses commentCount
    assert captured["sub_comment_count"] == "7"

    # creator_hash / nickname
    assert captured["creator_hash"] == anonymize_user_id(MOCK_COMMENT_V2_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_COMMENT_V2_AUTHOR_ID
    assert captured["nickname"] == mask_nickname(MOCK_COMMENT_V2_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_COMMENT_V2_AUTHOR_NAME
    assert "*" in captured["nickname"]


def test_kuaishou_comment_legacy_masks_user_info():
    """Legacy GraphQL comments (camelCase): anonymize authorId/authorName; do not store headurl."""
    with _patch_create_store() as holder:
        asyncio.run(update_ks_video_comment(MOCK_VIDEO_ID, make_mock_comment_legacy()))
    captured = holder.comment

    assert captured, "FakeStore 未捕获到 comment_item"
    _assert_no_forbidden_keys(captured, "kuaishou_comment_legacy")
    assert "headurl" not in captured and "avatar" not in captured

    # commentId is converted from int to str
    assert captured["comment_id"] == "8001"
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["content"] == "这条评论来自旧 GraphQL 接口"
    # Legacy format uses subCommentCount
    assert captured["sub_comment_count"] == "3"

    # creator_hash / nickname
    assert captured["creator_hash"] == anonymize_user_id(MOCK_COMMENT_LEGACY_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_COMMENT_LEGACY_AUTHOR_ID
    assert captured["nickname"] == mask_nickname(MOCK_COMMENT_LEGACY_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_COMMENT_LEGACY_AUTHOR_NAME
    assert "*" in captured["nickname"]


def test_kuaishou_store_end_to_end_sqlite():
    """End-to-end: FakeStore captures the dict, then KuaishouVideo(**captured) validates ORM columns
    -> 写入内存 SQLite -> 查询回读，验证属性正确且无禁用列。

    全程在同一个事件循环内完成(aiosqlite 连接绑定事件循环，跨 loop 会报错)，
    Do not patch db_session.get_session; use a local memory engine for ORM write/read."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from database.models import Base, KuaishouVideo, KuaishouVideoComment

    async def run():
        # In-memory SQLite + StaticPool so create_all and later IO share one connection
        engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
        SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[KuaishouVideo.__table__, KuaishouVideoComment.__table__],
            )

        # 1) update_kuaishou_video produces the storage dict (FakeStore capture)
        with _patch_create_store() as holder:
            await update_kuaishou_video(make_mock_video())
        captured = holder.content
        assert captured, "FakeStore 未捕获到 content_item"

        # 2) ORM column check: every captured key must be a KuaishouVideo column,
        #    otherwise KuaishouVideo(**captured) raises TypeError (forbidden extra keys are a bug)
        valid_cols = {c.name for c in KuaishouVideo.__table__.columns}
        assert set(captured.keys()) <= valid_cols, (
            f"captured 含非合法列: {set(captured.keys()) - valid_cols}"
        )
        obj = KuaishouVideo(**captured)  # 不抛异常即通过列校验
        assert obj.video_id == MOCK_VIDEO_ID
        assert obj.creator_hash == anonymize_user_id(MOCK_AUTHOR_ID)
        assert obj.creator_hash != MOCK_AUTHOR_ID
        assert obj.nickname == mask_nickname(MOCK_AUTHOR_NAME)
        assert obj.nickname != MOCK_AUTHOR_NAME
        assert obj.desc == MOCK_CAPTION  # 内容保留

        # 3) Real write + read-back query
        async with SessionFactory() as session:
            session.add(obj)
            await session.commit()

            res = await session.execute(
                select(KuaishouVideo).where(KuaishouVideo.video_id == MOCK_VIDEO_ID)
            )
            row = res.scalar_one()
            assert row is not None
            assert row.video_id == MOCK_VIDEO_ID
            assert row.creator_hash == anonymize_user_id(MOCK_AUTHOR_ID)
            assert row.creator_hash != MOCK_AUTHOR_ID
            assert row.nickname == mask_nickname(MOCK_AUTHOR_NAME)
            assert row.nickname != MOCK_AUTHOR_NAME
            # Content fields are kept
            assert row.desc == MOCK_CAPTION
            assert row.title == MOCK_CAPTION
            # ORM row objects must not have forbidden column attributes
            for bad in FORBIDDEN_KEYS:
                assert not hasattr(row, bad), f"KuaishouVideo 行对象仍含禁用属性: {bad}"

        await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
