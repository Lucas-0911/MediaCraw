# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

# @Time    : 2023/12/23 15:41
# @Desc    :
from enum import Enum


class SearchType(Enum):
    # Comprehensive
    DEFAULT = "1"

    # Real-time
    REAL_TIME = "61"

    # Popular
    POPULAR = "60"

    # Video
    VIDEO = "64"
