# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from typing import Dict

from sqlalchemy import select

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import TiktokAweme, TiktokAwemeComment
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var
from database.mongodb_store_base import MongoDBStoreBase


class TiktokCsvStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok",
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_csv(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_csv(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_csv(item=creator, item_type="creators")


class TiktokDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        aweme_id = content_item.get("aweme_id")
        async with get_session() as session:
            result = await session.execute(select(TiktokAweme).where(TiktokAweme.aweme_id == aweme_id))
            aweme_detail = result.scalar_one_or_none()
            if not aweme_detail:
                content_item["add_ts"] = utils.get_current_timestamp()
                if content_item.get("title"):
                    session.add(TiktokAweme(**content_item))
            else:
                for key, value in content_item.items():
                    setattr(aweme_detail, key, value)
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        async with get_session() as session:
            result = await session.execute(
                select(TiktokAwemeComment).where(TiktokAwemeComment.comment_id == comment_id)
            )
            comment_detail = result.scalar_one_or_none()
            if not comment_detail:
                comment_item["add_ts"] = utils.get_current_timestamp()
                session.add(TiktokAwemeComment(**comment_item))
            else:
                for key, value in comment_item.items():
                    setattr(comment_detail, key, value)
            await session.commit()

    async def store_creator(self, creator: Dict):
        pass


class TiktokJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok",
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_single_item_to_json(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_single_item_to_json(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_single_item_to_json(item=creator, item_type="creators")


class TiktokJsonlStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="tiktok",
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_jsonl(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_jsonl(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_jsonl(item=creator, item_type="creators")


class TiktokSqliteStoreImplement(TiktokDbStoreImplement):
    pass


class TiktokMongoStoreImplement(AbstractStore):
    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="tiktok")

    async def store_content(self, content_item: Dict):
        aweme_id = content_item.get("aweme_id")
        if not aweme_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"aweme_id": aweme_id},
            data=content_item,
        )

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item,
        )

    async def store_creator(self, creator_item: Dict):
        pass


class TiktokExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase

        return ExcelStoreBase.get_instance(
            platform="tiktok",
            crawler_type=crawler_type_var.get(),
        )
