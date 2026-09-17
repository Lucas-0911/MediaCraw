# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from .crawler import router as crawler_router
from .data import router as data_router
from .websocket import router as websocket_router
from .trend import router as trend_router

__all__ = ["crawler_router", "data_router", "websocket_router", "trend_router"]
