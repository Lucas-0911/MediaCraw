# -*- coding: utf-8 -*-
"""Telegram user-resolution port; concrete auth stays outside handlers."""
from __future__ import annotations

from typing import Protocol

from .contracts import TelegramUpdate, TelegramUser


class TelegramUserResolver(Protocol):
    async def resolve(self, update: TelegramUpdate) -> TelegramUser:
        """Resolve identity, license, permissions and quota for one update."""
