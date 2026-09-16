# -*- coding: utf-8 -*-
import pathlib
from typing import Dict

import aiofiles

import config
from base.base_crawler import AbstractStoreVideo
from tools import utils


class TikTokVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/tiktok/videos"
        else:
            self.video_store_path = "data/tiktok/videos"

    async def store_video(self, video_content_item: Dict):
        await self.save_video(
            video_content_item.get("aweme_id"),
            video_content_item.get("video_content"),
            video_content_item.get("extension_file_name"),
        )

    def make_save_file_name(self, aweme_id: str, extension_file_name: str) -> str:
        return f"{self.video_store_path}/{aweme_id}/{extension_file_name}"

    async def save_video(self, aweme_id: str, video_content: str, extension_file_name):
        pathlib.Path(self.video_store_path + "/" + aweme_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(aweme_id, extension_file_name)
        async with aiofiles.open(save_file_name, "wb") as f:
            await f.write(video_content)
            utils.logger.info(f"[TikTokVideo.save_video] save video {save_file_name} success ...")
