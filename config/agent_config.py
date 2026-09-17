# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Configuration for the read-only Agent Loop.

Secrets stay in the process environment and are deliberately not copied into
AgentContext or tool inputs.
"""
import os


MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "4"))
AGENT_REQUEST_TIMEOUT_SECONDS = float(os.getenv("AGENT_REQUEST_TIMEOUT_SECONDS", "45"))
AGENT_TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "10"))

AGENT_LLM_ENABLED = os.getenv("AGENT_LLM_ENABLED", "false").lower() in ("1", "true", "yes")
AGENT_LLM_BASE_URL = os.getenv("AGENT_LLM_BASE_URL", "https://api.openai.com/v1")
AGENT_LLM_MODEL = os.getenv("AGENT_LLM_MODEL", "gpt-4o-mini")
AGENT_LLM_API_KEY = os.getenv("AGENT_LLM_API_KEY", "")

# agent.memory.max-messages — recent turns loaded for the LLM, chronological.
AGENT_MEMORY_MAX_MESSAGES = int(os.getenv("AGENT_MEMORY_MAX_MESSAGES", "20"))
# agent.memory.context-ttl — Redis/memory short-term state TTL in seconds.
AGENT_CONTEXT_TTL = int(os.getenv("AGENT_CONTEXT_TTL", "3600"))
# agent.memory.lock-ttl — lock auto-expires; must not be infinite.
AGENT_MEMORY_LOCK_TTL = int(os.getenv("AGENT_MEMORY_LOCK_TTL", "60"))
# agent.memory.lock-timeout — seconds to wait before giving up on the lock.
AGENT_MEMORY_LOCK_TIMEOUT = float(os.getenv("AGENT_MEMORY_LOCK_TIMEOUT", "3"))
# Short-term state + lock backend: "memory" (local) or "redis".
AGENT_MEMORY_CACHE_TYPE = os.getenv("AGENT_MEMORY_CACHE_TYPE", "memory")
# Agent conversation store is independent of crawler SAVE_DATA_OPTION.
AGENT_MEMORY_DB_TYPE = os.getenv("AGENT_MEMORY_DB_TYPE", "sqlite")
AGENT_MEMORY_SQLITE_PATH = os.getenv(
    "AGENT_MEMORY_SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "agent_memory.db"),
)
