# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

import asyncio
import time
from pathlib import Path

from pydantic import ValidationError

from agent.core.contracts import AgentContext, LLMResponse, ToolCall, ToolResult, ToolResultStatus
from agent.core.loop import AgentLoop
from agent.memory.contracts import AgentShortTermState, AgentToolCallStatus
from agent.memory.errors import AgentMemoryUnavailable
from agent.memory.factory import create_agent_memory
from agent.memory.lock import InMemoryConversationLock, LOCK_KEY_PREFIX, RedisConversationLock
from agent.memory.sanitizer import REDACTED, sanitize, sanitize_text
from agent.memory.service import AgentMemoryService
from agent.memory.state import AgentShortTermStateStore, CONVERSATION_STATE_KEY_PREFIX, DictTtlCache
from agent.memory.store import SqlAgentMemoryStore
from agent.core.registry import ToolRegistry
from agent.tools.crawl_platform import CrawlPlatformTool
from agent.tools.search_crawl_results import SearchCrawlResultsTool
from services.crawl_result_service import CrawlResultService
from services.crawler_job_service import CrawlJob
from channels.telegram.adapter import TelegramAgentHandler
from channels.telegram.contracts import TelegramMessageResponse, TelegramUpdate, TelegramUser
from database.agent_session import create_agent_engine
from database.agent_models import AgentConversation, AgentMessage, AgentToolCall


class ScriptedLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.contexts = []

    async def respond(self, context, tool_definitions, tool_results):
        self.contexts.append(context)
        return next(self.responses)


class FakeCrawlerJobs:
    def __init__(self):
        self.calls = []

    async def start_keyword_crawl(self, platform, keyword, limit):
        self.calls.append((platform, keyword, limit))
        return CrawlJob(job_id="abc123", status="accepted")


class FakeResolver:
    def __init__(self, *, authenticated=True, cookie_available=False):
        self.user = TelegramUser(
            user_id="user-1",
            authenticated=authenticated,
            license="active" if authenticated else None,
            permissions={"crawl_results:read", "crawler:run"},
            quota_remaining=2,
            current_job_id="job-old",
            current_idea_ids=["idea-1"],
            current_video_job_id="video-old",
            cookie_available=cookie_available,
        )

    async def resolve(self, update):
        return self.user


class LegacyHandler:
    def __init__(self):
        self.updates = []

    async def handle(self, update):
        self.updates.append(update)
        return TelegramMessageResponse(text=f"legacy:{update.text}")


class DeadMemory:
    async def get_or_create_conversation(self, **kwargs):
        raise AgentMemoryUnavailable("postgres down")


def update(text, chat_id="chat-1", user_id="user-1"):
    return TelegramUpdate(
        update_id="update-1",
        message_id="message-1",
        user_id=user_id,
        chat_id=chat_id,
        text=text,
    )


def _memory(**kwargs):
    return create_agent_memory(in_memory=True, cache_type="memory", lock_timeout=0.05, **kwargs)


def test_context_contains_safe_fields_not_secrets():
    context = AgentContext(
        message="Tìm hoodie",
        user_id="user-1",
        telegram_chat_id="chat-1",
        conversation_id="conv-1",
        license="active",
        permissions={"crawl_results:read"},
        locale="vi",
        current_job_id="job-1",
        current_idea_ids=["idea-1"],
        current_video_job_id="video-1",
        cookie_available=True,
    )
    dumped = context.model_dump()
    assert dumped["user_id"] == "user-1"
    assert dumped["telegram_chat_id"] == "chat-1"
    assert dumped["conversation_id"] == "conv-1"
    assert dumped["license"] == "active"
    assert dumped["cookie_available"] is True
    assert dumped["current_job_id"] == "job-1"
    secret_keys = {
        "cookie",
        "cookies",
        "authorization",
        "api_key",
        "password",
        "bot_token",
        "token",
        "jwt",
        "secret",
    }
    assert secret_keys.isdisjoint(dumped.keys())


