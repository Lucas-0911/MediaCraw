# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Grep gates: learning-policy stamps must not return in Python headers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git", "webui"}
SKIP_FILES = {"file_header_manager.py", "test_product_identity.py"}
FORBIDDEN_IN_HEADER = (
    "声明：本代码仅供学习和研究目的使用",
    "NON-COMMERCIAL LEARNING LICENSE 1.1",
    "This file is part of MediaCrawler project",
    "relakkes@gmail.com",
)


def _python_files():
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        yield path


def test_python_headers_are_trend_radar():
    missing = []
    polluted = []
    for path in _python_files():
        header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:30])
        if "This file is part of Trend Radar." not in header:
            missing.append(str(path.relative_to(ROOT)))
        for marker in FORBIDDEN_IN_HEADER:
            if marker in header:
                polluted.append((str(path.relative_to(ROOT)), marker))
    assert not missing, f"missing Trend Radar header: {missing[:20]}"
    assert not polluted, f"learning-policy residue in headers: {polluted[:20]}"


def test_notice_preserves_upstream_credit():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "MediaCrawler" in notice
    assert "relakkes@gmail.com" in notice
