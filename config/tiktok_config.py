# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""TikTok Vietnam / international (tiktok.com) configuration."""

# Guest / public crawl without login. Keep True so you can test without a TikTok account.
TIKTOK_ALLOW_GUEST = True

# Official web domain for Vietnam is still www.tiktok.com (there is no tiktok.vn).
TIKTOK_INDEX_URL = "https://www.tiktok.com"
# Official locale query is lang=vi (not vi-VN).
TIKTOK_LANG = "vi"

# Detail mode: full URL, short link, or numeric video id
# 1. https://www.tiktok.com/@username/video/7123456789012345678
# 2. https://vt.tiktok.com/ZSxxxxxx/
# 3. 7123456789012345678
TIKTOK_SPECIFIED_ID_LIST = [
    "https://www.tiktok.com/@tiktok/video/7123456789012345678",
]

# Creator mode: homepage URL or @uniqueId
TIKTOK_CREATOR_ID_LIST = [
    "https://www.tiktok.com/@tiktok",
    "tiktok",
]