def test_context_rejects_secret_fields():
    payloads = [
        {"cookie": "sid=abc"},
        {"api_key": "sk-live"},
        {"password": "hunter2"},
        {"authorization": "Bearer abc"},
        {"bot_token": "123:abc"},
        {"metadata": {"api_key": "sk-live"}},
        {"metadata": {"authorization": "Bearer abc"}},
    ]
    for payload in payloads:
        try:
            AgentContext(message="hello", **payload)
        except (ValidationError, ValueError):
            continue
        raise AssertionError(f"secret payload was accepted: {payload}")


def test_conversation_schema_has_required_indexes():
    conv_indexes = {index.name for index in AgentConversation.__table__.indexes}
    assert "ix_agent_conversations_telegram_chat_id" in conv_indexes
    assert "ix_agent_conversations_user_channel" in conv_indexes
    constraint_names = {constraint.name for constraint in AgentConversation.__table__.constraints}
    assert "uq_agent_conv_user_channel_chat" in constraint_names
    message_indexes = {index.name for index in AgentMessage.__table__.indexes}
    assert "ix_agent_messages_conversation_created" in message_indexes
    tool_indexes = {index.name for index in AgentToolCall.__table__.indexes}
    assert "ix_agent_tool_calls_conversation_created" in tool_indexes


def test_create_and_get_conversation():
    async def scenario():
        memory = await _memory()
        created = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        fetched = await memory.get_conversation(created.id)
        again = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        assert fetched is not None
        assert fetched.id == created.id
        assert again.id == created.id
        assert created.telegram_chat_id == "chat-1"

    asyncio.run(scenario())


def test_telegram_chat_maps_consistently_and_not_by_chat_id_alone():
    async def scenario():
        memory = await _memory()
        first = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        same = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        other_user = await memory.get_or_create_conversation(
            user_id="user-2", channel="telegram", telegram_chat_id="chat-1"
        )
        other_chat = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-2"
        )
        assert first.id == same.id
        assert other_user.id != first.id
        assert other_chat.id != first.id

    asyncio.run(scenario())


def test_save_and_load_messages_preserve_order_and_limit():
    async def scenario():
        memory = await _memory(max_messages=3)
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        await memory.save_user_message(conversation.id, "1 old")
        await memory.save_assistant_message(conversation.id, "2 old")
        await memory.save_user_message(conversation.id, "3 recent")
        await memory.save_assistant_message(conversation.id, "4 recent")
        await memory.save_user_message(conversation.id, "5 recent")
        loaded = await memory.get_recent_messages(conversation.id)
        assert [item.content for item in loaded] == ["3 recent", "4 recent", "5 recent"]
        assert [item.role.value for item in loaded] == ["user", "assistant", "user"]
        chronological = await memory.get_recent_messages(conversation.id, limit=10)
        assert [item.content for item in chronological] == [
            "1 old",
            "2 old",
            "3 recent",
            "4 recent",
            "5 recent",
        ]

    asyncio.run(scenario())


def test_tool_call_lifecycle_and_latency():
    async def scenario():
        memory = await _memory()
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="internal", telegram_chat_id=""
        )
        user_message = await memory.save_user_message(conversation.id, "run tools")

        started = await memory.start_tool_call(
            conversation.id, "search_crawl_results", {"platform": "tiktok", "keyword": "hoodie"}, user_message.id
        )
        assert started.status == AgentToolCallStatus.RUNNING
        success = await memory.complete_tool_call(
            started.id,
            ToolResult(
                tool_call_id="call-1",
                tool_name="search_crawl_results",
                status=ToolResultStatus.OK,
                data={"count": 1},
            ),
            latency_ms=12,
        )
        assert success.status == AgentToolCallStatus.SUCCESS
        assert success.latency_ms == 12
        assert success.message_id == user_message.id

        failed = await memory.start_tool_call(conversation.id, "search_crawl_results", {"keyword": "x"})
        failed = await memory.complete_tool_call(
            failed.id,
            ToolResult(
                tool_call_id="call-2",
                tool_name="search_crawl_results",
                status=ToolResultStatus.ERROR,
                error_code="tool_execution_failed",
            ),
            latency_ms=3,
        )
        timed_out = await memory.start_tool_call(conversation.id, "slow_tool", {})
        timed_out = await memory.complete_tool_call(
            timed_out.id,
            ToolResult(
                tool_call_id="call-3",
                tool_name="slow_tool",
                status=ToolResultStatus.TIMEOUT,
                error_code="tool_timeout",
            ),
            latency_ms=1000,
        )
        denied = await memory.start_tool_call(conversation.id, "crawl_platform", {"platform": "tiktok"})
        denied = await memory.complete_tool_call(
            denied.id,
            ToolResult(
                tool_call_id="call-4",
                tool_name="crawl_platform",
                status=ToolResultStatus.DENIED,
                error_code="permission_denied",
            ),
            latency_ms=1,
        )
        records = await memory.list_tool_calls(conversation.id)
        assert [item.status for item in records] == [
            AgentToolCallStatus.SUCCESS,
            AgentToolCallStatus.FAILED,
            AgentToolCallStatus.TIMEOUT,
            AgentToolCallStatus.DENIED,
        ]
        assert records[0].latency_ms == 12
        assert records[2].latency_ms == 1000

    asyncio.run(scenario())


