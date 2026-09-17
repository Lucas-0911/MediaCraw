# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

# Privacy: crawled records must not keep identifiable creator fields.
import hashlib


def anonymize_user_id(user_id) -> str:
    """Hash a platform user id for creator grouping without storing the raw id."""
    if user_id is None:
        return ""
    s = str(user_id).strip()
    if not s:
        return ""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def mask_nickname(name) -> str:
    """Mask a nickname: keep first/last character, replace the middle with stars.

    Length 1 -> "*"; length 2 -> first + "*"; otherwise first + "***" + last.
    """
    if name is None:
        return ""
    s = str(name)
    if len(s) <= 1:
        return "*"
    if len(s) == 2:
        return s[0] + "*"
    return s[0] + "***" + s[-1]
