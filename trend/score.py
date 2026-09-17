# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

import math
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

from trend.google_trends import fetch_search_cn
from trend.settings import get_settings
from trend.store import TrendStore


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = p + z2 / (2 * n)
    adj = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    return max(0.0, (centre - adj) / denom)


def _age_hours(create_time: int, now: Optional[int] = None) -> float:
    now = now or int(time.time())
    created = int(create_time or 0)
    if created > 10_000_000_000:
        created = created // 1000
    return max((now - created) / 3600.0, 1.0)


def _minmax(values: List[float], value: float) -> float:
    if not values:
        return 0.0
    lo, hi = min(values), max(values)
    if hi <= lo:
        return 0.0 if value <= lo else 1.0
    return (value - lo) / (hi - lo)


def _median_play_velocity(videos: List[Dict[str, Any]], now: int) -> float:
    vels = []
    for video in videos:
        play = float(video.get("play_count") or 0)
        vels.append(play / _age_hours(int(video.get("create_time") or 0), now))
    return statistics.median(vels) if vels else 0.0


def select_videos(videos: List[Dict[str, Any]], settings: Dict[str, Any], now: Optional[int] = None) -> List[Dict[str, Any]]:
    now = now or int(time.time())
    min_age = float(settings.get("TREND_VIDEO_MIN_AGE_HOURS") or 2)
    max_age_hours = float(settings.get("TREND_VIDEO_MAX_AGE_DAYS") or 10) * 24
    require_increase = bool(settings.get("TREND_REQUIRE_PLAY_INCREASE"))
    limit = int(settings.get("TREND_VIDEOS_PER_ALERT") or 5)
    picked = []
    for video in videos:
        age = _age_hours(int(video.get("create_time") or 0), now)
        if age < min_age or age > max_age_hours:
            continue
        play = int(video.get("play_count") or 0)
        if play <= 0:
            continue
        last_play = int(video.get("last_play_count") or play)
        if require_increase and play < last_play:
            continue
        velocity = play / age
        item = dict(video)
        item["age_hours"] = round(age, 2)
        item["play_velocity"] = velocity
        picked.append(item)
    picked.sort(key=lambda x: x.get("play_velocity") or 0, reverse=True)
    return picked[:limit]


def compute_raw_metrics(videos: List[Dict[str, Any]], comments: List[Dict[str, Any]], now: Optional[int] = None) -> Dict[str, Any]:
    now = now or int(time.time())
    mention_n = len({(v.get("platform"), v.get("aweme_id")) for v in videos})
    spread = len({v.get("creator_hash") for v in videos if v.get("creator_hash")})
    play_vels = []
    eng_vels = []
    for video in videos:
        age = _age_hours(int(video.get("create_time") or 0), now)
        play = float(video.get("play_count") or 0)
        eng = float(video.get("like_count") or 0) + float(video.get("comment_count") or 0) + float(video.get("share_count") or 0)
        play_vels.append(play / age)
        eng_vels.append(eng / age)
    aweme_ids = {str(v.get("aweme_id")) for v in videos}
    related = [c for c in comments if str(c.get("aweme_id")) in aweme_ids]
    intent_n = sum(int(c.get("is_intent") or 0) for c in related)
    comment_n = len(related)
    return {
        "play_velocity": statistics.median(play_vels) if play_vels else 0.0,
        "eng_velocity": statistics.median(eng_vels) if eng_vels else 0.0,
        "mention_n": mention_n,
        "spread": spread,
        "intent_n": intent_n,
        "comment_n": comment_n,
        "intent_wilson": wilson_lower_bound(intent_n, max(comment_n, 1)),
    }


def heat_now(metrics: Dict[str, Any], peers: List[Dict[str, Any]], settings: Dict[str, Any]) -> float:
    def col(key: str) -> List[float]:
        return [float(p.get(key) or 0) for p in peers] + [float(metrics.get(key) or 0)]

    return (
        float(settings["TREND_WEIGHT_PLAY_VEL"]) * _minmax(col("play_velocity"), metrics["play_velocity"])
        + float(settings["TREND_WEIGHT_ENG_VEL"]) * _minmax(col("eng_velocity"), metrics["eng_velocity"])
        + float(settings["TREND_WEIGHT_MENTION"]) * _minmax(col("mention_n"), metrics["mention_n"])
        + float(settings["TREND_WEIGHT_SPREAD"]) * _minmax(col("spread"), metrics["spread"])
        + float(settings["TREND_WEIGHT_INTENT"]) * float(metrics.get("intent_wilson") or 0)
    )


