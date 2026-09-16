# -*- coding: utf-8 -*-
"""Routing-only Telegram adapter: legacy commands or AgentLoop."""
from __future__ import annotations

from typing import Protocol

from agent_core.contracts import AgentContext
from agent_core.loop import AgentLoop

from .auth import TelegramUserResolver
from .contracts import TelegramMessageResponse, TelegramUpdate
from .presenter import TelegramResponseMapper


class LegacyCommandHandler(Protocol):
    async def handle(self, update: TelegramUpdate) -> TelegramMessageResponse:
        """Delegate raw slash-command updates to the existing command handler."""


class TelegramAgentHandler:
    def __init__(
        self,
        command_handler: LegacyCommandHandler,
        user_resolver: TelegramUserResolver,
        agent_loop: AgentLoop,
        response_mapper: TelegramResponseMapper | None = None,
    ) -> None:
        self._command_handler = command_handler
        self._user_resolver = user_resolver
        self._agent_loop = agent_loop
        self._response_mapper = response_mapper or TelegramResponseMapper()

    async def handle(self, update: TelegramUpdate) -> TelegramMessageResponse:
        if update.text.lstrip().startswith("/"):
            # Keep the original update untouched so legacy command parsing and
            # response behavior remain entirely owned by the old handler.
            return await self._command_handler.handle(update)

        user = await self._user_resolver.resolve(update)
        context = AgentContext(
            channel="telegram",
            actor_id=f"telegram:{user.user_id}",
            user_id=user.user_id,
            telegram_chat_id=update.chat_id,
            conversation_id=f"telegram:{update.chat_id}:{user.user_id}",
            message=update.text,
            locale=update.locale,
            authenticated=user.authenticated,
            license=user.license,
            permissions=user.permissions,
            quota_remaining=user.quota_remaining,
            current_job_id=user.current_job_id,
            current_idea_ids=user.current_idea_ids,
            current_video_job_id=user.current_video_job_id,
            metadata={"telegram_update_id": update.update_id, "telegram_message_id": update.message_id},
        )
        return self._response_mapper.map(await self._agent_loop.run(context))
