# -*- coding: utf-8 -*-
# Copyright (c) 2026 Trend Radar product owner.
#
# This file is part of Trend Radar.
# See LICENSE. Upstream origin: NOTICE.

"""CLI alias. The crawler subprocess contract remains `uv run python main.py`."""

if __name__ == "__main__":
    import runpy

    runpy.run_module("main", run_name="__main__")