def test_secrets_are_redacted_before_persistence():
    async def scenario():
        memory = await _memory()
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        bot_token = "123456789:AAFakedTelegramBotTokenValue1234567"
        await memory.save_user_message(
            conversation.id,
            f"cookie=secret-cookie authorization=Bearer abc api_key=sk-live password=hunter2 {bot_token}",
        )
        await memory.save_assistant_message(conversation.id, f"token {bot_token}")
        started = await memory.start_tool_call(
            conversation.id,
            "search_crawl_results",
            {
                "cookie": "sid=abc",
                "authorization": "Bearer abc",
                "api_key": "sk-live",
                "password": "hunter2",
                "bot_token": bot_token,
                "keyword": "hoodie",
            },
        )
        completed = await memory.complete_tool_call(
            started.id,
            {
                "cookie": "sid=abc",
                "authorization": "Bearer abc",
                "api_key": "sk-live",
                "password": "hunter2",
                "url": "https://s3.amazonaws.com/x?X-Amz-Credential=AKIAxxx&X-Amz-Signature=deadbeef",
            },
            status=AgentToolCallStatus.SUCCESS,
            latency_ms=5,
        )
        messages = await memory.get_recent_messages(conversation.id)
        blob = " ".join(item.content for item in messages) + started.arguments_json + (completed.result_json or "")
        for secret in ("secret-cookie", "Bearer abc", "sk-live", "hunter2", bot_token, "AKIAxxx", "deadbeef"):
            assert secret not in blob
        assert REDACTED in started.arguments_json
        assert REDACTED in (completed.result_json or "")
        assert "hoodie" in started.arguments_json

    asyncio.run(scenario())


def test_sanitizer_redacts_sensitive_keys_and_presigned_credentials():
    payload = sanitize(
        {
            "cookie": "sid=abc",
            "authorization": "Bearer abc",
            "api_key": "sk-live",
            "password": "hunter2",
            "cookie_available": True,
            "keyword": "hoodie",
        }
    )
    assert payload["cookie"] == REDACTED
    assert payload["authorization"] == REDACTED
    assert payload["api_key"] == REDACTED
    assert payload["password"] == REDACTED
    assert payload["cookie_available"] is True
    assert payload["keyword"] == "hoodie"
    assert "Bearer super-secret" not in sanitize_text("Authorization: Bearer super-secret")


def test_short_term_state_ttl_and_restore():
    async def scenario():
        cache = DictTtlCache()
        state = AgentShortTermStateStore(cache, ttl_seconds=1)
        engine = create_agent_engine(in_memory=True)
        store = SqlAgentMemoryStore(engine)
        await store.create_schema()
        memory = AgentMemoryService(store, state, InMemoryConversationLock(timeout_seconds=0.05))
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        await memory.save_short_term_state(
            conversation.id,
            AgentShortTermState(
                current_job_id="job-9",
                current_idea_ids=["idea-9"],
                current_video_job_id="video-9",
                last_activity=1,
            ),
        )
        assert cache.get(f"{CONVERSATION_STATE_KEY_PREFIX}{conversation.id}")["current_job_id"] == "job-9"
        restored = await memory.get_short_term_state(conversation.id)
        assert restored is not None
        assert restored.current_job_id == "job-9"
        assert restored.current_idea_ids == ["idea-9"]
        await asyncio.sleep(1.2)
        assert await memory.get_short_term_state(conversation.id) is None

    asyncio.run(scenario())


