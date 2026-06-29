#!/usr/bin/env python3
"""Compatibility wrapper for the default SPEDAS fetch/kernel guard.

Older local copies of the plugin documentation pointed to this example path. The
real, enabled-by-default implementation now lives at ``hooks/fetch_guard.py``;
this wrapper delegates there so copied configs do not silently lose the stronger
issue #6 behavior.
"""
from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[1] / "fetch_guard.py"), run_name="__main__")
