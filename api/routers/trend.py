# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trend.marketplace import source_product
from trend.media import download_videos
from trend.scheduler import process_scan, scheduler_status, start_scheduler, stop_scheduler
from trend.settings import get_settings, update_settings
from trend.store import TrendStore

router = APIRouter(prefix="/trend", tags=["trend"])


class SettingsPatch(BaseModel):
    settings: Dict[str, Any]


class MarketplaceRequest(BaseModel):
    product_key: Optional[str] = None


@router.get("/settings")
async def trend_settings():
    return {"settings": get_settings(mask_secrets=True)}


@router.put("/settings")
async def save_trend_settings(body: SettingsPatch):
    return {"settings": update_settings(body.settings)}


@router.get("/products")
async def list_products(min_confidence: int = 0):
    store = TrendStore()
    products = await store.list_products(min_confidence=min_confidence)
    for item in products:
        if isinstance(item.get("gates_json"), str):
            try:
                item["gates"] = json.loads(item["gates_json"] or "{}")
            except Exception:
                item["gates"] = {}
        else:
            item["gates"] = item.get("gates_json") or {}
    return {"products": products}


@router.get("/products/{product_key:path}")
async def product_detail(product_key: str):
    store = TrendStore()
    product = await store.get_product(product_key)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        product["gates"] = json.loads(product.get("gates_json") or "{}")
    except Exception:
        product["gates"] = {}
    videos = await store.videos_for(product_key)
    snapshots = await store.snapshots_for(product_key, limit=8)
    listings = await store.listings_for(product_key)
    return {"product": product, "videos": videos, "snapshots": snapshots, "listings": listings}


@router.get("/alerts")
async def list_alerts(limit: int = 50):
    store = TrendStore()
    return {"alerts": await store.list_alerts(limit=limit)}


@router.post("/scan")
async def run_scan():
    detail = await process_scan()
    return {"status": "ok", "detail": detail}


@router.get("/scheduler")
async def get_scheduler():
    return scheduler_status()


@router.post("/scheduler/start")
async def enable_scheduler():
    update_settings({"TREND_SCHEDULER_ENABLED": True})
    await start_scheduler()
    return scheduler_status()


@router.post("/scheduler/stop")
async def disable_scheduler():
    update_settings({"TREND_SCHEDULER_ENABLED": False})
    return scheduler_status()


@router.post("/products/{product_key:path}/marketplace")
async def run_marketplace(product_key: str):
    store = TrendStore()
    product = await store.get_product(product_key)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    listings = await source_product(product_key, product.get("name") or product_key, store)
    return {"listings": listings}


@router.post("/products/{product_key:path}/media")
async def run_media(product_key: str):
    store = TrendStore()
    videos = await store.videos_for(product_key)
    saved = await download_videos(videos, store)
    return {"saved": saved}


@router.post("/telegram/test")
async def telegram_test():
    from trend.alerts import send_telegram

    ok = await send_telegram("Trend Radar test")
    return {"ok": bool(ok)}