def test_lock_acquire_release_and_timeout():
    async def scenario():
        lock = InMemoryConversationLock(ttl_seconds=30, timeout_seconds=0)
        assert await lock.acquire("conv-1") is True
        assert await lock.acquire("conv-1") is False
        await lock.release("conv-1")
        assert await lock.acquire("conv-1") is True
        await lock.release("conv-1")

        expiring = InMemoryConversationLock(ttl_seconds=0.05, timeout_seconds=0)
        assert await expiring.acquire("conv-2") is True
        await asyncio.sleep(0.12)
        assert await expiring.acquire("conv-2") is True

        blocking = InMemoryConversationLock(ttl_seconds=30, timeout_seconds=0.05)
        assert await blocking.acquire("conv-3") is True
        started = time.monotonic()
        assert await blocking.acquire("conv-3") is False
        assert time.monotonic() - started < 1.0
        assert RedisConversationLock._key("conv-9") == f"{LOCK_KEY_PREFIX}conv-9"

    asyncio.run(scenario())


def test_agent_loop_persists_user_tool_and_assistant_memory(tmp_path: Path):
    async def scenario():
        data_file = tmp_path / "tiktok" / "jsonl" / "search_contents.jsonl"
        data_file.parent.mkdir(parents=True)
        data_file.write_text(
            '{"aweme_id":"1","title":"Blue hoodie","desc":"warm hoodie","source_keyword":"hoodie"}\n',
            encoding="utf-8",
        )
        memory = await _memory(max_messages=10)
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
        response = await AgentLoop(llm, ToolRegistry([tool]), memory=memory).run(
            AgentContext(
                message="find hoodie",
                user_id="user-1",
                channel="telegram",
                telegram_chat_id="chat-1",
                authenticated=True,
                license="active",
                permissions={"crawl_results:read"},
            )
        )
        assert response.answer == "Found one stored result."
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        messages = await memory.get_recent_messages(conversation.id)
        assert [item.role.value for item in messages] == ["user", "assistant"]
        assert messages[0].content == "find hoodie"
        assert messages[1].content == "Found one stored result."
        tool_calls = await memory.list_tool_calls(conversation.id)
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "search_crawl_results"
        assert tool_calls[0].status == AgentToolCallStatus.SUCCESS
        assert tool_calls[0].latency_ms is not None
        assert llm.contexts[0].conversation_id == conversation.id
        restored = await memory.get_short_term_state(conversation.id)
        assert restored is not None

        follow_up = ScriptedLLM([LLMResponse(final_answer="Still the hoodie from before.")])
        await AgentLoop(follow_up, ToolRegistry([tool]), memory=memory).run(
            AgentContext(
                message="what did I ask?",
                user_id="user-1",
                channel="telegram",
                telegram_chat_id="chat-1",
                authenticated=True,
                license="active",
                permissions={"crawl_results:read"},
            )
        )
        assert follow_up.contexts[0].history[0].content == "find hoodie"
        assert follow_up.contexts[0].history[1].content == "Found one stored result."

    asyncio.run(scenario())


def test_memory_unavailable_does_not_start_crawl():
    async def scenario():
        jobs = FakeCrawlerJobs()
        llm = ScriptedLLM(
            [
                LLMResponse(
                    tool_calls=[
                        ToolCall(
                            id="crawl-1",
                            name="crawl_platform",
                            arguments={"platform": "tiktok", "keyword": "hoodie", "limit": 20},
                        )
                    ]
                )
            ]
        )
        response = await AgentLoop(
            llm, ToolRegistry([CrawlPlatformTool(jobs)]), memory=DeadMemory()
        ).run(
            AgentContext(
                message="Crawl 20 video hoodie trên TikTok",
                user_id="user-1",
                channel="telegram",
                telegram_chat_id="chat-1",
                authenticated=True,
                license="active",
                permissions={"crawler:run"},
                quota_remaining=2,
            )
        )
        assert jobs.calls == []
        assert response.error == "memory_unavailable"
        assert llm.contexts == []

    asyncio.run(scenario())


