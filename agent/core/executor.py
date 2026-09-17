# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Validation, timeout and duplicate-call protection for registered tools."""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Set

from pydantic import ValidationError

from .contracts import AgentContext, ToolCall, ToolResult, ToolResultStatus
from .policy import inspect_tool_call
from .registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, per_tool_timeout_seconds: float) -> None:
        self._registry = registry
        self._per_tool_timeout_seconds = per_tool_timeout_seconds
        self._seen_lock = asyncio.Lock()

    @staticmethod
    def _fingerprint(call: ToolCall) -> str:
        serialized = json.dumps(
            {"name": call.name, "arguments": call.arguments},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def execute(
        self, call: ToolCall, context: AgentContext, seen_calls: Set[str]
    ) -> ToolResult:
        fingerprint = self._fingerprint(call)
        async with self._seen_lock:
            if fingerprint in seen_calls:
                return ToolResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    status=ToolResultStatus.INVALID,
                    error_code="duplicate_tool_call",
                    message="This tool call was already executed for the request.",
                )
            seen_calls.add(fingerprint)

        denial = inspect_tool_call(call.name, call.arguments)
        if denial:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.DENIED,
                error_code=denial.error_code,
                message=denial.message,
            )

        tool = self._registry.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.DENIED,
                error_code="tool_not_registered",
                message="The requested tool is not registered.",
            )
        denial = self._authorization_denial(tool, context)
        if denial:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.DENIED,
                error_code=denial,
                message="The current user is not allowed to execute this tool.",
            )

        try:
            arguments = tool.input_model.model_validate(call.arguments)
        except ValidationError as exc:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.INVALID,
                error_code="invalid_tool_arguments",
                message=exc.errors(include_url=False)[0]["msg"],
            )

        try:
            result = await asyncio.wait_for(
                tool.execute(arguments, context),
                timeout=self._per_tool_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.TIMEOUT,
                error_code="tool_timeout",
                message="Tool execution timed out.",
            )
        except Exception:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.ERROR,
                error_code="tool_execution_failed",
                message="Tool execution failed.",
            )

        if result.tool_call_id not in ("", call.id) or result.tool_name != call.name:
            return ToolResult(
                tool_call_id=call.id,
                tool_name=call.name,
                status=ToolResultStatus.ERROR,
                error_code="invalid_tool_result",
                message="Tool returned an invalid result identity.",
            )
        # The tool deliberately has no LLM transport details. Bind the provider
        # call ID here, after successful execution and before it re-enters LLM
        # context.
        return result.model_copy(update={"tool_call_id": call.id})

    @staticmethod
    def _authorization_denial(tool: object, context: AgentContext) -> str | None:
        if not context.authenticated:
            return "unauthenticated"
        if context.license != "active":
            return "license_inactive"
        permission = getattr(tool, "required_permission", None)
        if permission and permission not in context.permissions:
            return "permission_denied"
        if getattr(tool, "requires_quota", False) and context.quota_remaining is not None:
            if context.quota_remaining <= 0:
                return "quota_exhausted"
        return None
