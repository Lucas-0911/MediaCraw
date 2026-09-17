# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Memory-layer errors. AgentLoop maps these to structured AgentResponse values."""


class AgentMemoryError(Exception):
    """Base error for conversation memory failures."""


class AgentMemoryUnavailable(AgentMemoryError):
    """PostgreSQL/SQLite (or the memory store) could not complete a required operation."""


class AgentMemoryLockTimeout(AgentMemoryError):
    """The conversation lock could not be acquired before the configured timeout."""
