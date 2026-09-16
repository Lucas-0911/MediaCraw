import asyncio
from pathlib import Path

from pydantic import BaseModel

from agent_core.contracts import LLMResponse, ToolCall, ToolResult, ToolResultStatus
from agent_core.loop import AgentLoop
from agent_core.registry import ToolRegistry
from agent_tools.crawl_platform import CrawlPlatformTool
from agent_tools.search_crawl_results import SearchCrawlResultsTool
from api.services.crawl_result_service import CrawlResultService
from api.services.crawler_job_service import CrawlJob
from channels.telegram.adapter import TelegramAgentHandler
from channels.telegram.contracts import TelegramMessageResponse, TelegramUpdate, TelegramUser


class ScriptedLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.contexts = []

    async def respond(self, context, tool_definitions, tool_results):
        self.contexts.append(context)
        return next(self.responses)


class SlowLLM:
    async def respond(self, context, tool_definitions, tool_results):
        await asyncio.sleep(0.05)
        return LLMResponse(final_answer="late")


class FakeResolver:
    def __init__(self, *, authenticated=True, permissions=None):
        self.user = TelegramUser(
            user_id="user-1",
            authenticated=authenticated,
            license="active" if authenticated else None,
            permissions=permissions or {"crawl_results:read", "crawler:run"},
            quota_remaining=2,
            current_job_id="job-old",
            current_idea_ids=["idea-1"],
            current_video_job_id="video-old",
        )

    async def resolve(self, update):
        return self.user


class LegacyHandler:
    def __init__(self):
        self.updates = []

    async def handle(self, update):
        self.updates.append(update)
        return TelegramMessageResponse(text=f"legacy:{update.text}")


class FakeCrawlerJobs:
    def __init__(self):
        self.calls = []

    async def start_keyword_crawl(self, platform, keyword, limit):
        self.calls.append((platform, keyword, limit))
        return CrawlJob(job_id="abc123", status="accepted")


class ExplodingTool:
    name = "explode"
    input_model = BaseModel

    async def execute(self, arguments, context):
        raise RuntimeError("database password should never be exposed")


def update(text):
    return TelegramUpdate(
        update_id="update-1", message_id="message-1", user_id="user-1", chat_id="chat-1", text=text
    )


def handler(llm, tools, resolver=None, request_timeout=45):
    return TelegramAgentHandler(
        LegacyHandler(),
        resolver or FakeResolver(),
        AgentLoop(llm, ToolRegistry(tools), request_timeout_seconds=request_timeout),
    )


def test_status_slash_command_delegates_to_legacy_handler():
    legacy = LegacyHandler()
    adapter = TelegramAgentHandler(
        legacy, FakeResolver(), AgentLoop(ScriptedLLM([LLMResponse(final_answer="unused")]), ToolRegistry())
    )
    response = asyncio.run(adapter.handle(update("/status")))
    assert response.text == "legacy:/status"
    assert legacy.updates[0].text == "/status"


def test_natural_language_routes_to_agent_not_legacy():
    llm = ScriptedLLM([LLMResponse(final_answer="Xin chào")])
    legacy = LegacyHandler()
    adapter = TelegramAgentHandler(legacy, FakeResolver(), AgentLoop(llm, ToolRegistry()))
    response = asyncio.run(adapter.handle(update("Tìm video hoodie")))
    assert response.text == "Xin chào"
    assert len(llm.contexts) == 1
    assert legacy.updates == []


def test_existing_data_search_is_presented_without_raw_entity(tmp_path: Path):
    data_file = tmp_path / "tiktok" / "jsonl" / "result.jsonl"
    data_file.parent.mkdir(parents=True)
    data_file.write_text(
        '{"aweme_id":"1","title":"Hoodie oversized","desc":"hoodie warm","aweme_url":"https://tiktok/1"}\n',
        encoding="utf-8",
    )
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="search-1", name=tool.name, arguments={"platform": "tiktok", "keyword": "hoodie", "limit": 20})]),
            LLMResponse(final_answer="ignored presentation"),
        ]
    )
    response = asyncio.run(handler(llm, [tool]).handle(update("Tìm 20 video hoodie trên TikTok")))
    assert "Tìm thấy 1 video phù hợp" in response.text
    assert "Hoodie oversized" in response.text
    assert "source_file" not in response.text


def test_empty_search_returns_safe_no_data_message(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="search-1", name=tool.name, arguments={"platform": "tiktok", "keyword": "hoodie"})]),
            LLMResponse(final_answer="invented result"),
        ]
    )
    response = asyncio.run(handler(llm, [tool]).handle(update("Tìm video hoodie")))
    assert response.text == "Không tìm thấy dữ liệu phù hợp trong dữ liệu hiện có."


def test_explicit_crawl_is_asynchronous_job():
    tool = CrawlPlatformTool(FakeCrawlerJobs())
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="crawl-1", name=tool.name, arguments={"platform": "tiktok", "keyword": "hoodie", "limit": 20})]),
            LLMResponse(final_answer="ignored presentation"),
        ]
    )
    response = asyncio.run(handler(llm, [tool]).handle(update("Crawl 20 video hoodie trên TikTok")))
    assert response.job_id == "abc123"
    assert "Đã tạo job crawl #abc123" in response.text


def test_search_request_does_not_run_crawl_tool(tmp_path: Path):
    search = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    jobs = FakeCrawlerJobs()
    crawl = CrawlPlatformTool(jobs)
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="search-1", name=search.name, arguments={"platform": "tiktok", "keyword": "hoodie"})]),
            LLMResponse(final_answer="ignored"),
        ]
    )
    response = asyncio.run(handler(llm, [search, crawl]).handle(update("Tìm video hoodie")))
    assert response.job_id is None
    assert jobs.calls == []


def test_unauthorized_user_is_denied_safely(tmp_path: Path):
    tool = SearchCrawlResultsTool(CrawlResultService(tmp_path))
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="search-1", name=tool.name, arguments={"platform": "tiktok", "keyword": "hoodie"})]),
            LLMResponse(final_answer="ignored"),
        ]
    )
    response = asyncio.run(handler(llm, [tool], FakeResolver(authenticated=False)).handle(update("Tìm video hoodie")))
    assert response.text == "Bạn không có quyền thực hiện yêu cầu này."
    assert response.error == "permission_denied"


def test_tool_exception_is_hidden_from_telegram_user():
    llm = ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="bad-1", name="explode")]),
            LLMResponse(final_answer="ignored"),
        ]
    )
    response = asyncio.run(handler(llm, [ExplodingTool()]).handle(update("do it")))
    assert response.text == "Xin lỗi, hiện tại hệ thống không thể xử lý yêu cầu này."
    assert "password" not in response.text


def test_agent_timeout_is_safe_for_telegram_user():
    response = asyncio.run(handler(SlowLLM(), [], request_timeout=0.001).handle(update("Tìm video hoodie")))
    assert response.text == "Xin lỗi, yêu cầu đã hết thời gian xử lý."


def test_context_contains_authorization_not_secrets():
    llm = ScriptedLLM([LLMResponse(final_answer="ok")])
    asyncio.run(handler(llm, []).handle(update("Xin chào")))
    context = llm.contexts[0]
    assert context.user_id == "user-1"
    assert context.telegram_chat_id == "chat-1"
    assert context.license == "active"
    assert context.current_job_id == "job-old"
    assert context.current_idea_ids == ["idea-1"]
    assert "api_key" not in context.model_dump()
    assert "token" not in context.model_dump()
