# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Transport-neutral Agent Loop primitives."""

from .contracts import AgentContext, AgentHistoryMessage, AgentResponse, ToolCall, ToolResult
from .executor import ToolExecutor
from .loop import AgentLoop
from .policy import inspect_tool_call
from .registry import ToolRegistry

__all__ = [
    "AgentContext",
    "AgentHistoryMessage",
    "AgentLoop",
    "AgentResponse",
    "inspect_tool_call",
    "ToolCall",
    "ToolExecutor",
    "ToolRegistry",
    "ToolResult",
]
