# -*- coding: utf-8 -*-
from httpx import RequestError


class DataFetchError(RequestError):
    """Failed to fetch TikTok data"""


class IPBlockError(RequestError):
    """IP blocked or rate limited"""
