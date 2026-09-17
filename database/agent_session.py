# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""SQLAlchemy engine/session factory for Agent conversation memory.

Crawler storage still uses SAVE_DATA_OPTION. Agent memory is independent so it
can persist conversations even when crawl results are written as JSON/CSV.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config import agent_config
from config.db_config import mysql_db_config, postgres_db_config
from database.agent_models import AgentConversation, AgentMessage, AgentToolCall

_engines: dict[str, AsyncEngine] = {}


AGENT_TABLES = (
    AgentConversation.__table__,
    AgentMessage.__table__,
    AgentToolCall.__table__,
)


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _fk_pragma(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_agent_engine(
    db_type: Optional[str] = None,
    *,
    sqlite_path: Optional[str] = None,
    in_memory: bool = False,
) -> AsyncEngine:
    db_type = db_type or agent_config.AGENT_MEMORY_DB_TYPE
    if in_memory:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        _enable_sqlite_foreign_keys(engine)
        return engine

    cache_key = f"{db_type}:{sqlite_path or agent_config.AGENT_MEMORY_SQLITE_PATH}"
    if cache_key in _engines:
        return _engines[cache_key]

    if db_type == "sqlite":
        path = sqlite_path or agent_config.AGENT_MEMORY_SQLITE_PATH
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
        _enable_sqlite_foreign_keys(engine)
    elif db_type in ("mysql", "db"):
        engine = create_async_engine(
            (
                f"mysql+asyncmy://{mysql_db_config['user']}:{mysql_db_config['password']}"
                f"@{mysql_db_config['host']}:{mysql_db_config['port']}/{mysql_db_config['db_name']}"
            ),
            echo=False,
        )
    elif db_type == "postgres":
        engine = create_async_engine(
            (
                f"postgresql+asyncpg://{postgres_db_config['user']}:{postgres_db_config['password']}"
                f"@{postgres_db_config['host']}:{postgres_db_config['port']}/{postgres_db_config['db_name']}"
            ),
            echo=False,
        )
    else:
        raise ValueError(f"Unsupported agent memory database type: {db_type}")

    _engines[cache_key] = engine
    return engine


async def create_agent_tables(engine: Optional[AsyncEngine] = None) -> None:
    engine = engine or create_agent_engine()
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: AgentConversation.metadata.create_all(sync_conn, tables=list(AGENT_TABLES)))


@asynccontextmanager
async def get_agent_session(engine: Optional[AsyncEngine] = None) -> AsyncIterator[AsyncSession]:
    engine = engine or create_agent_engine()
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
