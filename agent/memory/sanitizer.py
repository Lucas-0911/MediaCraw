# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Redact secrets before they are written to conversation memory."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

REDACTED = "[REDACTED]"

_SAFE_KEYS = {"cookie_available"}

_SENSITIVE_EXACT = {
    "cookie",
    "cookies",
    "set_cookie",
    "cookie_str",
    "authorization",
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bot_token",
    "telegram_bot_token",
    "jwt",
    "private_key",
    "db_password",
    "database_password",
    "client_secret",
    "x_amz_credential",
    "x_amz_signature",
    "x_amz_security_token",
    "aws_secret_access_key",
    "aws_access_key_id",
    "bearer",
    "bearer_token",
}

_SENSITIVE_PARTS = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bot_token",
    "private_key",
    "authorization",
    "bearer",
    "credential",
)

_VALUE_PATTERNS = (
    (re.compile(r"(?i)(\bBearer\s+)\S+"), rf"\1{REDACTED}"),
    (re.compile(r"(?i)(\b(?:api[_-]?key|password|secret|bot[_-]?token)\s*[:=]\s*)\S+"), rf"\1{REDACTED}"),
    (re.compile(r"(?i)(\bcookies?\s*[:=]\s*)\S+"), rf"\1{REDACTED}"),
    (
        re.compile(
            r"(?i)([?&](?:X-Amz-Credential|X-Amz-Signature|X-Amz-Security-Token|AWSAccessKeyId|Signature)=)[^&\s]+"
        ),
        rf"\1{REDACTED}",
    ),
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), REDACTED),
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in _SAFE_KEYS:
        return False
    if normalized in _SENSITIVE_EXACT:
        return True
    if "cookie" in normalized and normalized != "cookie_available":
        return True
    if normalized == "token" or normalized.endswith("_token"):
        return True
    return any(part in normalized for part in _SENSITIVE_PARTS)


def sanitize(value: Any) -> Any:
    """Return a copy of value with secrets replaced by [REDACTED]."""
    if isinstance(value, Mapping):
        return {str(key): REDACTED if is_sensitive_key(str(key)) else sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize(item) for item in value]
    if isinstance(value, bytes):
        return REDACTED
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def sanitize_text(value: str) -> str:
    return _sanitize_string(value)


def sanitize_json(value: Any) -> str:
    return json.dumps(sanitize(value), ensure_ascii=False, default=str)


def _sanitize_string(text: str) -> str:
    stripped = text.strip()
    if stripped[:1] in "{[":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, (dict, list)):
            return json.dumps(sanitize(parsed), ensure_ascii=False, default=str)
    redacted = text
    for pattern, replacement in _VALUE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
