# -*- coding: utf-8 -*-
import math
from datetime import datetime

import pytest

from trend.extract import extract_anchor_product, extract_hashtags, extract_mentions, normalize_name
from trend.ingest import comment_is_intent
from trend.score import heat_now, label_for, select_videos, wilson_lower_bound
from trend.scheduler import _cron_due


def test_normalize_and_hashtags():
    assert "美白精华" in normalize_name("#美白精华 种草")
    tags = extract_hashtags({"desc": "试试 #美白精华 #fyp 开箱"})
    assert any("美白精华" in t for t in tags)
    assert all(t.lower() != "fyp" for t in tags)


def test_anchor_product_id():
    aweme = {
        "anchor_info": {
            "extra": '{"product_id": "P123", "product_name": "美白精华"}'
        }
    }
    found = extract_anchor_product(aweme)
    assert found == ("P123", "美白精华")
    mentions = extract_mentions(aweme, {"desc": "hello"})
    assert mentions[0].identity_type == "xiaohuangche"
    assert mentions[0].product_key == "sku:P123"


def test_wilson_and_heat():
    assert wilson_lower_bound(0, 0) == 0
    bound = wilson_lower_bound(14, 61)
    assert 0.1 < bound < 0.35
    settings = {
        "TREND_WEIGHT_PLAY_VEL": 0.35,
        "TREND_WEIGHT_ENG_VEL": 0.20,
        "TREND_WEIGHT_MENTION": 0.20,
        "TREND_WEIGHT_SPREAD": 0.15,
        "TREND_WEIGHT_INTENT": 0.10,
    }
    metrics = {"play_velocity": 10, "eng_velocity": 2, "mention_n": 8, "spread": 4, "intent_wilson": 0.14}
    peers = [
        {"play_velocity": 1, "eng_velocity": 1, "mention_n": 2, "spread": 1, "intent_wilson": 0.01},
        {"play_velocity": 20, "eng_velocity": 4, "mention_n": 12, "spread": 8, "intent_wilson": 0.2},
    ]
    score = heat_now(metrics, peers, settings)
    assert 0 < score < 1
    assert math.isfinite(score)


def test_label_and_video_filter():
    settings = {
        "TREND_HOT_HEATNOW": 0.7,
        "TREND_RISING_HEATNOW_MIN": 0.4,
        "TREND_RISING_DELTA_RATIO": 0.25,
        "TREND_VIDEO_MIN_AGE_HOURS": 2,
        "TREND_VIDEO_MAX_AGE_DAYS": 10,
        "TREND_REQUIRE_PLAY_INCREASE": True,
        "TREND_VIDEOS_PER_ALERT": 3,
    }
    assert label_for(0.8, 0.5, 10, 5, settings, True) == "DANG HOT"
    assert label_for(0.5, 0.3, 10, 5, settings, True) == "DU KIEN NONG"
    assert label_for(0.5, 0.3, 10, 5, settings, False) == "QUAN SAT"
    now = 1_700_000_000
    videos = [
        {
            "aweme_id": "1",
            "play_count": 80000,
            "last_play_count": 10000,
            "like_count": 100,
            "create_time": now - 5 * 3600,
            "url": "https://www.douyin.com/video/1",
        },
        {
            "aweme_id": "2",
            "play_count": 10,
            "last_play_count": 20,
            "like_count": 1,
            "create_time": now - 5 * 3600,
            "url": "https://www.douyin.com/video/2",
        },
    ]
    picked = select_videos(videos, settings, now)
    assert len(picked) == 1
    assert picked[0]["aweme_id"] == "1"


def test_intent_and_cron():
    assert comment_is_intent("这个多少钱求链接")
    assert comment_is_intent("mua ngay link shop")
    assert not comment_is_intent("好看")
    now = datetime(2026, 9, 16, 18, 0)
    assert _cron_due("0 */6 * * *", now)
    assert not _cron_due("0 */6 * * *", datetime(2026, 9, 16, 18, 1))


def test_settings_roundtrip(tmp_path, monkeypatch):
    settings_file = tmp_path / "trend_settings.json"
    monkeypatch.setenv("TREND_SETTINGS_PATH", str(settings_file))
    from trend.settings import get_settings, update_settings
    update_settings({"TREND_MIN_CONFIDENCE": 3, "TREND_VIDEOS_PER_ALERT": 4})
    loaded = get_settings()
    assert loaded["TREND_MIN_CONFIDENCE"] == 3
    assert loaded["TREND_VIDEOS_PER_ALERT"] == 4


@pytest.mark.asyncio
async def test_ingest_and_score(tmp_path, monkeypatch):
    monkeypatch.setenv("TREND_DB_PATH", str(tmp_path / "trend.sqlite"))
    monkeypatch.setenv("TREND_SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setenv("TREND_GOOGLE_TRENDS_ENABLED", "false")
    monkeypatch.setenv("TREND_LLM_ENABLED", "false")
    from trend.ingest import ingest_aweme, ingest_comment
    from trend.score import score_all
    from trend.store import TrendStore

    now = 1_700_000_000
    for i in range(6):
        aweme = {
            "aweme_id": f"v{i}",
            "desc": "#美白精华 种草测评",
            "create_time": now - 5 * 3600,
            "statistics": {"play_count": 20000 + i, "digg_count": 100, "comment_count": 20, "share_count": 5},
            "author": {"uid": f"u{i}", "nickname": "shop"},
            "anchor_info": {"product_id": "SKU99", "product_name": "美白精华"},
        }
        saved = {
            "aweme_id": f"v{i}",
            "desc": aweme["desc"],
            "create_time": aweme["create_time"],
            "creator_hash": f"hash{i}",
            "liked_count": 100,
            "comment_count": 20,
            "share_count": 5,
            "aweme_url": f"https://www.douyin.com/video/v{i}",
            "source_keyword": "美妆",
        }
        await ingest_aweme("dy", aweme, saved)
        await ingest_comment("dy", f"v{i}", {"cid": f"c{i}", "text": "求链接多少钱", "digg_count": 1})

    result = await score_all(TrendStore(tmp_path / "trend.sqlite"))
    assert result["count"] >= 1
    item = result["scored"][0]
    assert item["product_id"] == "SKU99"
    assert item["metrics"]["mention_n"] == 6


def test_marketplace_urls():
    from trend.marketplace import search_urls
    urls = search_urls("美白精华")
    assert any("shopee.vn" in u["url"] for u in urls)
    assert any("lazada.vn" in u["url"] for u in urls)


def test_telegram_test_endpoint():
    from unittest.mock import AsyncMock, patch
    from fastapi.testclient import TestClient
    from api.main import app

    with patch("trend.alerts.send_telegram", new_callable=AsyncMock, return_value=True) as mocked:
        client = TestClient(app)
        resp = client.post("/api/trend/telegram/test")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mocked.assert_awaited_once()
        assert mocked.await_args.args[0] == "Trend Radar test"

    with patch("trend.alerts.send_telegram", new_callable=AsyncMock, return_value=False):
        client = TestClient(app)
        resp = client.post("/api/trend/telegram/test")
        assert resp.status_code == 200
        assert resp.json() == {"ok": False}
