# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Compose AgentMemoryService from existing DB and cache infrastructure."""
from __future__ import annotations

from typing import Optional

from cache.cache_factory import CacheFactory
from config import agent_config
from database.agent_session import create_agent_engine

from .lock import create_conversation_lock
from .service import AgentMemoryService
from .state import AgentShortTermStateStore, DictTtlCache
from .store import SqlAgentMemoryStore


async def create_agent_memory(
    *,
    db_type: Optional[str] = None,
    sqlite_path: Optional[str] = None,
    in_memory: bool = False,
    cache_type: Optional[str] = None,
    max_messages: Optional[int] = None,
    context_ttl: Optional[int] = None,
    lock_ttl: Optional[float] = None,
    lock_timeout: Optional[float] = None,
) -> AgentMemoryService:
    engine = create_agent_engine(db_type, sqlite_path=sqlite_path, in_memory=in_memory)
    store = SqlAgentMemoryStore(engine)
    await store.create_schema()

    resolved_cache_type = cache_type or agent_config.AGENT_MEMORY_CACHE_TYPE
    cache = DictTtlCache() if resolved_cache_type == "memory" else CacheFactory.create_cache(resolved_cache_type)
    state = AgentShortTermStateStore(cache, context_ttl or agent_config.AGENT_CONTEXT_TTL)
    lock = create_conversation_lock(
        resolved_cache_type,
        ttl_seconds=lock_ttl or agent_config.AGENT_MEMORY_LOCK_TTL,
        timeout_seconds=lock_timeout if lock_timeout is not None else agent_config.AGENT_MEMORY_LOCK_TIMEOUT,
    )
    return AgentMemoryService(
        store,
        state,
        lock,
        max_messages=max_messages or agent_config.AGENT_MEMORY_MAX_MESSAGES,
    )
