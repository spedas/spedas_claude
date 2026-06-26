#!/usr/bin/env python3
"""Opt-in PreToolUse fetch/kernel guard for the SPEDAS Claude plugin.

DISABLED BY DEFAULT. This script only runs if a user copies the hook config from
``hooks/examples/pretooluse-fetch-guard.md`` into ``hooks/hooks.json``. The shipped
``hooks/hooks.json`` is an intentional empty placeholder.

Behavior (deliberately minimal and non-destructive):

- Reads the Claude Code PreToolUse hook JSON from stdin.
- Emits ONE advisory reminder line to stderr for the matched fetch/kernel tool.
- Exits 0 (non-blocking). It does NO network access and writes NO files.

It never mutates user state. To turn this into a blocking gate, change the exit
behavior per the Claude Code hook documentation — but advisory is the safer default.
"""
from __future__ import annotations

import json
import sys

# Tools that perform real network downloads (the "opt-in" column in docs/safety.md).
FETCH_TOOLS = {
    "mcp__spedas__fetch_data_product",
    "mcp__spedas__fetch_data",
    "mcp__spedas__fetch_pds_data",
}
KERNEL_TOOL = "mcp__spedas__manage_spice_kernels"


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
    elif tool == KERNEL_TOOL:
        action = tool_input.get("action", "?")
        if action == "status":
            # Status is safe/metadata-only; just a light note.
            sys.stderr.write(
                "[spedas-fetch-guard] manage_spice_kernels(action=status) is metadata-only "
                "(no download).\n"
            )
        else:
            sys.stderr.write(
                f"[spedas-fetch-guard] manage_spice_kernels(action={action}) may download "
                "SPICE kernels (often 100 MB-1+ GB). Confirm cache dir and scope before "
                "proceeding (see docs/safety.md).\n"
            )

    # Non-blocking: allow the tool call to proceed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
