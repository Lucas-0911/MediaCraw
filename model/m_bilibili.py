# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.



# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class VideoUrlInfo(BaseModel):
    """Bilibili video URL information"""
    video_id: str = Field(title="video id (BV id)")
    video_type: str = Field(default="video", title="video type")


class CreatorUrlInfo(BaseModel):
    """Bilibili creator URL information"""
    creator_id: str = Field(title="creator id (UID)")
