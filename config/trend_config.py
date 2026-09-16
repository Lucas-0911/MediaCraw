# -*- coding: utf-8 -*-
"""Trend Radar defaults. Override via env or data/trend_settings.json."""

import os

TREND_SCAN_INTERVAL_HOURS = float(os.getenv("TREND_SCAN_INTERVAL_HOURS", "6"))
TREND_SCAN_CRON = os.getenv("TREND_SCAN_CRON", "")
TREND_SNAPSHOT_GAP_HOURS = float(os.getenv("TREND_SNAPSHOT_GAP_HOURS", "6"))
TREND_ALERT_COOLDOWN_HOURS = float(os.getenv("TREND_ALERT_COOLDOWN_HOURS", "12"))

TREND_VIDEOS_PER_ALERT = int(os.getenv("TREND_VIDEOS_PER_ALERT", "5"))
TREND_VIDEO_MIN_AGE_HOURS = float(os.getenv("TREND_VIDEO_MIN_AGE_HOURS", "2"))
TREND_VIDEO_MAX_AGE_DAYS = float(os.getenv("TREND_VIDEO_MAX_AGE_DAYS", "10"))
TREND_REQUIRE_PLAY_INCREASE = os.getenv("TREND_REQUIRE_PLAY_INCREASE", "true").lower() in ("1", "true", "yes")
TREND_VIDEO_SORT = os.getenv("TREND_VIDEO_SORT", "play_velocity")

TREND_MIN_CONFIDENCE = int(os.getenv("TREND_MIN_CONFIDENCE", "4"))
TREND_MIN_MENTION = int(os.getenv("TREND_MIN_MENTION", "5"))
TREND_MIN_SPREAD = int(os.getenv("TREND_MIN_SPREAD", "3"))
TREND_MIN_INTENT_N = int(os.getenv("TREND_MIN_INTENT_N", "8"))
TREND_MIN_INTENT_WILSON = float(os.getenv("TREND_MIN_INTENT_WILSON", "0.08"))
TREND_MIN_NAME_VIDEOS = int(os.getenv("TREND_MIN_NAME_VIDEOS", "5"))

TREND_HOT_HEATNOW = float(os.getenv("TREND_HOT_HEATNOW", "0.70"))
TREND_RISING_HEATNOW_MIN = float(os.getenv("TREND_RISING_HEATNOW_MIN", "0.40"))
TREND_RISING_DELTA_RATIO = float(os.getenv("TREND_RISING_DELTA_RATIO", "0.25"))

TREND_GOOGLE_TRENDS_ENABLED = os.getenv("TREND_GOOGLE_TRENDS_ENABLED", "true").lower() in ("1", "true", "yes")
TREND_LLM_ENABLED = os.getenv("TREND_LLM_ENABLED", "false").lower() in ("1", "true", "yes")
TREND_LLM_BASE_URL = os.getenv("TREND_LLM_BASE_URL", "https://api.openai.com/v1")
TREND_LLM_MODEL = os.getenv("TREND_LLM_MODEL", "gpt-4o-mini")
TREND_LLM_API_KEY = os.getenv("TREND_LLM_API_KEY", "")

TREND_PLATFORMS = os.getenv("TREND_PLATFORMS", "dy,tiktok")
TREND_DOWNLOAD_MEDIA = os.getenv("TREND_DOWNLOAD_MEDIA", "false").lower() in ("1", "true", "yes")
TREND_MAX_MEDIA_PER_SCAN = int(os.getenv("TREND_MAX_MEDIA_PER_SCAN", "20"))

TREND_MARKETPLACE_ENABLED = os.getenv("TREND_MARKETPLACE_ENABLED", "true").lower() in ("1", "true", "yes")
TREND_SHOPEE_ENABLED = os.getenv("TREND_SHOPEE_ENABLED", "true").lower() in ("1", "true", "yes")
TREND_LAZADA_ENABLED = os.getenv("TREND_LAZADA_ENABLED", "true").lower() in ("1", "true", "yes")
TREND_ORDER_MODE = os.getenv("TREND_ORDER_MODE", "draft")

TREND_WEIGHT_PLAY_VEL = float(os.getenv("TREND_WEIGHT_PLAY_VEL", "0.35"))
TREND_WEIGHT_ENG_VEL = float(os.getenv("TREND_WEIGHT_ENG_VEL", "0.20"))
TREND_WEIGHT_MENTION = float(os.getenv("TREND_WEIGHT_MENTION", "0.20"))
TREND_WEIGHT_SPREAD = float(os.getenv("TREND_WEIGHT_SPREAD", "0.15"))
TREND_WEIGHT_INTENT = float(os.getenv("TREND_WEIGHT_INTENT", "0.10"))

TREND_TELEGRAM_BOT_TOKEN = os.getenv("TREND_TELEGRAM_BOT_TOKEN", "")
TREND_TELEGRAM_CHAT_ID = os.getenv("TREND_TELEGRAM_CHAT_ID", "")
TREND_KEYWORDS = os.getenv("TREND_KEYWORDS", "")
TREND_SCHEDULER_ENABLED = os.getenv("TREND_SCHEDULER_ENABLED", "false").lower() in ("1", "true", "yes")
TREND_TRIGGER_CRAWL = os.getenv("TREND_TRIGGER_CRAWL", "false").lower() in ("1", "true", "yes")

TREND_DB_PATH = os.getenv("TREND_DB_PATH", "data/trend.sqlite")
TREND_SETTINGS_PATH = os.getenv("TREND_SETTINGS_PATH", "data/trend_settings.json")
