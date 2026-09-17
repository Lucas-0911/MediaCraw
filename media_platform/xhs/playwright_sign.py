# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

# Xiaohongshu signature generation using xhshow pure-algorithm library
#
# Credits: signing uses the xhshow library by Cloxl
# Repository: https://github.com/Cloxl/xhshow
# License: MIT
#
# Requires xhshow>=0.2.0 which fixes GET a3_hash calculation
# (https://github.com/Cloxl/xhshow/issues/104); no local monkey-patch is required.

from typing import Any, Dict, Optional, Union

from .xhs_sign import get_trace_id


def sign_with_xhshow(
    uri: str,
    data: Optional[Union[Dict, str]] = None,
    cookie_str: str = "",
    method: str = "POST",
) -> Dict[str, Any]:
    """
    使用 xhshow 纯算法生成完整签名请求头

    Args:
        uri: API path
        data: Request data (GET params dict or POST payload dict)
        cookie_str: Cookie string
        method: Request method (GET or POST)

    Returns:
        Dictionary containing x-s, x-t, x-s-common, x-b3-traceid
    """
    from xhshow import Xhshow
    xhshow_client = Xhshow()

    if method.upper() == "POST":
        headers = xhshow_client.sign_headers_post(
            uri=uri,
            cookies=cookie_str,
            payload=data if isinstance(data, dict) else {},
        )
    else:
        headers = xhshow_client.sign_headers_get(
            uri=uri,
            cookies=cookie_str,
            params=data if isinstance(data, dict) else {},
        )

    return {
        "x-s": headers.get("x-s", ""),
        "x-t": headers.get("x-t", ""),
        "x-s-common": headers.get("x-s-common", ""),
        "x-b3-traceid": headers.get("x-b3-traceid", get_trace_id()),
    }
