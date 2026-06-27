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
    # #25: the handshake must not pin the old per-script hardcoded constant, but
    # it must still send protocolVersion because the server rejects an omitted
    # field. The version comes from one helper: env override, mcp library constant,
    # or the helper's documented compatibility fallback.
    params = mcp_client.initialize_params("unit-test")
    assert params["clientInfo"]["name"] == "unit-test"
    assert "capabilities" in params
    version = mcp_client.negotiated_protocol_version()
    assert params["protocolVersion"] == version, "initialize must use shared helper version"
    assert params["protocolVersion"] != "2024-11-05", "must not regress to the stale literal"
    print(f"PASS: initialize_params uses shared protocolVersion={version!r}")


def test_protocol_version_env_override() -> None:
    # #25/#26: users and CI need an escape hatch if the MCP protocol changes before
    # the wrapper updates. The primary SPEDAS-specific env var should win.
    import os

    old_spedas = os.environ.get("SPEDAS_MCP_PROTOCOL_VERSION")
    old_generic = os.environ.get("MCP_PROTOCOL_VERSION")
    try:
        os.environ["MCP_PROTOCOL_VERSION"] = "generic-test-version"
        assert mcp_client.negotiated_protocol_version() == "generic-test-version"
        os.environ["SPEDAS_MCP_PROTOCOL_VERSION"] = "spedas-test-version"
        assert mcp_client.negotiated_protocol_version() == "spedas-test-version"
        assert mcp_client.initialize_params("unit-test")["protocolVersion"] == "spedas-test-version"
    finally:
        if old_spedas is None:
            os.environ.pop("SPEDAS_MCP_PROTOCOL_VERSION", None)
        else:
            os.environ["SPEDAS_MCP_PROTOCOL_VERSION"] = old_spedas
        if old_generic is None:
            os.environ.pop("MCP_PROTOCOL_VERSION", None)
        else:
            os.environ["MCP_PROTOCOL_VERSION"] = old_generic
    print("PASS: protocol version env override works")


def test_protocol_version_fallback_when_mcp_unavailable() -> None:
    # The CI wrapper matrix does not install the optional mcp client package. In
    # that environment we must still send protocolVersion rather than omit it.
    import builtins
    import os

    old_spedas = os.environ.pop("SPEDAS_MCP_PROTOCOL_VERSION", None)
    old_generic = os.environ.pop("MCP_PROTOCOL_VERSION", None)
    real_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[override]
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("blocked mcp import for fallback test")
        return real_import(name, globals, locals, fromlist, level)

    try:
        builtins.__import__ = blocked_import
        version = mcp_client.negotiated_protocol_version()
        assert version == mcp_client.FALLBACK_PROTOCOL_VERSION
        assert mcp_client.initialize_params("unit-test")["protocolVersion"] == version
        assert version != "2024-11-05"
    finally:
        builtins.__import__ = real_import
        if old_spedas is not None:
            os.environ["SPEDAS_MCP_PROTOCOL_VERSION"] = old_spedas
        if old_generic is not None:
            os.environ["MCP_PROTOCOL_VERSION"] = old_generic
    print("PASS: fallback protocolVersion is sent when mcp is unavailable")


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


def test_dependency_audit_parses_pinned_sha() -> None:
    # Issue #3: the audit object must report the pinned commit and a bounded MCP req
    # from .mcp.json args alone, no network.
    server = {
        "args": [
            "--with", "mcp>=1.26.0,<2",
            "--from", "git+https://github.com/spedas/spedas_mcp.git@4afdae39bda2ee11e27606809491b4d642e8ecc9",
            "spedas-mcp",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["is_spedas_mcp_source"], audit
    assert audit["configured_git_url"] == "git+https://github.com/spedas/spedas_mcp.git", audit
    assert audit["pinned_ref"] == "4afdae39bda2ee11e27606809491b4d642e8ecc9", audit
    assert audit["ref_kind"] == "commit", audit
    assert audit["is_pinned"] is True, audit
    assert audit["resolved_spedas_mcp_commit"] == "4afdae39bda2ee11e27606809491b4d642e8ecc9", audit
    assert audit["mcp_requirement"] == "mcp>=1.26.0,<2", audit
    assert audit["mcp_has_upper_bound"] is True, audit
    assert audit["entrypoint"] == "spedas-mcp", audit
    print("PASS: dependency audit parses a pinned full SHA + bounded mcp req")


def test_dependency_audit_detects_floating_and_unbounded() -> None:
    # A floating source (no @ref) and an open-ended mcp floor must be flagged.
    server = {
        "args": [
            "--with", "mcp>=1.26.0",
            "--from", "git+https://github.com/spedas/spedas_mcp.git",
            "spedas-mcp",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["pinned_ref"] is None, audit
    assert audit["ref_kind"] == "floating", audit
    assert audit["is_pinned"] is False, audit
    assert audit["resolved_spedas_mcp_commit"] is None, audit
    assert audit["mcp_has_upper_bound"] is False, audit
    print("PASS: dependency audit flags floating source + unbounded mcp")


def test_dependency_audit_does_not_treat_ssh_userinfo_as_pin() -> None:
    # user@host in an SSH URL is not a ref pin. The ref delimiter must come after
    # the repository path.
    server = {
        "args": [
            "--with", "mcp~=1.26.0",
            "--from", "git+ssh://git@github.com/spedas/spedas_mcp.git",
            "spedas-mcp",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["configured_git_url"] == "git+ssh://git@github.com/spedas/spedas_mcp.git", audit
    assert audit["pinned_ref"] is None, audit
    assert audit["ref_kind"] == "floating", audit
    assert audit["is_pinned"] is False, audit
    assert audit["mcp_requirement"] == "mcp~=1.26.0", audit
    assert audit["mcp_has_upper_bound"] is True, audit
    print("PASS: dependency audit rejects SSH userinfo as a pin and handles ~=")


def test_dependency_audit_tag_ref_is_pinned_not_commit() -> None:
    # A tag pin is reproducible-ish (pinned) but not a content-addressed commit.
    server = {
        "args": [
            "--with", "mcp==1.26.0",
            "--from", "git+https://github.com/spedas/spedas_mcp.git@v0.2.0",
            "spedas-mcp",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["pinned_ref"] == "v0.2.0", audit
    assert audit["ref_kind"] == "tag", audit
    assert audit["is_pinned"] is True, audit
    assert audit["resolved_spedas_mcp_commit"] is None, audit
    # exact == also counts as upper-bounded for the protocol dep.
    assert audit["mcp_has_upper_bound"] is True, audit
    print("PASS: dependency audit treats a tag ref as pinned (not a commit)")


def main() -> int:
    test_all_groups_present()
    test_missing_geometry_group_detected()
    test_partial_backend_group_detected()
    test_core_tools_are_subset_of_groups()
    test_initialize_params_no_hardcoded_protocol()
    test_protocol_version_env_override()
    test_protocol_version_fallback_when_mcp_unavailable()
    test_report_stderr_surfaces_empty_exit()
    test_skip_group_check_render_is_not_missing()
    test_dependency_audit_parses_pinned_sha()
    test_dependency_audit_detects_floating_and_unbounded()
    test_dependency_audit_does_not_treat_ssh_userinfo_as_pin()
    test_dependency_audit_tag_ref_is_pinned_not_commit()
    print("\nAll smoke group tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
