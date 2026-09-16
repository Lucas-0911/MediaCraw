# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class VideoUrlInfo(BaseModel):
    aweme_id: str = Field(title="video id")
    unique_id: str = Field(default="", title="creator uniqueId")
    url_type: str = Field(default="normal", title="normal | short | id")


class CreatorUrlInfo(BaseModel):
    unique_id: str = Field(title="TikTok uniqueId / @handle")
