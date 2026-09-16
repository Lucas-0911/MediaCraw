# -*- coding: utf-8 -*-
"""Safe Telegram boundary DTOs; no bot SDK is required here."""
from __future__ import annotations

from typing import List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_id: str = Field(min_length=1, max_length=128)
    message_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=256)
    chat_id: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=8_000)
    locale: Optional[str] = Field(default=None, max_length=32)


class TelegramUser(BaseModel):
    """Resolved authorization data, never credentials or provider tokens."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    authenticated: bool
    license: Optional[str] = None
    permissions: Set[str] = Field(default_factory=set)
    quota_remaining: Optional[int] = Field(default=None, ge=0)
    current_job_id: Optional[str] = None
    current_idea_ids: List[str] = Field(default_factory=list)
    current_video_job_id: Optional[str] = None


class TelegramMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    data: Optional[dict] = None
    job_id: Optional[str] = None
    requires_confirmation: bool = False
    error: Optional[str] = None
