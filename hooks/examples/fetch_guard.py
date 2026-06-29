#!/usr/bin/env python3
"""Opt-in PreToolUse fetch/kernel guard for the SPEDAS Claude plugin.

DISABLED BY DEFAULT. This script only runs if a user copies the hook config from
``hooks/examples/pretooluse-fetch-guard.md`` into ``hooks/hooks.json``. The shipped
``hooks/hooks.json`` is an intentional empty placeholder.
"""
from __future__ import annotations

import json
import sys

# Tools that perform real data downloads (the "opt-in" column in docs/safety.md).
FETCH_TOOLS = {
    "mcp__spedas__fetch_data_product",
    "mcp__spedas__fetch_hapi_data",
    "mcp__spedas__fetch_fdsn_data",
}
# Geometry tools can download SPICE kernels only when allow_kernel_download=True.
GEOMETRY_TOOLS = {
    "mcp__spedas__get_ephemeris",
    "mcp__spedas__compute_distance",
    "mcp__spedas__transform_coordinates",
}


def _read_event() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def main() -> int:
    event = _read_event()
    tool = event.get("tool_name") or event.get("toolName") or ""
    tool_input = event.get("tool_input") or event.get("toolInput") or {}

    if tool in FETCH_TOOLS:
        src = tool_input.get("source_type") or tool_input.get("dataset_id") or "?"
        sys.stderr.write(
            f"[spedas-fetch-guard] About to call {tool} (source/dataset: {src}). "
            "This is a real network download subject to archive rate limits. "
            "Confirm dataset/time-range/cache scope and record opt-in in provenance "
            "before proceeding (see docs/safety.md).\n"
        )
    elif tool in GEOMETRY_TOOLS and tool_input.get("allow_kernel_download") is True:
        target = tool_input.get("target") or tool_input.get("target1") or tool_input.get("spacecraft") or "?"
        sys.stderr.write(
            f"[spedas-fetch-guard] {tool} has allow_kernel_download=True (target: {target}). "
            "This may download SPICE kernels, often 100 MB-1+ GB. Confirm cache dir "
            "and scope before proceeding (see docs/safety.md).\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
