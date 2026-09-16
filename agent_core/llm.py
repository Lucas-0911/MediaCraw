# -*- coding: utf-8 -*-
"""LLM port and OpenAI-compatible adapter for the Agent Loop."""
from __future__ import annotations

import json
from typing import Protocol, Sequence

import httpx

from config import agent_config

from .contracts import AgentContext, LLMResponse, ToolCall, ToolResult


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
            {
                "role": "system",
                "content": (
                    "You are a read-only crawl-results assistant. Use tools only "
                    "when needed. Never invent facts; if a tool returns empty, say "
                    "no stored data was found. Do not request crawling automatically. "
                    "Call crawl_platform only for an explicit user request to crawl."
                ),
            },
            {"role": "user", "content": context.message},
        ]
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
                    "content": result.model_dump_json(),
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
