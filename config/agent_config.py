# -*- coding: utf-8 -*-
"""Configuration for the read-only Agent Loop.

Secrets stay in the process environment and are deliberately not copied into
AgentContext or tool inputs.
"""
import os


MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "4"))
AGENT_REQUEST_TIMEOUT_SECONDS = float(os.getenv("AGENT_REQUEST_TIMEOUT_SECONDS", "45"))
AGENT_TOOL_TIMEOUT_SECONDS = float(os.getenv("AGENT_TOOL_TIMEOUT_SECONDS", "10"))

AGENT_LLM_ENABLED = os.getenv("AGENT_LLM_ENABLED", "false").lower() in ("1", "true", "yes")
AGENT_LLM_BASE_URL = os.getenv("AGENT_LLM_BASE_URL", "https://api.openai.com/v1")
AGENT_LLM_MODEL = os.getenv("AGENT_LLM_MODEL", "gpt-4o-mini")
AGENT_LLM_API_KEY = os.getenv("AGENT_LLM_API_KEY", "")