def test_lock_timeout_does_not_run_tools():
    async def scenario():
        memory = await _memory()
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        assert await memory.acquire_lock(conversation.id) is True
        jobs = FakeCrawlerJobs()
        llm = ScriptedLLM(
            [
                LLMResponse(
                    tool_calls=[
                        ToolCall(
                            id="crawl-1",
                            name="crawl_platform",
                            arguments={"platform": "tiktok", "keyword": "hoodie", "limit": 20},
                        )
                    ]
                )
            ]
        )
        response = await AgentLoop(
            llm, ToolRegistry([CrawlPlatformTool(jobs)]), memory=memory
        ).run(
            AgentContext(
                message="Crawl 20 video hoodie trên TikTok",
                user_id="user-1",
                channel="telegram",
                telegram_chat_id="chat-1",
                authenticated=True,
                license="active",
                permissions={"crawler:run"},
                quota_remaining=2,
            )
        )
        assert jobs.calls == []
        assert response.error == "conversation_busy"
        assert llm.contexts == []
        await memory.release_lock(conversation.id)

    asyncio.run(scenario())


def test_telegram_natural_language_uses_stable_conversation_id():
    async def scenario():
        memory = await _memory()
        llm = ScriptedLLM([LLMResponse(final_answer="Xin chào"), LLMResponse(final_answer="Xin chào")])
        adapter = TelegramAgentHandler(
            LegacyHandler(),
            FakeResolver(cookie_available=True),
            AgentLoop(llm, ToolRegistry(), memory=memory),
        )
        first = await adapter.handle(update("Tìm video hoodie"))
        second = await adapter.handle(update("còn gì nữa không"))
        assert first.text == "Xin chào"
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        assert llm.contexts[0].conversation_id == conversation.id
        assert llm.contexts[1].conversation_id == conversation.id
        assert llm.contexts[0].cookie_available is True
        assert "cookie" not in llm.contexts[0].model_dump()
        messages = await memory.get_recent_messages(conversation.id)
        assert [item.content for item in messages] == [
            "Tìm video hoodie",
            "Xin chào",
            "còn gì nữa không",
            "Xin chào",
        ]
        assert second.text == "Xin chào"

    asyncio.run(scenario())


def test_slash_commands_bypass_agent_memory():
    async def scenario():
        memory = await _memory()
        legacy = LegacyHandler()
        llm = ScriptedLLM([LLMResponse(final_answer="unused")])
        adapter = TelegramAgentHandler(
            legacy,
            FakeResolver(),
            AgentLoop(llm, ToolRegistry(), memory=memory),
        )
        for command in ("/status", "/kichhoat", "/goi", "/hot", "/crawl", "/ketqua"):
            response = await adapter.handle(update(command))
            assert response.text == f"legacy:{command}"
        assert llm.contexts == []
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        assert await memory.get_recent_messages(conversation.id) == []

    asyncio.run(scenario())


def test_lock_backend_failure_is_explicit():
    async def scenario():
        class BoomLock:
            async def acquire(self, conversation_id):
                raise ConnectionError("redis down")

            async def release(self, conversation_id):
                return None

        engine = create_agent_engine(in_memory=True)
        store = SqlAgentMemoryStore(engine)
        await store.create_schema()
        memory = AgentMemoryService(store, AgentShortTermStateStore(DictTtlCache()), BoomLock())
        try:
            await memory.acquire_lock("conv-1")
        except AgentMemoryUnavailable:
            return
        raise AssertionError("lock backend failure must be explicit")

    asyncio.run(scenario())


def test_telegram_busy_lock_is_explicit():
    async def scenario():
        memory = await _memory()
        conversation = await memory.get_or_create_conversation(
            user_id="user-1", channel="telegram", telegram_chat_id="chat-1"
        )
        assert await memory.acquire_lock(conversation.id) is True
        adapter = TelegramAgentHandler(
            LegacyHandler(),
            FakeResolver(),
            AgentLoop(ScriptedLLM([LLMResponse(final_answer="unused")]), ToolRegistry(), memory=memory),
        )
        response = await adapter.handle(update("Tìm video hoodie"))
        assert response.error == "conversation_busy"
        assert "thử lại" in response.text
        await memory.release_lock(conversation.id)

    asyncio.run(scenario())
