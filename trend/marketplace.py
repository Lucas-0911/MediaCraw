# -*- coding: utf-8 -*-
import csv
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import httpx

from trend.settings import get_settings
from trend.store import TrendStore


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def search_urls(name: str) -> List[Dict[str, str]]:
    q = quote(name)
    return [
        {
            "marketplace": "shopee",
            "item_id": "",
            "title": f"Shopee search: {name}",
            "price": "",
            "url": f"https://shopee.vn/search?keyword={q}",
        },
        {
            "marketplace": "lazada",
            "item_id": "",
            "title": f"Lazada search: {name}",
            "price": "",
            "url": f"https://www.lazada.vn/catalog/?q={q}",
        },
    ]


async def _search_shopee(name: str) -> List[Dict[str, str]]:
    url = "https://shopee.vn/api/v4/search/search_items"
    params = {"by": "relevancy", "keyword": name, "limit": 5, "newest": 0, "order": "desc", "page_type": "search"}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://shopee.vn/",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            data = resp.json()
    except Exception:
        return []
    items = []
    for entry in data.get("items") or []:
        item = entry.get("item_basic") or entry.get("item") or {}
        item_id = str(item.get("itemid") or "")
        shop_id = str(item.get("shopid") or "")
        title = item.get("name") or name
        price = item.get("price")
        if isinstance(price, (int, float)) and price > 1000:
            price = f"{price / 100000:.0f}"
        if not item_id:
            continue
        items.append(
            {
                "marketplace": "shopee",
                "item_id": item_id,
                "title": title,
                "price": str(price or ""),
                "url": f"https://shopee.vn/product/{shop_id}/{item_id}",
            }
        )
    return items


async def _search_lazada(name: str) -> List[Dict[str, str]]:
    # Public catalog URL is always returned; JSON search is best-effort.
    url = "https://www.lazada.vn/catalog/"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            await client.get(url, params={"q": name}, headers={"User-Agent": "Mozilla/5.0"})
    except Exception:
        pass
    return []


def write_draft(product_key: str, name: str, listings: List[Dict[str, str]]) -> str:
    folder = _root() / "data" / "trend" / "orders"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{product_key.replace(':', '_')}_{int(time.time())}.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["product_key", "name", "marketplace", "item_id", "title", "price", "url", "qty"])
        writer.writeheader()
        for listing in listings:
            writer.writerow(
                {
                    "product_key": product_key,
                    "name": name,
                    "marketplace": listing.get("marketplace"),
                    "item_id": listing.get("item_id"),
                    "title": listing.get("title"),
                    "price": listing.get("price"),
                    "url": listing.get("url"),
                    "qty": 1,
                }
            )
    return str(path)


async def source_product(product_key: str, name: str, store: TrendStore | None = None) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.get("TREND_MARKETPLACE_ENABLED"):
        return []
    listings: List[Dict[str, str]] = []
    if settings.get("TREND_SHOPEE_ENABLED"):
        listings.extend(await _search_shopee(name))
    if settings.get("TREND_LAZADA_ENABLED"):
        listings.extend(await _search_lazada(name))
    if not listings:
        urls = search_urls(name)
        listings = [u for u in urls if (u["marketplace"] == "shopee" and settings.get("TREND_SHOPEE_ENABLED")) or (u["marketplace"] == "lazada" and settings.get("TREND_LAZADA_ENABLED"))]
        if not listings:
            listings = urls
    draft_path = write_draft(product_key, name, listings) if settings.get("TREND_ORDER_MODE") == "draft" else ""
    rows = [{**item, "product_key": product_key, "draft_path": draft_path} for item in listings]
    store = store or TrendStore()
    await store.save_listings(rows)
    return rows
