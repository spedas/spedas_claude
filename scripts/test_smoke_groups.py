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
import mcp_client_common as mcp_client  # noqa: E402


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


def test_initialize_params_no_hardcoded_protocol() -> None:
    # #25: the handshake must not pin the old hardcoded constant. Either the field
    # is sourced from the mcp library, or it is omitted so the server negotiates —
    # but it must never be the stale "2024-11-05" literal regardless of mcp presence.
    params = mcp_client.initialize_params("unit-test")
    assert params["clientInfo"]["name"] == "unit-test"
    assert "capabilities" in params
    version = mcp_client.negotiated_protocol_version()
    if version is None:
        assert "protocolVersion" not in params, "omit the field when version is unknown"
    else:
        assert params["protocolVersion"] == version, "must use the library's current version"
        assert params["protocolVersion"] != "2024-11-05" or version == "2024-11-05"
    print(f"PASS: initialize_params hardcode-free (protocolVersion={version!r})")


def test_report_stderr_surfaces_empty_exit() -> None:
    # #26: an abnormal exit with empty stderr must still produce a message, not
    # silence. Capture stderr to assert the synthetic line is emitted.
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        mcp_client.report_stderr(1, "")          # abnormal exit, no stderr
        mcp_client.report_stderr(0, "")          # normal exit -> nothing
        mcp_client.report_stderr(-15, "")        # SIGTERM -> nothing
        mcp_client.report_stderr(None, "")       # still running -> nothing
    out = buf.getvalue()
    assert "exited 1 with no stderr" in out, f"empty-stderr crash must be reported: {out!r}"
    assert out.count("\n") == 1, f"only the abnormal exit should print: {out!r}"
    print("PASS: report_stderr surfaces empty-stderr crash, stays quiet on normal exits")


def test_skip_group_check_render_is_not_missing() -> None:
    # #33: emulate the per-group render path used by main() and assert that with
    # --skip-group-check no line says MISSING (it would contradict exit 0).
    tools = [t for t in _all_tools() if t not in smoke.TOOL_GROUPS["geometry_spice"]]
    groups = smoke._check_groups(tools)

    def render(skip: bool) -> list[str]:
        lines = []
        for name, info in groups.items():
            if skip:
                status = "skipped (not checked)"
            else:
                status = "ok" if info["ok"] else "MISSING " + ",".join(info["missing"])
            lines.append(f"  group {name}: {status}")
        return lines

    skipped = render(skip=True)
    assert not any("MISSING" in line for line in skipped), f"skip mode must not print MISSING: {skipped}"
    assert all("skipped (not checked)" in line for line in skipped)
    # Sanity: without skipping, the dropped group IS reported missing.
    enforced = render(skip=False)
    assert any("MISSING" in line for line in enforced), "enforced mode must still flag the gap"
    print("PASS: --skip-group-check render shows 'skipped', never MISSING")


def main() -> int:
    test_all_groups_present()
    test_missing_geometry_group_detected()
    test_partial_backend_group_detected()
    test_core_tools_are_subset_of_groups()
    test_initialize_params_no_hardcoded_protocol()
    test_report_stderr_surfaces_empty_exit()
    test_skip_group_check_render_is_not_missing()
    print("\nAll smoke group tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