def evaluate_gates(
    product: Dict[str, Any],
    metrics: Dict[str, Any],
    prev: Optional[Dict[str, Any]],
    search_cn: str,
    settings: Dict[str, Any],
    videos: List[Dict[str, Any]],
    now: int,
) -> Tuple[Dict[str, Any], int, str]:
    mention_ok = metrics["mention_n"] >= int(settings["TREND_MIN_MENTION"]) and metrics["spread"] >= int(settings["TREND_MIN_SPREAD"])
    play_up = False
    if prev:
        play_up = metrics["play_velocity"] > float(prev.get("play_velocity") or 0)
    else:
        # still compute median vs last_play proxy
        current = _median_play_velocity(videos, now)
        older = []
        for video in videos:
            last = float(video.get("last_play_count") or 0)
            age = _age_hours(int(video.get("create_time") or 0), now)
            older.append(last / age)
        play_up = current > (statistics.median(older) if older else 0)
    intent_ok = metrics["intent_n"] >= int(settings["TREND_MIN_INTENT_N"]) and metrics["intent_wilson"] >= float(settings["TREND_MIN_INTENT_WILSON"])
    trends_ok = search_cn != "falling"
    identity_ok = bool(product.get("product_id")) or metrics["mention_n"] >= int(settings["TREND_MIN_NAME_VIDEOS"])
    gates = {
        "mention_spread": mention_ok,
        "play_increase": play_up,
        "intent": intent_ok,
        "search_cn": trends_ok,
        "identity": identity_ok,
        "search_cn_value": search_cn,
        "two_snapshots": bool(prev),
    }
    confidence = 0
    if product.get("product_id") or product.get("identity_type") == "xiaohuangche":
        confidence += 1
    if mention_ok:
        confidence += 1
    if play_up:
        confidence += 1
    if intent_ok:
        confidence += 1
    if search_cn == "rising":
        confidence += 1
    return gates, confidence, search_cn


def label_for(heat: float, prev_heat: Optional[float], mention_n: int, prev_mention: Optional[int], settings: Dict[str, Any], snapshots_ready: bool) -> str:
    if not snapshots_ready:
        return "QUAN SAT"
    hot = float(settings["TREND_HOT_HEATNOW"])
    rising_min = float(settings["TREND_RISING_HEATNOW_MIN"])
    ratio = float(settings["TREND_RISING_DELTA_RATIO"])
    if heat >= hot:
        return "DANG HOT"
    delta = 0.0 if prev_heat is None else heat - prev_heat
    grew = prev_mention is not None and mention_n > prev_mention
    if rising_min <= heat < hot and grew and (delta / max(prev_heat or 0.05, 0.05)) >= ratio:
        return "DU KIEN NONG"
    return "QUAN SAT"


async def score_all(store: Optional[TrendStore] = None) -> Dict[str, Any]:
    settings = get_settings()
    store = store or TrendStore()
    products = await store.list_products(min_confidence=0)
    now = int(time.time())
    gap = float(settings["TREND_SNAPSHOT_GAP_HOURS"]) * 3600
    industry_metrics: Dict[str, List[Dict[str, Any]]] = {}
    computed: List[Dict[str, Any]] = []

    for product in products:
        videos = await store.videos_for(product["product_key"])
        comments = await store.comments_for_awemes([str(v.get("aweme_id")) for v in videos])
        metrics = compute_raw_metrics(videos, comments, now)
        snapshots = await store.snapshots_for(product["product_key"], limit=5)
        prev = None
        if snapshots:
            latest = snapshots[0]
            if now - int(latest.get("ts") or 0) >= gap:
                prev = latest
            elif len(snapshots) > 1:
                prev = snapshots[1]
        search_cn = "unknown"
        if settings.get("TREND_GOOGLE_TRENDS_ENABLED"):
            search_cn = await fetch_search_cn(product.get("name") or "")
        gates, confidence, search_cn = evaluate_gates(product, metrics, prev, search_cn, settings, videos, now)
        row = {
            "product": product,
            "metrics": metrics,
            "prev": prev,
            "gates": gates,
            "confidence": confidence,
            "search_cn": search_cn,
            "videos": videos,
            "snapshots_ready": bool(prev),
        }
        computed.append(row)
        industry = product.get("industry") or "_"
        industry_metrics.setdefault(industry, []).append(metrics)

    scored = []
    for row in computed:
        product = row["product"]
        industry = product.get("industry") or "_"
        heat = heat_now(row["metrics"], industry_metrics.get(industry, []), settings)
        prev_heat = float(row["prev"]["heat_now"]) if row["prev"] else None
        prev_mention = int(row["prev"]["mention_n"]) if row["prev"] else None
        heat_delta = 0.0 if prev_heat is None else heat - prev_heat
        label = label_for(
            heat,
            prev_heat,
            row["metrics"]["mention_n"],
            prev_mention,
            settings,
            row["snapshots_ready"],
        )
        await store.save_snapshot(
            {
                "product_key": product["product_key"],
                "ts": now,
                "play_velocity": row["metrics"]["play_velocity"],
                "eng_velocity": row["metrics"]["eng_velocity"],
                "mention_n": row["metrics"]["mention_n"],
                "spread": row["metrics"]["spread"],
                "intent_n": row["metrics"]["intent_n"],
                "intent_wilson": row["metrics"]["intent_wilson"],
                "heat_now": heat,
                "search_cn": row["search_cn"],
            }
        )
        await store.update_product_score(
            product["product_key"],
            {
                "confidence": row["confidence"],
                "heat_now": heat,
                "heat_delta": heat_delta,
                "label": label,
                "gates_json": row["gates"],
            },
        )
        picked = select_videos(row["videos"], settings, now)
        scored.append(
            {
                "product_key": product["product_key"],
                "name": product.get("name"),
                "product_id": product.get("product_id"),
                "identity_type": product.get("identity_type"),
                "confidence": row["confidence"],
                "heat_now": heat,
                "heat_delta": heat_delta,
                "label": label,
                "gates": row["gates"],
                "metrics": row["metrics"],
                "videos": picked,
                "snapshots_ready": row["snapshots_ready"],
                "search_cn": row["search_cn"],
            }
        )
    return {"scored": scored, "count": len(scored), "ts": now}
