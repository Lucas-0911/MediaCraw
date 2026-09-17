# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Thin, transport-independent Telegram adapter."""

from .adapter import LegacyCommandHandler, TelegramAgentHandler
from .contracts import TelegramMessageResponse, TelegramUpdate, TelegramUser

__all__ = [
    "LegacyCommandHandler",
    "TelegramAgentHandler",
    "TelegramMessageResponse",
    "TelegramUpdate",
    "TelegramUser",
]
