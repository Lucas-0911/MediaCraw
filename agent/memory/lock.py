# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Conversation execution lock. Locks always expire; acquisition never waits forever."""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional, Protocol
from uuid import uuid4

from config import agent_config
from tools import utils

LOCK_KEY_PREFIX = "agent:lock:"
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class ConversationLock(Protocol):
    async def acquire(self, conversation_id: str) -> bool: ...

    async def release(self, conversation_id: str) -> None: ...


class InMemoryConversationLock:
    def __init__(
        self,
        ttl_seconds: float = agent_config.AGENT_MEMORY_LOCK_TTL,
        timeout_seconds: float = agent_config.AGENT_MEMORY_LOCK_TIMEOUT,
    ) -> None:
        if ttl_seconds <= 0 or timeout_seconds < 0:
            raise ValueError("lock ttl must be positive and timeout must be >= 0")
        self._ttl_seconds = ttl_seconds
        self._timeout_seconds = timeout_seconds
        self._guard = asyncio.Lock()
        self._locks: Dict[str, tuple[str, float]] = {}
        self._held: Dict[str, str] = {}

    async def acquire(self, conversation_id: str) -> bool:
        token = uuid4().hex
        deadline = time.monotonic() + self._timeout_seconds
        while True:
            async with self._guard:
                self._purge(conversation_id)
                if conversation_id not in self._locks:
                    self._locks[conversation_id] = (token, time.monotonic() + self._ttl_seconds)
                    self._held[conversation_id] = token
                    return True
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(0.02)

    async def release(self, conversation_id: str) -> None:
        token = self._held.pop(conversation_id, None)
        async with self._guard:
            current = self._locks.get(conversation_id)
            if token and current and current[0] == token:
                self._locks.pop(conversation_id, None)

    def _purge(self, conversation_id: str) -> None:
        current = self._locks.get(conversation_id)
        if current and current[1] < time.monotonic():
            self._locks.pop(conversation_id, None)


class RedisConversationLock:
    """SET NX EX lock using the existing Redis connection settings."""

    def __init__(
        self,
        redis_client: object,
        ttl_seconds: float = agent_config.AGENT_MEMORY_LOCK_TTL,
        timeout_seconds: float = agent_config.AGENT_MEMORY_LOCK_TIMEOUT,
    ) -> None:
        if ttl_seconds <= 0 or timeout_seconds < 0:
            raise ValueError("lock ttl must be positive and timeout must be >= 0")
        self._redis = redis_client
        self._ttl_seconds = int(ttl_seconds)
        self._timeout_seconds = timeout_seconds
        self._held: Dict[str, str] = {}

    async def acquire(self, conversation_id: str) -> bool:
        token = uuid4().hex
        key = self._key(conversation_id)
        deadline = time.monotonic() + self._timeout_seconds
        try:
            while True:
                acquired = await asyncio.to_thread(
                    self._redis.set, key, token, nx=True, ex=self._ttl_seconds
                )
                if acquired:
                    self._held[conversation_id] = token
                    return True
                if time.monotonic() >= deadline:
                    return False
                await asyncio.sleep(0.05)
        except Exception:
            utils.logger.warning("agent conversation lock backend unavailable")
            raise

    async def release(self, conversation_id: str) -> None:
        token = self._held.pop(conversation_id, None)
        if not token:
            return
        try:
            await asyncio.to_thread(self._redis.eval, _RELEASE_SCRIPT, 1, self._key(conversation_id), token)
        except Exception:
            utils.logger.warning("agent conversation lock release failed for %s", conversation_id)

    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"{LOCK_KEY_PREFIX}{conversation_id}"


def create_conversation_lock(
    cache_type: Optional[str] = None,
    ttl_seconds: float = agent_config.AGENT_MEMORY_LOCK_TTL,
    timeout_seconds: float = agent_config.AGENT_MEMORY_LOCK_TIMEOUT,
) -> ConversationLock:
    cache_type = cache_type or agent_config.AGENT_MEMORY_CACHE_TYPE
    if cache_type == "redis":
        from cache.redis_cache import RedisCache

        return RedisConversationLock(RedisCache()._redis_client, ttl_seconds, timeout_seconds)
    return InMemoryConversationLock(ttl_seconds, timeout_seconds)
