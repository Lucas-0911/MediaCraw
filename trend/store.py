# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

from contextlib import asynccontextmanager
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite

from trend.settings import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS trend_product (
  product_key TEXT PRIMARY KEY,
  product_id TEXT,
  name TEXT NOT NULL,
  identity_type TEXT,
  industry TEXT,
  confidence INTEGER DEFAULT 0,
  heat_now REAL DEFAULT 0,
  heat_delta REAL DEFAULT 0,
  label TEXT DEFAULT 'QUAN SAT',
  gates_json TEXT DEFAULT '{}',
  last_alert_ts INTEGER DEFAULT 0,
  updated_ts INTEGER
);

CREATE TABLE IF NOT EXISTS trend_video (
  aweme_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  product_key TEXT NOT NULL,
  creator_hash TEXT,
  play_count INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  comment_count INTEGER DEFAULT 0,
  share_count INTEGER DEFAULT 0,
  create_time INTEGER,
  url TEXT,
  download_url TEXT,
  desc TEXT,
  source_keyword TEXT,
  last_play_count INTEGER,
  local_media_path TEXT,
  updated_ts INTEGER,
  PRIMARY KEY (aweme_id, platform, product_key)
);

CREATE TABLE IF NOT EXISTS trend_comment (
  comment_id TEXT PRIMARY KEY,
  aweme_id TEXT,
  platform TEXT,
  content TEXT,
  like_count INTEGER DEFAULT 0,
  is_intent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS trend_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_key TEXT NOT NULL,
  ts INTEGER NOT NULL,
  play_velocity REAL,
  eng_velocity REAL,
  mention_n INTEGER,
  spread INTEGER,
  intent_n INTEGER,
  intent_wilson REAL,
  heat_now REAL,
  search_cn TEXT
);

