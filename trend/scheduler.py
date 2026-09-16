# -*- coding: utf-8 -*-
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from trend.alerts import maybe_alert
from trend.marketplace import source_product
from trend.media import download_videos
from trend.score import score_all
from trend.settings import get_settings
from trend.store import TrendStore

_task: Optional[asyncio.Task] = None
_running = False
_last_run: Optional[int] = None
_last_result: Optional[Dict[str, Any]] = None


def _cron_due(expr: str, now: datetime) -> bool:
    parts = expr.split()
    if len(parts) < 5:
        return False
    minute, hour, *_rest = parts

    def match(field: str, value: int) -> bool:
        if field == "*":
            return True
        if field.startswith("*/"):
            try:
                step = int(field[2:])
            except ValueError:
                return False
            return step > 0 and value % step == 0
        try:
            return int(field) == value
        except ValueError:
            return False

    return match(minute, now.minute) and match(hour, now.hour)


async def process_scan() -> Dict[str, Any]:
    started = int(time.time())
    store = TrendStore()
    result = await score_all(store)
    settings = get_settings()
    alerts = 0
    media = 0
    listings = 0
    for item in result.get("scored") or []:
        if settings.get("TREND_MARKETPLACE_ENABLED") and int(item.get("confidence") or 0) >= int(settings["TREND_MIN_CONFIDENCE"]):
            sourced = await source_product(item["product_key"], item.get("name") or "", store)
            item["listings"] = sourced
            listings += len(sourced)
        if settings.get("TREND_DOWNLOAD_MEDIA"):
            saved = await download_videos(item.get("videos") or [], store)
            media += len(saved)
        if await maybe_alert(item, store):
            alerts += 1
    detail = {
        "products": result.get("count") or 0,
        "alerts": alerts,
        "media": media,
        "listings": listings,
    }
    await store.save_scan_run("ok", detail, started)
    global _last_run, _last_result
    _last_run = started
    _last_result = detail
    return detail


async def _loop() -> None:
    global _running
    _running = True
    last_cron_slot = None
    while _running:
        settings = get_settings()
        if not settings.get("TREND_SCHEDULER_ENABLED"):
            await asyncio.sleep(15)
            continue
        cron = (settings.get("TREND_SCAN_CRON") or "").strip()
        now = datetime.now(timezone.utc).astimezone()
        due = False
        if cron:
            slot = (now.year, now.month, now.day, now.hour, now.minute)
            if slot != last_cron_slot and _cron_due(cron, now):
                due = True
                last_cron_slot = slot
            sleep_for = 20
        else:
            interval = max(float(settings.get("TREND_SCAN_INTERVAL_HOURS") or 6), 0.05) * 3600
            if _last_run is None or (time.time() - _last_run) >= interval:
                due = True
            sleep_for = min(60, max(10, interval / 12))
        if due:
            try:
                await process_scan()
            except Exception:
                store = TrendStore()
                await store.save_scan_run("error", {"error": "scan failed"}, int(time.time()))
        await asyncio.sleep(sleep_for)


async def start_scheduler() -> None:
    global _task, _running
    if _task and not _task.done():
        return
    _running = True
    _task = asyncio.create_task(_loop())


async def stop_scheduler() -> None:
    global _task, _running
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None


def scheduler_status() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "enabled": bool(settings.get("TREND_SCHEDULER_ENABLED")),
        "running": bool(_task and not _task.done()),
        "last_run": _last_run,
        "last_result": _last_result,
        "interval_hours": settings.get("TREND_SCAN_INTERVAL_HOURS"),
        "cron": settings.get("TREND_SCAN_CRON"),
    }
