# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

import asyncio
from pathlib import Path

from pydantic import BaseModel

from agent.core.contracts import AgentContext, LLMResponse, ToolCall, ToolResultStatus
from agent.core.loop import AgentLoop
from agent.core.registry import ToolRegistry
from agent.tools.search_crawl_results import SearchCrawlResultsTool
from services.crawl_result_service import CrawlResultService


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def respond(self, context, tool_definitions, tool_results):
        return next(self._responses)


class EmptyInput(BaseModel):
    pass


class SlowTool:
    name = "slow_tool"
    input_model = EmptyInput

    async def execute(self, arguments, context):
        await asyncio.sleep(0.05)
        raise AssertionError("ToolExecutor should time out first")


class SlowLLM:
    async def respond(self, context, tool_definitions, tool_results):
        await asyncio.sleep(0.05)
        return LLMResponse(final_answer="too late")


def test_agent_loop_returns_only_persisted_search_results(tmp_path: Path):
    data_file = tmp_path / "tiktok" / "jsonl" / "search_contents.jsonl"
    data_file.parent.mkdir(parents=True)
    data_file.write_text(
        '{"aweme_id":"1","title":"Blue hoodie","desc":"warm hoodie","source_keyword":"hoodie"}\n',
        encoding="utf-8",
    )
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="search_crawl_results",
                        arguments={"platform": "tiktok", "keyword": "hoodie", "limit": 20},
                    )
                ]
            ),
            LLMResponse(final_answer="Found one stored result."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool])).run(
            AgentContext(message="find hoodie", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.answer == "Found one stored result."
    assert response.tool_results[0].status == ToolResultStatus.OK
    assert response.tool_results[0].data["count"] == 1
    assert response.tool_results[0].data["records"][0]["record_id"] == "1"


def test_empty_result_is_structured_not_invented(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="search_crawl_results",
                        arguments={"platform": "tiktok", "keyword": "hoodie"},
                    )
                ]
            ),
            LLMResponse(final_answer="No stored data was found."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool])).run(
            AgentContext(message="find hoodie", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.tool_results[0].status == ToolResultStatus.EMPTY
    assert response.tool_results[0].data["records"] == []


def test_duplicate_tool_call_is_not_executed_twice(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    call = ToolCall(
        id="call-1",
        name="search_crawl_results",
        arguments={"platform": "tiktok", "keyword": "hoodie"},
    )
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[call]),
            LLMResponse(tool_calls=[ToolCall(id="call-2", name=call.name, arguments=call.arguments)]),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool]), max_steps=2).run(
            AgentContext(message="find", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.tool_results[-1].error_code == "duplicate_tool_call"


def test_context_rejects_secret_metadata():
    try:
        AgentContext(message="find", metadata={"api_key": "must-not-be-here"})
    except ValueError:
        pass
    else:
        raise AssertionError("secret metadata was accepted")


def test_invalid_tool_arguments_are_not_executed(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="search_crawl_results",
                        arguments={"platform": "not-a-platform", "keyword": "hoodie"},
                    )
                ]
            ),
            LLMResponse(final_answer="Please provide a supported platform."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool])).run(
            AgentContext(message="find", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.tool_results[0].status == ToolResultStatus.INVALID
    assert response.tool_results[0].error_code == "invalid_tool_arguments"


def test_per_tool_timeout_is_structured():
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="call-1", name="slow_tool")]),
            LLMResponse(final_answer="The search timed out."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([SlowTool()]), per_tool_timeout_seconds=0.001).run(
            AgentContext(message="find", authenticated=True, license="active")
        )
    )
    assert response.tool_results[0].status == ToolResultStatus.TIMEOUT


def test_max_steps_stops_repeated_tool_requests(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="search_crawl_results",
                        arguments={"platform": "tiktok", "keyword": "hoodie"},
                    )
                ]
            )
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool]), max_steps=1).run(
            AgentContext(message="find", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.status.value == "max_steps"


def test_total_request_timeout_is_structured():
    response = asyncio.run(
        AgentLoop(SlowLLM(), ToolRegistry(), request_timeout_seconds=0.001).run(
            AgentContext(message="find")
        )
    )
    assert response.status.value == "timeout"