CREATE TABLE IF NOT EXISTS trend_alert (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_key TEXT,
  ts INTEGER,
  confidence INTEGER,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS trend_listing (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_key TEXT,
  marketplace TEXT,
  item_id TEXT,
  title TEXT,
  price TEXT,
  url TEXT,
  draft_path TEXT,
  ts INTEGER
);

CREATE TABLE IF NOT EXISTS trend_scan_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_ts INTEGER,
  finished_ts INTEGER,
  status TEXT,
  detail_json TEXT
);
"""


class TrendStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else db_path()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        try:
            await db.executescript(SCHEMA)
            await db.commit()
            yield db
        finally:
            await db.close()

    async def upsert_product(
        self,
        product_key: str,
        name: str,
        product_id: Optional[str] = None,
        identity_type: str = "hashtag",
        industry: str = "",
    ) -> None:
        now = int(time.time())
        async with self.connect() as db:
            await db.execute(
                """
                INSERT INTO trend_product (product_key, product_id, name, identity_type, industry, updated_ts)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_key) DO UPDATE SET
                  name=excluded.name,
                  product_id=COALESCE(excluded.product_id, trend_product.product_id),
                  identity_type=CASE
                    WHEN excluded.identity_type = 'xiaohuangche' THEN excluded.identity_type
                    ELSE trend_product.identity_type
                  END,
                  industry=CASE WHEN excluded.industry != '' THEN excluded.industry ELSE trend_product.industry END,
                  updated_ts=excluded.updated_ts
                """,
                (product_key, product_id, name, identity_type, industry, now),
            )
            await db.commit()

    async def upsert_video(self, row: Dict[str, Any]) -> None:
        now = int(time.time())
        async with self.connect() as db:
            existing = await db.execute(
                "SELECT play_count FROM trend_video WHERE aweme_id=? AND platform=? AND product_key=?",
                (row["aweme_id"], row["platform"], row["product_key"]),
            )
            prev = await existing.fetchone()
            last_play = prev["play_count"] if prev else row.get("play_count") or 0
            await db.execute(
                """
                INSERT INTO trend_video (
                  aweme_id, platform, product_key, creator_hash, play_count, like_count,
                  comment_count, share_count, create_time, url, download_url, desc,
                  source_keyword, last_play_count, local_media_path, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(aweme_id, platform, product_key) DO UPDATE SET
                  play_count=excluded.play_count,
                  like_count=excluded.like_count,
                  comment_count=excluded.comment_count,
                  share_count=excluded.share_count,
                  last_play_count=trend_video.play_count,
                  download_url=excluded.download_url,
                  url=excluded.url,
                  updated_ts=excluded.updated_ts
                """,
                (
                    row["aweme_id"],
                    row["platform"],
                    row["product_key"],
                    row.get("creator_hash") or "",
                    int(row.get("play_count") or 0),
                    int(row.get("like_count") or 0),
                    int(row.get("comment_count") or 0),
                    int(row.get("share_count") or 0),
                    int(row.get("create_time") or 0),
                    row.get("url") or "",
                    row.get("download_url") or "",
                    row.get("desc") or "",
                    row.get("source_keyword") or "",
                    int(last_play or 0),
                    row.get("local_media_path") or "",
                    now,
                ),
            )
            await db.commit()

    async def upsert_comment(self, row: Dict[str, Any]) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                INSERT INTO trend_comment (comment_id, aweme_id, platform, content, like_count, is_intent)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(comment_id) DO UPDATE SET
                  content=excluded.content,
                  like_count=excluded.like_count,
                  is_intent=excluded.is_intent
                """,
                (
                    row["comment_id"],
                    row.get("aweme_id") or "",
                    row.get("platform") or "",
                    row.get("content") or "",
                    int(row.get("like_count") or 0),
                    int(row.get("is_intent") or 0),
                ),
            )
            await db.commit()

    async def list_products(self, min_confidence: int = 0) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                """
                SELECT * FROM trend_product
                WHERE confidence >= ?
                ORDER BY heat_now DESC, confidence DESC, updated_ts DESC
                """,
                (min_confidence,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_product(self, product_key: str) -> Optional[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM trend_product WHERE product_key=?",
                (product_key,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def videos_for(self, product_key: str) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM trend_video WHERE product_key=?",
                (product_key,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def comments_for_awemes(self, aweme_ids: List[str]) -> List[Dict[str, Any]]:
        if not aweme_ids:
            return []
        placeholders = ",".join("?" * len(aweme_ids))
        async with self.connect() as db:
            cur = await db.execute(
                f"SELECT * FROM trend_comment WHERE aweme_id IN ({placeholders})",
                aweme_ids,
            )
            return [dict(r) for r in await cur.fetchall()]

    async def snapshots_for(self, product_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM trend_snapshot WHERE product_key=? ORDER BY ts DESC LIMIT ?",
                (product_key, limit),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def save_snapshot(self, row: Dict[str, Any]) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                INSERT INTO trend_snapshot (
                  product_key, ts, play_velocity, eng_velocity, mention_n, spread,
                  intent_n, intent_wilson, heat_now, search_cn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["product_key"],
                    int(row["ts"]),
                    row.get("play_velocity") or 0,
                    row.get("eng_velocity") or 0,
                    row.get("mention_n") or 0,
                    row.get("spread") or 0,
                    row.get("intent_n") or 0,
                    row.get("intent_wilson") or 0,
                    row.get("heat_now") or 0,
                    row.get("search_cn") or "unknown",
                ),
            )
            await db.commit()

    async def update_product_score(self, product_key: str, fields: Dict[str, Any]) -> None:
        fields = dict(fields)
        fields["updated_ts"] = int(time.time())
        if "gates_json" in fields and not isinstance(fields["gates_json"], str):
            fields["gates_json"] = json.dumps(fields["gates_json"], ensure_ascii=False)
        cols = ", ".join(f"{k}=?" for k in fields)
        async with self.connect() as db:
            await db.execute(
                f"UPDATE trend_product SET {cols} WHERE product_key=?",
                (*fields.values(), product_key),
            )
            await db.commit()

    async def save_alert(self, product_key: str, confidence: int, payload: Dict[str, Any]) -> None:
        now = int(time.time())
        async with self.connect() as db:
            await db.execute(
                "INSERT INTO trend_alert (product_key, ts, confidence, payload_json) VALUES (?, ?, ?, ?)",
                (product_key, now, confidence, json.dumps(payload, ensure_ascii=False)),
            )
            await db.execute(
                "UPDATE trend_product SET last_alert_ts=? WHERE product_key=?",
                (now, product_key),
            )
            await db.commit()

    async def list_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM trend_alert ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def save_listings(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        now = int(time.time())
        async with self.connect() as db:
            await db.executemany(
                """
                INSERT INTO trend_listing (product_key, marketplace, item_id, title, price, url, draft_path, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r["product_key"],
                        r.get("marketplace") or "",
                        r.get("item_id") or "",
                        r.get("title") or "",
                        str(r.get("price") or ""),
                        r.get("url") or "",
                        r.get("draft_path") or "",
                        now,
                    )
                    for r in rows
                ],
            )
            await db.commit()

    async def listings_for(self, product_key: str) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM trend_listing WHERE product_key=? ORDER BY ts DESC LIMIT 40",
                (product_key,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def set_media_path(self, aweme_id: str, platform: str, path: str) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE trend_video SET local_media_path=? WHERE aweme_id=? AND platform=?",
                (path, aweme_id, platform),
            )
            await db.commit()

    async def save_scan_run(self, status: str, detail: Dict[str, Any], started_ts: int) -> None:
        async with self.connect() as db:
            await db.execute(
                "INSERT INTO trend_scan_run (started_ts, finished_ts, status, detail_json) VALUES (?, ?, ?, ?)",
                (started_ts, int(time.time()), status, json.dumps(detail, ensure_ascii=False)),
            )
            await db.commit()
