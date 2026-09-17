# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""LLM port and OpenAI-compatible adapter for the Agent Loop."""
from __future__ import annotations

import json
from typing import Any, Protocol, Sequence

import httpx

from config import agent_config

from .contracts import AgentContext, LLMResponse, ToolCall, ToolResult
from .prompts import AGENT_SYSTEM_PROMPT


class AgentLLM(Protocol):
    async def respond(
        self,
        context: AgentContext,
        tool_definitions: Sequence[dict[str, object]],
        tool_results: Sequence[ToolResult],
    ) -> LLMResponse:
        """Return a final answer or one or more registered-tool calls."""


class OpenAICompatibleAgentLLM:
    """Adapter only; API credentials remain in configuration, never context."""

    def __init__(
        self,
        base_url: str = agent_config.AGENT_LLM_BASE_URL,
        model: str = agent_config.AGENT_LLM_MODEL,
        api_key: str = agent_config.AGENT_LLM_API_KEY,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    async def respond(
        self,
        context: AgentContext,
        tool_definitions: Sequence[dict[str, object]],
        tool_results: Sequence[ToolResult],
    ) -> LLMResponse:
        if not agent_config.AGENT_LLM_ENABLED or not self._api_key:
            return LLMResponse(final_answer="Agent LLM is not configured.")

        messages: list[dict[str, object]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        ]
        for turn in context.history:
            if turn.role in ("user", "assistant"):
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": context.message})
        if tool_results:
            # OpenAI-compatible chat APIs require tool output to follow an
            # assistant tool-call message. The loop keeps only safe ToolResult
            # objects, so reconstruct the minimum protocol envelope here.
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": result.tool_call_id,
                            "type": "function",
                            "function": {"name": result.tool_name, "arguments": "{}"},
                        }
                        for result in tool_results
                    ],
                }
            )
        for result in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": json.dumps(self._compact_tool_result(result), ensure_ascii=False, default=str),
                }
            )

        payload: dict[str, object] = {
            "model": self._model,
            "temperature": 0,
            "messages": messages,
            "tools": [{"type": "function", "function": item} for item in tool_definitions],
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]

        calls = [
            ToolCall(
                id=str(call["id"]),
                name=str(call["function"]["name"]),
                arguments=json.loads(call["function"].get("arguments") or "{}"),
            )
            for call in message.get("tool_calls") or []
        ]
        return LLMResponse(final_answer=message.get("content"), tool_calls=calls)

    @staticmethod
    def _compact_tool_result(result: ToolResult) -> dict[str, Any]:
        payload = result.model_dump(mode="json")
        data = payload.get("data")
        if not isinstance(data, dict):
            return payload
        records = data.get("records")
        if isinstance(records, list):
            compacted = []
            for record in records[:8]:
                if not isinstance(record, dict):
                    compacted.append(record)
                    continue
                compacted.append(
                    {
                        "platform": record.get("platform"),
                        "record_id": record.get("record_id"),
                        "title": record.get("title"),
                        "content": str(record.get("content") or "")[:240],
                        "url": record.get("url"),
                    }
                )
            data["records"] = compacted
            if len(records) > 8:
                data["truncated"] = True
        payload["data"] = data
        return payload
