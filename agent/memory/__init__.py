# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Conversation memory port used by AgentLoop."""

from .contracts import (
    AgentConversationRecord,
    AgentMemory,
    AgentMessageRecord,
    AgentMessageRole,
    AgentShortTermState,
    AgentToolCallRecord,
    AgentToolCallStatus,
)
from .errors import AgentMemoryError, AgentMemoryLockTimeout, AgentMemoryUnavailable
from .factory import create_agent_memory
from .sanitizer import REDACTED, sanitize, sanitize_json, sanitize_text
from .service import AgentMemoryService

__all__ = [
    "AgentConversationRecord",
    "AgentMemory",
    "AgentMemoryError",
    "AgentMemoryLockTimeout",
    "AgentMemoryService",
    "AgentMemoryUnavailable",
    "AgentMessageRecord",
    "AgentMessageRole",
    "AgentShortTermState",
    "AgentToolCallRecord",
    "AgentToolCallStatus",
    "REDACTED",
    "create_agent_memory",
    "sanitize",
    "sanitize_json",
    "sanitize_text",
]
