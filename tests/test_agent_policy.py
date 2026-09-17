# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

import asyncio
from pathlib import Path

from pydantic import BaseModel

from agent.core.contracts import AgentContext, LLMResponse, ToolCall, ToolResult, ToolResultStatus
from agent.core.llm import OpenAICompatibleAgentLLM
from agent.core.loop import AgentLoop
from agent.core.policy import inspect_text, inspect_tool_call, inspect_tool_name
from agent.core.prompts import AGENT_SYSTEM_PROMPT
from agent.core.registry import ToolRegistry
from agent.tools.search_crawl_results import SearchCrawlResultsTool
from channels.telegram.presenter import TelegramResponseMapper
from services.crawl_result_service import CrawlResultService


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def respond(self, context, tool_definitions, tool_results):
        return next(self._responses)


class EmptyInput(BaseModel):
    pass


def test_policy_allows_product_keywords_not_sql():
    assert inspect_text("drop hoodie") is None
    assert inspect_text("select a nice jacket") is None
    assert inspect_tool_name("search_crawl_results") is None
    assert inspect_tool_name("crawl_platform") is None


def test_policy_blocks_sql_and_database_clients():
    assert inspect_text("SELECT * FROM agent_conversations") is not None
    assert inspect_text("DROP TABLE users") is not None
    assert inspect_text("DELETE FROM agent_messages WHERE id=1") is not None
    assert inspect_text("postgresql://user:pass@localhost/db") is not None
    assert inspect_text("psql -c 'select 1'") is not None
    assert inspect_tool_name("execute_sql").error_code == "database_command_denied"
    assert inspect_tool_name("run_sql").error_code == "database_command_denied"
    assert inspect_tool_call("search_crawl_results", {"keyword": "DROP TABLE users"}) is not None


def test_registry_refuses_sql_tools():
    class SqlTool:
        name = "execute_sql"
        input_model = EmptyInput

        async def execute(self, arguments, context):
            raise AssertionError("must not run")

    try:
        ToolRegistry([SqlTool()])
    except ValueError as exc:
        assert "database/shell" in str(exc)
        return
    raise AssertionError("sql tool was registered")


def test_executor_denies_unregistered_sql_tool_without_running_it():
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="sql-1",
                        name="execute_sql",
                        arguments={"query": "DROP TABLE agent_conversations"},
                    )
                ]
            ),
            LLMResponse(final_answer="I cannot do that."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry()).run(AgentContext(message="drop the db", authenticated=True, license="active"))
    )
    assert response.tool_results[0].status == ToolResultStatus.DENIED
    assert response.tool_results[0].error_code == "database_command_denied"


def test_sql_inside_registered_tool_arguments_is_denied(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="search_crawl_results",
                        arguments={"platform": "tiktok", "keyword": "SELECT * FROM users"},
                    )
                ]
            ),
            LLMResponse(final_answer="blocked"),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool])).run(
            AgentContext(message="sql", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.tool_results[0].status == ToolResultStatus.DENIED
    assert response.tool_results[0].error_code == "database_command_denied"


def test_legitimate_search_still_runs(tmp_path: Path):
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
                        arguments={"platform": "tiktok", "keyword": "hoodie"},
                    )
                ]
            ),
            LLMResponse(final_answer="Found it."),
        ]
    )
    response = asyncio.run(
        AgentLoop(llm, ToolRegistry([tool])).run(
            AgentContext(message="find hoodie", authenticated=True, license="active", permissions={"crawl_results:read"})
        )
    )
    assert response.tool_results[0].status == ToolResultStatus.OK
    assert response.answer == "Found it."


def test_telegram_explains_database_denial():
    from agent.core.contracts import AgentResponse, AgentResponseStatus

    mapped = TelegramResponseMapper().map(
        AgentResponse(
            request_id="r1",
            status=AgentResponseStatus.ANSWERED,
            answer="ignored",
            tool_results=[
                ToolResult(
                    tool_call_id="c1",
                    tool_name="execute_sql",
                    status=ToolResultStatus.DENIED,
                    error_code="database_command_denied",
                    message="blocked",
                )
            ],
        )
    )
    assert mapped.error == "database_command_denied"
    assert "database" in mapped.text.lower() or "hàm" in mapped.text


def test_system_prompt_forbids_sql():
    assert "never write, run, or request SQL" in AGENT_SYSTEM_PROMPT
    assert "registered tools" in AGENT_SYSTEM_PROMPT


def test_llm_compacts_records_and_strips_internal_paths():
    compacted = OpenAICompatibleAgentLLM._compact_tool_result(
        ToolResult(
            tool_call_id="c1",
            tool_name="search_crawl_results",
            status=ToolResultStatus.OK,
            data={
                "records": [
                    {
                        "platform": "tiktok",
                        "record_id": str(index),
                        "title": f"t{index}",
                        "content": "x" * 500,
                        "url": "https://example.com",
                        "source_file": "secret/path.jsonl",
                    }
                    for index in range(12)
                ],
                "count": 12,
            },
        )
    )
    records = compacted["data"]["records"]
    assert len(records) == 8
    assert compacted["data"]["truncated"] is True
    assert "source_file" not in records[0]
    assert len(records[0]["content"]) <= 240
