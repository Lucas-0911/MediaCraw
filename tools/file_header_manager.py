# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""Ensure Python files carry the Trend Radar header, not the upstream learning-policy stamp."""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Tuple

_HEADER_LINES = (
    "# Copyright (c) 2026 Trend Radar product owner.",
    "#",
    "# This file is part of Trend Radar.",
    "# See LICENSE. Upstream origin: NOTICE.",
)
HEADER_BODY = "\n".join(_HEADER_LINES) + "\n"

_NEW_HEADER_RE = re.compile(
    r"# Copyright \(c\) 2026 Trend Radar product owner\.\n"
    r"#\n"
    r"# This file is part of Trend Radar\.\n"
    r"# See LICENSE\. Upstream origin: NOTICE\.\n(?:\n)?"
)

_OLD_BLOCK_RE = re.compile(
    r"# Copyright \(c\) 202[0-9] relakkes@gmail\.com\n"
    r"(?:#.*\n)*?"
    r"(?:# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。\n|# Licensed under NON-COMMERCIAL LEARNING LICENSE 1\.1\n)",
)

_OLD_COPYRIGHT_RE = re.compile(
    r"# Copyright \(c\) 202[0-9] relakkes@gmail\.com\n"
    r"(?:#\n)?"
    r"(?:# This file is part of MediaCrawler project\.\n)"
    r"(?:# Repository: .*\n)?"
    r"(?:# GitHub: .*\n)?"
    r"(?:# Licensed under NON-COMMERCIAL LEARNING LICENSE 1\.1\n)?"
    r"(?:#\n)*"
)

_DISCLAIMER_RE = re.compile(
    r"(?:#\n)*"
    r"# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：\n"
    r"(?:# \d+\. .*\n)+"
    r"(?:#\n)?"
    r"# 详细许可条款请参阅项目根目录下的LICENSE文件。\n"
    r"# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。\n"
)

_AUTHOR_RE = re.compile(r"# @Author\s*:.*relakkes.*\n(?:# @Name\s*:.*\n)?")

_DUPLICATE_ENCODING_RE = re.compile(r"(# -\*- coding: utf-8 -\*-\n)(?:\n)*(# -\*- coding: utf-8 -\*-\n)+")

OLD_POLICY_MARKERS = (
    "声明：本代码仅供学习和研究目的使用",
    "NON-COMMERCIAL LEARNING LICENSE 1.1",
    "This file is part of MediaCrawler project",
    "relakkes@gmail.com",
)


def header_region(content: str) -> str:
    return "\n".join(content.splitlines()[:30])


def has_new_header(content: str) -> bool:
    return bool(_NEW_HEADER_RE.search(header_region(content)))


def has_old_policy(content: str) -> bool:
    return any(marker in header_region(content) for marker in OLD_POLICY_MARKERS)


def strip_legacy(content: str) -> str:
    lines = content.splitlines(keepends=True)
    head = "".join(lines[:50])
    tail = "".join(lines[50:])
    head = _NEW_HEADER_RE.sub("", head)
    head = _OLD_BLOCK_RE.sub("", head)
    head = _OLD_COPYRIGHT_RE.sub("", head)
    head = _DISCLAIMER_RE.sub("", head)
    head = _AUTHOR_RE.sub("", head)
    head = _DUPLICATE_ENCODING_RE.sub(r"\1", head)
    head = re.sub(r"(# -\*- coding: utf-8 -\*-\n)(?:\n|#\n)+", r"\1", head, count=1)
    return head + tail


def apply_header(content: str) -> str:
    if has_new_header(content) and not has_old_policy(content):
        return content
    content = strip_legacy(content)
    lines = content.splitlines(keepends=True)
    insert_pos = 0
    has_encoding = False
    if lines and lines[0].startswith("#!"):
        insert_pos = 1
    for i in range(insert_pos, min(insert_pos + 2, len(lines))):
        if re.match(r"#.*coding[:=]\s*([-\w.]+)", lines[i].strip()):
            has_encoding = True
            insert_pos = i + 1
            break

    prefix: List[str] = []
    if not has_encoding:
        prefix.append("# -*- coding: utf-8 -*-\n")
    prefix.extend(lines[:insert_pos])
    prefix.append(HEADER_BODY)
    rest = lines[insert_pos:]
    while rest and rest[0].strip() == "":
        rest.pop(0)
    prefix.append("\n")
    return "".join(prefix + rest)


def process_file(file_path: str, dry_run: bool = False) -> Tuple[bool, str]:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            original = handle.read()
        updated = apply_header(original)
        if updated == original:
            return False, f"✓ Already has Trend Radar header: {file_path}"
        if dry_run:
            return True, f"→ Would update: {file_path}"
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
        return True, f"✓ Updated: {file_path}"
    except Exception as exc:
        return False, f"✗ Error processing {file_path}: {exc}"


def find_python_files(root_dir: str) -> List[str]:
    exclude = {"venv", ".venv", "node_modules", "__pycache__", ".git", "build", "dist", ".eggs"}
    files: List[str] = []
    for root, dirs, names in os.walk(root_dir):
        dirs[:] = [name for name in dirs if name not in exclude and not name.startswith(".")]
        for name in names:
            if name.endswith(".py") and name != "file_header_manager.py":
                files.append(os.path.join(root, name))
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trend Radar Python file header manager")
    parser.add_argument("files", nargs="*", help="Python files (default: all project .py files)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root) if args.project_root else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    files_to_process = (
        [os.path.abspath(path) for path in args.files if path.endswith(".py")]
        if args.files
        else find_python_files(project_root)
    )

    updated = skipped = errors = 0
    for path in files_to_process:
        changed, message = process_file(path, args.dry_run or args.check)
        print(message)
        if message.startswith("✗"):
            errors += 1
        elif changed:
            updated += 1
        else:
            skipped += 1

    print(f"Updated/Need update: {updated}; compliant: {skipped}; errors: {errors}")
    if args.check and updated > 0:
        sys.exit(1)
    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
