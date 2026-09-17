# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Allowlisted tool registry; the Agent cannot execute arbitrary callables."""
from __future__ import annotations

from typing import Dict, Iterable, Protocol, Type

from pydantic import BaseModel

from .contracts import AgentContext, ToolResult
from .policy import inspect_tool_name


class RegisteredTool(Protocol):
    name: str
    input_model: Type[BaseModel]

    async def execute(self, arguments: BaseModel, context: AgentContext) -> ToolResult:
        """Execute a validated request through an application service."""


class ToolRegistry:
    def __init__(self, tools: Iterable[RegisteredTool] = ()) -> None:
        self._tools: Dict[str, RegisteredTool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: RegisteredTool) -> None:
        denial = inspect_tool_name(tool.name)
        if denial:
            raise ValueError(f"Refusing to register a database/shell tool: {tool.name}")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def definitions(self) -> list[dict[str, object]]:
        """Provider-neutral tool schemas for an LLM client."""
        return [
            {
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "parameters": tool.input_model.model_json_schema(),
            }
            for tool in self._tools.values()
        ]
