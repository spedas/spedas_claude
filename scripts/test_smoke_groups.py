#!/usr/bin/env python3
"""Network-free tests for the runtime smoke's tool-group check (issue #8).

These do NOT start the MCP server. They import the pure ``_check_groups`` helper
from ``smoke_mcp_runtime`` and assert that the geometry/SPICE and
unified-vs-backend tool groups are evaluated correctly, so CI catches a backend
that drops a whole group (e.g. all SPICE tools) even if the total tool count
still looks plausible. Run with plain ``python scripts/test_smoke_groups.py`` —
no pytest, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import smoke_mcp_runtime as smoke  # noqa: E402


def _all_tools() -> list[str]:
    tools: list[str] = []
    for members in smoke.TOOL_GROUPS.values():
        tools.extend(members)
    return tools


def test_all_groups_present() -> None:
    report = smoke._check_groups(_all_tools())
    assert set(report) == set(smoke.TOOL_GROUPS), "report must cover every group"
    for name, info in report.items():
        assert info["ok"], f"group {name} should be ok when all tools present: {info}"
        assert info["missing"] == [], f"group {name} should have no missing tools"
    print("PASS: all groups present -> every group ok")


def test_missing_geometry_group_detected() -> None:
    # Drop the whole geometry/SPICE family; everything else stays.
    tools = [t for t in _all_tools() if t not in smoke.TOOL_GROUPS["geometry_spice"]]
    report = smoke._check_groups(tools)
    assert not report["geometry_spice"]["ok"], "missing SPICE tools must flag the group"
    assert set(report["geometry_spice"]["missing"]) == set(smoke.TOOL_GROUPS["geometry_spice"])
    assert report["unified_data"]["ok"], "unrelated groups must remain ok"
    print("PASS: dropped geometry_spice group is detected")


def test_partial_backend_group_detected() -> None:
    # Remove a single backend tool -> that group must report it missing.
    dropped = smoke.TOOL_GROUPS["backend_cdaweb"][0]
    tools = [t for t in _all_tools() if t != dropped]
    report = smoke._check_groups(tools)
    assert not report["backend_cdaweb"]["ok"], "a missing backend tool must flag its group"
    assert report["backend_cdaweb"]["missing"] == [dropped]
    print(f"PASS: partially-missing backend_cdaweb detected (dropped {dropped!r})")


def test_core_tools_are_subset_of_groups() -> None:
    # The legacy EXPECTED_CORE_TOOLS must all live in the workflow/unified groups,
    # so the two checks stay consistent.
    grouped = set(_all_tools())
    for name in smoke.EXPECTED_CORE_TOOLS:
        assert name in grouped, f"core tool {name!r} missing from TOOL_GROUPS"
    print("PASS: EXPECTED_CORE_TOOLS are all covered by TOOL_GROUPS")


def main() -> int:
    test_all_groups_present()
    test_missing_geometry_group_detected()
    test_partial_backend_group_detected()
    test_core_tools_are_subset_of_groups()
    print("\nAll smoke group tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
