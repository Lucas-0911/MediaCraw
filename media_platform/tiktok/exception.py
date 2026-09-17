# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from httpx import RequestError


class DataFetchError(RequestError):
    """Failed to fetch TikTok data"""


class IPBlockError(RequestError):
    """IP blocked or rate limited"""
