#!/usr/bin/env python3
"""Default PreToolUse fetch/kernel safety gate for the SPEDAS Claude plugin.

The hook is intentionally small, dependency-free, and side-effect-free: it reads
Claude Code's hook event JSON from stdin and, for calls that can download archive
data or large SPICE kernels, asks Claude Code to request explicit user permission
before the MCP tool proceeds. Metadata/planning tools and geometry calls that do
not opt into kernel downloads remain quiet.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

FETCH_TOOLS = {
    # Current data-download tools exposed by the pinned SPEDAS MCP server.
    "mcp__spedas__fetch_data_product",
    "mcp__spedas__fetch_hapi_data",
    "mcp__spedas__fetch_fdsn_data",
    # Legacy/source-specific names kept in the matcher so older MCP pins and
    # copied configs stay protected.
    "mcp__spedas__fetch_data",
    "mcp__spedas__fetch_pds_data",
}
SPICE_MUTATION_TOOLS = {
    "mcp__spedas__manage_spice_kernels",
}
GEOMETRY_TOOLS = {
    "mcp__spedas__get_ephemeris",
    "mcp__spedas__compute_distance",
    "mcp__spedas__transform_coordinates",
}
SAFE_SPICE_ACTIONS = {"status", "list", "show", "check", "info"}
WIDE_RANGE_DAYS = 7.0


def _read_event() -> dict[str, Any]:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Treat plausible Unix timestamps as UTC. Reject tiny mission-relative
        # numbers because hook input schemas for those are not standardized.
        if value > 10_000_000:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Common SPEDAS/user forms: YYYY-MM-DD, ISO date-time, and space-separated
    # UTC date-times. Keep this conservative; failure only suppresses the range
    # length hint, never the safety gate itself.
    for candidate in (text, text.replace(" ", "T", 1)):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _time_values(tool_input: dict[str, Any]) -> tuple[Any, Any]:
    for key in ("trange", "time_range", "time_range_utc", "timerange"):
        value = tool_input.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return value[0], value[1]
        if isinstance(value, str) and "/" in value:
            left, right = value.split("/", 1)
            return left, right
    start = (
        tool_input.get("start_time")
        or tool_input.get("start")
        or tool_input.get("time_start")
        or tool_input.get("begin_time")
    )
    end = (
        tool_input.get("end_time")
        or tool_input.get("end")
        or tool_input.get("time_end")
        or tool_input.get("stop_time")
    )
    return start, end


def _range_hint(tool_input: dict[str, Any]) -> str:
    start_raw, end_raw = _time_values(tool_input)
    start = _parse_time(start_raw)
    end = _parse_time(end_raw)
    if not (start and end):
        if start_raw or end_raw:
            return f" Time range seen: {start_raw or '?'} to {end_raw or '?'}; keep it narrow."
        return " Time range not obvious in hook input; verify it is narrow before approving."
    days = abs((end - start).total_seconds()) / 86_400.0
    if days > WIDE_RANGE_DAYS:
        return (
            f" Wide time range detected (~{days:.1f} days from {start_raw} to {end_raw}); "
            "prefer metadata/browse first or split into narrower windows."
        )
    return f" Time range is ~{days:.1f} days ({start_raw} to {end_raw}); still confirm cache/output/provenance."


def _dataset_hint(tool_input: dict[str, Any]) -> str:
    for key in ("dataset_id", "dataset", "source_type", "mission", "instrument", "product"):
        value = tool_input.get(key)
        if value:
            return f" Dataset/source: {value}."
    return " Dataset/source not obvious; confirm the exact archive product before approving."


def _target_hint(tool_input: dict[str, Any]) -> str:
    for key in ("target", "target1", "target2", "spacecraft", "observer", "body"):
        value = tool_input.get(key)
        if value:
            return f" Target/body: {value}."
    return " Target/body not obvious; confirm the exact SPICE scope before approving."


def _is_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes", "y", "on"}:
        return True
    return False


def _ask(reason: str) -> int:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return 0


def _fetch_reason(tool: str, tool_input: dict[str, Any]) -> str:
    preference = ""
    if tool in {"mcp__spedas__fetch_hapi_data", "mcp__spedas__fetch_fdsn_data", "mcp__spedas__fetch_data", "mcp__spedas__fetch_pds_data"}:
        preference = " Prefer the unified fetch_data_product workflow unless this source-specific call is necessary."
    return (
        f"SPEDAS safety gate: {tool} performs a real archive/network download."
        " Approve only after explicit user confirmation of the science question, dataset, UTC time range, cache/output location, and provenance plan. If metadata/browse/planning has not already happened, do that first."
        f"{_dataset_hint(tool_input)}{_range_hint(tool_input)}{preference}"
    )


def _spice_reason(tool: str, tool_input: dict[str, Any]) -> str:
    return (
        f"SPEDAS safety gate: {tool} may download or mutate SPICE kernel cache state."
        " SPICE kernels can be 100 MB-1+ GB. Approve only after explicit user confirmation of target/body, time span, kernel/cache directory, and provenance plan. If cache status/planning has not already happened, do that first."
        f"{_target_hint(tool_input)}{_range_hint(tool_input)}"
    )


def main() -> int:
    event = _read_event()
    tool = event.get("tool_name") or event.get("toolName") or ""
    raw_input = event.get("tool_input") or event.get("toolInput") or {}
    tool_input = raw_input if isinstance(raw_input, dict) else {}

    if tool in FETCH_TOOLS:
        return _ask(_fetch_reason(tool, tool_input))

    if tool in SPICE_MUTATION_TOOLS:
        action = str(tool_input.get("action") or "").strip().lower()
        if action in SAFE_SPICE_ACTIONS:
            return 0
        return _ask(_spice_reason(tool, tool_input))

    if tool in GEOMETRY_TOOLS and _is_true(tool_input.get("allow_kernel_download")):
        return _ask(_spice_reason(tool, tool_input))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
