# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""ORM models for Agent conversation memory.

These tables live on the shared SQLAlchemy Base but are kept out of
database.models' public namespace so crawler privacy introspection is unchanged.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from database.models import Base


class AgentConversation(Base):
    """Long-lived Agent conversation/session. Not an AgentContext snapshot."""

    __tablename__ = "agent_conversations"
    id = Column(String(36), primary_key=True, comment="Conversation UUID")
    user_id = Column(String(256), nullable=False, comment="Authenticated application user")
    channel = Column(String(32), nullable=False, comment="Inbound channel")
    telegram_chat_id = Column(String(256), nullable=False, default="", comment="Telegram chat id")
    created_at = Column(BigInteger, nullable=False, comment="Created timestamp (ms)")
    updated_at = Column(BigInteger, nullable=False, comment="Updated timestamp (ms)")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "channel",
            "telegram_chat_id",
            name="uq_agent_conv_user_channel_chat",
        ),
        Index("ix_agent_conversations_telegram_chat_id", "telegram_chat_id"),
        Index("ix_agent_conversations_user_channel", "user_id", "channel"),
    )


class AgentMessage(Base):
    """Persisted conversation turn. Secrets must be sanitized before insert."""

    __tablename__ = "agent_messages"
    id = Column(String(36), primary_key=True, comment="Message UUID")
    conversation_id = Column(
        String(36),
        ForeignKey("agent_conversations.id"),
        nullable=False,
        comment="Parent conversation",
    )
    role = Column(String(32), nullable=False, comment="user/assistant/system/tool")
    content = Column(Text, nullable=False, comment="Sanitized message content")
    created_at = Column(BigInteger, nullable=False, comment="Created timestamp (ms)")

    __table_args__ = (Index("ix_agent_messages_conversation_created", "conversation_id", "created_at"),)


class AgentToolCall(Base):
    """Persisted tool invocation for a conversation. Payloads are sanitized."""

    __tablename__ = "agent_tool_calls"
    id = Column(String(36), primary_key=True, comment="Tool-call UUID")
    conversation_id = Column(
        String(36),
        ForeignKey("agent_conversations.id"),
        nullable=False,
        comment="Parent conversation",
    )
    message_id = Column(
        String(36),
        ForeignKey("agent_messages.id"),
        nullable=True,
        comment="Related message if applicable",
    )
    tool_name = Column(String(128), nullable=False, comment="Registered tool name")
    arguments_json = Column(Text, nullable=False, default="{}", comment="Sanitized arguments JSON")
    result_json = Column(Text, comment="Sanitized result JSON")
    status = Column(String(32), nullable=False, comment="RUNNING/SUCCESS/FAILED/TIMEOUT/DENIED")
    latency_ms = Column(Integer, comment="Execution latency in milliseconds")
    created_at = Column(BigInteger, nullable=False, comment="Created timestamp (ms)")

    __table_args__ = (Index("ix_agent_tool_calls_conversation_created", "conversation_id", "created_at"),)
