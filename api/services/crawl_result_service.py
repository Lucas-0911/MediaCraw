# -*- coding: utf-8 -*-
"""Read-only application service for persisted file-based crawler results."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


class CrawlResultService:
    """Searches existing crawl files only; it never starts a crawler or opens a DB."""

    _SUPPORTED_EXTENSIONS = {".json", ".jsonl", ".csv"}

    def __init__(self, data_root: Path | str | None = None) -> None:
        self._data_root = Path(data_root) if data_root else Path(__file__).resolve().parents[2] / "data"

    async def search(self, platform: str, keyword: str, limit: int) -> list[dict[str, Any]]:
        platform_dir = self._data_root / platform
        if not platform_dir.is_dir():
            return []
        needle = keyword.casefold().strip()
        matches: list[dict[str, Any]] = []
        for path in sorted(platform_dir.rglob("*"), reverse=True):
            if path.suffix.lower() not in self._SUPPORTED_EXTENSIONS or not path.is_file():
                continue
            if not self._is_within_root(path):
                continue
            for record in self._read_records(path):
                if needle and needle not in self._searchable_text(record).casefold():
                    continue
                matches.append(self._normalize_record(platform, path, record))
                if len(matches) >= limit:
                    return matches
        return matches

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._data_root.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _read_records(path: Path) -> Iterable[dict[str, Any]]:
        try:
            if path.suffix.lower() == ".json":
                loaded = json.loads(path.read_text(encoding="utf-8"))
                rows = loaded if isinstance(loaded, list) else [loaded]
                return (row for row in rows if isinstance(row, dict))
            if path.suffix.lower() == ".jsonl":
                return (
                    row
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                    for row in [json.loads(line)]
                    if isinstance(row, dict)
                )
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
            return ()

    @staticmethod
    def _searchable_text(record: dict[str, Any]) -> str:
        return " ".join(
            str(record.get(field) or "")
            for field in ("title", "desc", "content", "source_keyword", "keywords")
        )

    def _normalize_record(self, platform: str, path: Path, record: dict[str, Any]) -> dict[str, Any]:
        record_id = record.get("aweme_id") or record.get("note_id") or record.get("video_id") or ""
        return {
            "platform": platform,
            "record_id": str(record_id),
            "title": str(record.get("title") or ""),
            "content": str(record.get("desc") or record.get("content") or ""),
            "url": str(record.get("aweme_url") or record.get("note_url") or record.get("video_url") or ""),
            "created_at": record.get("create_time") or record.get("time") or record.get("publish_time"),
            "source_keyword": str(record.get("source_keyword") or ""),
            "source_file": str(path.relative_to(self._data_root)),
        }
