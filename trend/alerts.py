# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

import httpx

from trend.settings import get_settings
from trend.store import TrendStore


def format_alert(item: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> str:
    settings = settings or get_settings()
    gates = item.get("gates") or {}
    metrics = item.get("metrics") or {}
    label = item.get("label") or "QUAN SAT"
    conf = item.get("confidence") or 0
    identity = "小黄车" if item.get("product_id") or item.get("identity_type") == "xiaohuangche" else "name"
    heat = float(item.get("heat_now") or 0)
    delta = float(item.get("heat_delta") or 0)
    w = (
        settings.get("TREND_WEIGHT_PLAY_VEL"),
        settings.get("TREND_WEIGHT_ENG_VEL"),
        settings.get("TREND_WEIGHT_MENTION"),
        settings.get("TREND_WEIGHT_SPREAD"),
        settings.get("TREND_WEIGHT_INTENT"),
    )
    lines = [
        f"[{label}] Confidence {conf}/5  identity={identity}",
        str(item.get("name") or item.get("product_key")),
        f"HeatNow {heat:.2f}  Δ{delta:+.2f}",
        "",
        "Cổng: "
        + " | ".join(
            [
                f"mention+spread {'OK' if gates.get('mention_spread') else 'NO'}",
                f"play còn tăng {'OK' if gates.get('play_increase') else 'NO'}",
                f"intent {'OK' if gates.get('intent') else 'NO'}",
                f"trends_CN {gates.get('search_cn_value') or 'unknown'}",
                f"{'có product_id' if item.get('product_id') else 'không product_id'}",
            ]
        ),
        f"HeatNow = {w[0]} play_vel + {w[1]} eng_vel + {w[2]} mention + {w[3]} spread + {w[4]} intent_wilson",
        f"- play_velocity {metrics.get('play_velocity', 0):.1f}/h",
        f"- mention {metrics.get('mention_n', 0)} · spread {metrics.get('spread', 0)}",
        f"- intent {metrics.get('intent_n', 0)}/{metrics.get('comment_n', 0)} · Wilson {metrics.get('intent_wilson', 0):.2f}",
        "",
        "Video:",
    ]
    for idx, video in enumerate(item.get("videos") or [], start=1):
        lines.append(
            f"{idx}. play {video.get('play_count', 0)} · like {video.get('like_count', 0)} · "
            f"{video.get('age_hours', 0)}h · {video.get('url') or ''}"
        )
    listings = item.get("listings") or []
    if listings:
        lines.append("")
        lines.append("Shopee/Lazada draft:")
        for listing in listings[:5]:
            lines.append(
                f"- {listing.get('marketplace')} {listing.get('price') or ''} {listing.get('url')}"
            )
    return "\n".join(lines)


async def send_telegram(text: str, settings: Optional[Dict[str, Any]] = None) -> bool:
    settings = settings or get_settings()
    token = settings.get("TREND_TELEGRAM_BOT_TOKEN") or ""
    chat_id = settings.get("TREND_TELEGRAM_CHAT_ID") or ""
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                json={"chat_id": chat_id, "text": text[:3900], "disable_web_page_preview": False},
            )
            return resp.status_code == 200
    except Exception:
        return False


async def maybe_alert(item: Dict[str, Any], store: Optional[TrendStore] = None) -> bool:
    settings = get_settings()
    store = store or TrendStore()
    if not item.get("snapshots_ready"):
        return False
    if int(item.get("confidence") or 0) < int(settings["TREND_MIN_CONFIDENCE"]):
        return False
    product = await store.get_product(item["product_key"])
    last_alert = int((product or {}).get("last_alert_ts") or 0)
    cooldown = float(settings["TREND_ALERT_COOLDOWN_HOURS"]) * 3600
    import time

    if last_alert and (int(time.time()) - last_alert) < cooldown:
        return False
    text = format_alert(item, settings)
    sent = await send_telegram(text, settings)
    await store.save_alert(item["product_key"], int(item.get("confidence") or 0), {"text": text, "sent": sent, "item": item})
    return sent
