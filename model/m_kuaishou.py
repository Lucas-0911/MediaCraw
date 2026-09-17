# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from pydantic import BaseModel, Field


class VideoUrlInfo(BaseModel):
    """Kuaishou video URL information"""
    video_id: str = Field(title="video id (photo id)")
    url_type: str = Field(default="normal", title="url type: normal")


class CreatorUrlInfo(BaseModel):
    """Kuaishou creator URL information"""
    user_id: str = Field(title="user id (creator id)")
