# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Short-term Agent state. PostgreSQL remains the source of truth for history."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from cache.abs_cache import AbstractCache
from config import agent_config
from tools import utils

from .contracts import AgentShortTermState
from .sanitizer import sanitize

CONVERSATION_STATE_KEY_PREFIX = "agent:conversation:"


class DictTtlCache(AbstractCache):
    """Process-local TTL cache used when Redis is not configured."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        value, expires_at = self._store.get(key, (None, 0.0))
        if value is None:
            return None
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, expire_time: int) -> None:
        self._store[key] = (value, time.time() + expire_time)

    def keys(self, pattern: str) -> List[str]:
        self._purge()
        if pattern == "*":
            return list(self._store.keys())
        needle = pattern.replace("*", "")
        return [key for key in self._store if needle in key]

    def _purge(self) -> None:
        now = time.time()
        expired = [key for key, (_value, expires_at) in self._store.items() if expires_at < now]
        for key in expired:
            self._store.pop(key, None)


class AgentShortTermStateStore:
    def __init__(self, cache: AbstractCache, ttl_seconds: int = agent_config.AGENT_CONTEXT_TTL) -> None:
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def get(self, conversation_id: str) -> Optional[AgentShortTermState]:
        try:
            payload = self._cache.get(self._key(conversation_id))
        except Exception:
            utils.logger.warning("agent short-term state read failed for %s", conversation_id)
            return None
        if not payload:
            return None
        try:
            if isinstance(payload, AgentShortTermState):
                return payload
            if isinstance(payload, dict):
                return AgentShortTermState.model_validate(sanitize(payload))
        except Exception:
            utils.logger.warning("agent short-term state was invalid for %s", conversation_id)
        return None

    async def set(self, conversation_id: str, state: AgentShortTermState) -> None:
        try:
            payload = sanitize(state.model_dump())
            self._cache.set(self._key(conversation_id), payload, self._ttl_seconds)
        except Exception:
            utils.logger.warning("agent short-term state write failed for %s", conversation_id)

    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"{CONVERSATION_STATE_KEY_PREFIX}{conversation_id}"
