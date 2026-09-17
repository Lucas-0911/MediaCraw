# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Hard rules: the Agent may call registered service functions only.

It must never run SQL, shell, or database clients. Persistence happens inside
application services invoked by allowlisted tools.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

FORBIDDEN_TOOL_NAMES = {
    "sql",
    "execute_sql",
    "run_sql",
    "raw_sql",
    "query_db",
    "query_database",
    "db",
    "database",
    "psql",
    "mysql",
    "sqlite",
    "sqlite3",
    "mongodb",
    "redis_cli",
    "shell",
    "bash",
    "sh",
    "zsh",
    "cmd",
    "powershell",
    "eval",
    "exec",
    "run_command",
    "system",
    "os_system",
    "subprocess",
    "python_eval",
}

_FORBIDDEN_NAME_PARTS = (
    "execute_sql",
    "run_sql",
    "raw_sql",
    "raw_query",
    "db_query",
    "sql_query",
    "shell",
    "subprocess",
    "os_system",
)

# Require a statement shape so product keywords like "drop hoodie" stay allowed.
_SQL_STATEMENT = re.compile(
    r"(?is)\b(select|insert|update|delete|drop|alter|truncate|create|grant|revoke|"
    r"replace|upsert|merge|explain|pragma|attach|detach|vacuum|analyze)\b"
    r".{0,200}\b(from|into|table|database|index|schema|view|on|set|exists|values)\b"
)
_CONNECTION_URI = re.compile(
    r"(?i)\b(postgres(ql)?|mysql|mariadb|sqlite|mongodb(\+srv)?|redis)://"
)
_DB_CLIENT = re.compile(
    r"(?i)\b(psql|mysql|mysqldump|sqlite3|mongosh|mongo|redis-cli|createdb|dropdb)\b"
)
_SHELL_INJECTION = re.compile(r"(?i)\b(bash|sh|zsh|cmd\.exe|powershell)\b.*[-/c]\s")


class PolicyDenial:
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message


def normalize_tool_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def is_forbidden_tool_name(name: str) -> bool:
    normalized = normalize_tool_name(name)
    if normalized in FORBIDDEN_TOOL_NAMES:
        return True
    return any(part in normalized for part in _FORBIDDEN_NAME_PARTS)


def inspect_tool_name(name: str) -> Optional[PolicyDenial]:
    if is_forbidden_tool_name(name):
        return PolicyDenial(
            "database_command_denied",
            "The Agent may only call registered application functions, never SQL or database commands.",
        )
    return None


def inspect_arguments(arguments: Mapping[str, Any] | None) -> Optional[PolicyDenial]:
    if not arguments:
        return None
    for value in _walk_strings(arguments):
        denial = inspect_text(value)
        if denial:
            return denial
    return None


def inspect_text(text: str) -> Optional[PolicyDenial]:
    sample = text.strip()
    if not sample:
        return None
    if _CONNECTION_URI.search(sample) or _DB_CLIENT.search(sample):
        return PolicyDenial(
            "database_command_denied",
            "Database clients, URIs and admin commands are not allowed. Use registered tools.",
        )
    if _SQL_STATEMENT.search(sample):
        return PolicyDenial(
            "database_command_denied",
            "SQL and schema commands are not allowed. Use registered tools that wrap services.",
        )
    if _SHELL_INJECTION.search(sample):
        return PolicyDenial(
            "unsafe_operation",
            "Shell execution is not allowed. Use registered tools.",
        )
    return None


def inspect_tool_call(name: str, arguments: Mapping[str, Any] | None) -> Optional[PolicyDenial]:
    return inspect_tool_name(name) or inspect_arguments(arguments)


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        found: list[str] = []
        for item in value.values():
            found.extend(_walk_strings(item))
        return found
    if isinstance(value, (list, tuple)):
        found: list[str] = []
        for item in value:
            found.extend(_walk_strings(item))
        return found
    return []
