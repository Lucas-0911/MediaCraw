# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import Any, Dict

import config.trend_config as trend_defaults

SETTING_KEYS = [
    "TREND_SCAN_INTERVAL_HOURS",
    "TREND_SCAN_CRON",
    "TREND_SNAPSHOT_GAP_HOURS",
    "TREND_ALERT_COOLDOWN_HOURS",
    "TREND_VIDEOS_PER_ALERT",
    "TREND_VIDEO_MIN_AGE_HOURS",
    "TREND_VIDEO_MAX_AGE_DAYS",
    "TREND_REQUIRE_PLAY_INCREASE",
    "TREND_VIDEO_SORT",
    "TREND_MIN_CONFIDENCE",
    "TREND_MIN_MENTION",
    "TREND_MIN_SPREAD",
    "TREND_MIN_INTENT_N",
    "TREND_MIN_INTENT_WILSON",
    "TREND_MIN_NAME_VIDEOS",
    "TREND_HOT_HEATNOW",
    "TREND_RISING_HEATNOW_MIN",
    "TREND_RISING_DELTA_RATIO",
    "TREND_GOOGLE_TRENDS_ENABLED",
    "TREND_LLM_ENABLED",
    "TREND_LLM_BASE_URL",
    "TREND_LLM_MODEL",
    "TREND_LLM_API_KEY",
    "TREND_PLATFORMS",
    "TREND_DOWNLOAD_MEDIA",
    "TREND_MAX_MEDIA_PER_SCAN",
    "TREND_MARKETPLACE_ENABLED",
    "TREND_SHOPEE_ENABLED",
    "TREND_LAZADA_ENABLED",
    "TREND_ORDER_MODE",
    "TREND_WEIGHT_PLAY_VEL",
    "TREND_WEIGHT_ENG_VEL",
    "TREND_WEIGHT_MENTION",
    "TREND_WEIGHT_SPREAD",
    "TREND_WEIGHT_INTENT",
    "TREND_TELEGRAM_BOT_TOKEN",
    "TREND_TELEGRAM_CHAT_ID",
    "TREND_KEYWORDS",
    "TREND_SCHEDULER_ENABLED",
    "TREND_TRIGGER_CRAWL",
    "TREND_DB_PATH",
    "TREND_SETTINGS_PATH",
]

_BOOL_KEYS = {
    "TREND_REQUIRE_PLAY_INCREASE",
    "TREND_GOOGLE_TRENDS_ENABLED",
    "TREND_LLM_ENABLED",
    "TREND_DOWNLOAD_MEDIA",
    "TREND_MARKETPLACE_ENABLED",
    "TREND_SHOPEE_ENABLED",
    "TREND_LAZADA_ENABLED",
    "TREND_SCHEDULER_ENABLED",
    "TREND_TRIGGER_CRAWL",
}

_INT_KEYS = {
    "TREND_VIDEOS_PER_ALERT",
    "TREND_MIN_CONFIDENCE",
    "TREND_MIN_MENTION",
    "TREND_MIN_SPREAD",
    "TREND_MIN_INTENT_N",
    "TREND_MIN_NAME_VIDEOS",
    "TREND_MAX_MEDIA_PER_SCAN",
}

_FLOAT_KEYS = {
    "TREND_SCAN_INTERVAL_HOURS",
    "TREND_SNAPSHOT_GAP_HOURS",
    "TREND_ALERT_COOLDOWN_HOURS",
    "TREND_VIDEO_MIN_AGE_HOURS",
    "TREND_VIDEO_MAX_AGE_DAYS",
    "TREND_MIN_INTENT_WILSON",
    "TREND_HOT_HEATNOW",
    "TREND_RISING_HEATNOW_MIN",
    "TREND_RISING_DELTA_RATIO",
    "TREND_WEIGHT_PLAY_VEL",
    "TREND_WEIGHT_ENG_VEL",
    "TREND_WEIGHT_MENTION",
    "TREND_WEIGHT_SPREAD",
    "TREND_WEIGHT_INTENT",
}

_SECRET_KEYS = {"TREND_LLM_API_KEY", "TREND_TELEGRAM_BOT_TOKEN"}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _settings_path() -> Path:
    raw = os.getenv("TREND_SETTINGS_PATH") or getattr(
        trend_defaults, "TREND_SETTINGS_PATH", "data/trend_settings.json"
    )
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _cast(key: str, value: Any) -> Any:
    if value is None:
        return value
    if key in _BOOL_KEYS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")
    if key in _INT_KEYS:
        return int(value)
    if key in _FLOAT_KEYS:
        return float(value)
    return value


def _defaults() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in SETTING_KEYS:
        out[key] = _cast(key, getattr(trend_defaults, key, None))
    return out


def _load_file() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: _cast(k, v) for k, v in data.items() if k in SETTING_KEYS}


def _env_overrides() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in SETTING_KEYS:
        if key in os.environ:
            out[key] = _cast(key, os.environ[key])
    return out


def get_settings(mask_secrets: bool = False) -> Dict[str, Any]:
    merged = _defaults()
    merged.update(_env_overrides())
    merged.update(_load_file())
    if mask_secrets:
        for key in _SECRET_KEYS:
            val = merged.get(key) or ""
            if val:
                merged[key] = "***"
    return merged


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    current = get_settings(mask_secrets=False)
    for key, value in patch.items():
        if key not in SETTING_KEYS:
            continue
        if key in _SECRET_KEYS and value in ("***", None, ""):
            if value in ("***", None):
                continue
        current[key] = _cast(key, value)
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = dict(current)
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_settings(mask_secrets=True)


def db_path() -> Path:
    settings = get_settings()
    raw = settings.get("TREND_DB_PATH") or "data/trend.sqlite"
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
