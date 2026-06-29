#!/usr/bin/env python3
"""Network-free tests for the runtime smoke's tool-group check (issues #8/#115).

These do NOT start the MCP server. They import the pure ``_check_groups`` and
``_check_optional_tiers`` helpers from ``smoke_mcp_runtime`` and assert that the
current 13-tool base surface is grouped correctly and that the gated optional
tiers (analysis / datasource / compat) are reported but never required, so CI
catches a dropped base family (for example all SPICE/geometry tools) even if the
total tool count still looks plausible. Run with plain
``python scripts/test_smoke_groups.py`` — no pytest, no network.
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


def test_optional_tiers_absent_on_base_surface() -> None:
    # The default wrapper ships the base surface only: HAPI/FDSN, analysis, and
    # legacy CDAWeb/PDS compat tools are gated off, so every optional tier must
    # report ``absent`` and none of them may appear in the base groups.
    base = _all_tools()
    tiers = smoke._check_optional_tiers(base)
    assert set(tiers) == set(smoke.OPTIONAL_TIERS), "report must cover every optional tier"
    for name, info in tiers.items():
        assert info["status"] == "absent", f"tier {name} must be absent on base surface: {info}"
        assert info["present"] == [], f"tier {name} must contribute no base tools"
    # The base groups must not accidentally re-list any gated tool.
    grouped = set(base)
    for tier, spec in smoke.OPTIONAL_TIERS.items():
        for tool in spec["tools"]:
            assert tool not in grouped, f"gated {tier} tool {tool!r} leaked into base TOOL_GROUPS"
    print("PASS: optional tiers are absent from the base surface")


def test_optional_tier_detected_when_unlocked() -> None:
    # When a deployment installs an extra / sets a gate flag, the corresponding
    # tier must be reported ``enabled`` (informational only; never gates ``ok``).
    base = _all_tools()
    analysis_tools = smoke.OPTIONAL_TIERS["analysis"]["tools"]
    tiers = smoke._check_optional_tiers(base + analysis_tools)
    assert tiers["analysis"]["status"] == "enabled", tiers["analysis"]
    assert tiers["datasource"]["status"] == "absent", tiers["datasource"]
    # A single advertised datasource tool -> partial.
    one = smoke.OPTIONAL_TIERS["datasource"]["tools"][:1]
    partial = smoke._check_optional_tiers(base + one)
    assert partial["datasource"]["status"] == "partial", partial["datasource"]
    print("PASS: unlocked optional tier reported enabled/partial")


def test_base_tools_are_subset_of_groups() -> None:
    # Every base tool must live in one of the base TOOL_GROUPS so the core-tool
    # check and the group check stay consistent.
    grouped = set(_all_tools())
    for name in smoke.BASE_EXPECTED_TOOLS:
        assert name in grouped, f"base tool {name!r} missing from TOOL_GROUPS"
    # The total base surface is exactly the 13 grouped tools.
    assert len(grouped) == len(smoke.BASE_EXPECTED_TOOLS) == 13, (
        f"base surface must be 13 tools, got {len(grouped)} grouped / "
        f"{len(smoke.BASE_EXPECTED_TOOLS)} expected"
    )
    print("PASS: BASE_EXPECTED_TOOLS are all covered by TOOL_GROUPS (13 tools)")


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
            "--from", "git+https://github.com/spedas/spedas_agent_kit.git@4d3e9a737e8bdd17988fb1f8f233e42aeaaa5baa",
            "spedas-agent-kit",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["is_spedas_agent_kit_source"], audit
    assert audit["configured_git_url"] == "git+https://github.com/spedas/spedas_agent_kit.git", audit
    assert audit["pinned_ref"] == "4d3e9a737e8bdd17988fb1f8f233e42aeaaa5baa", audit
    assert audit["ref_kind"] == "commit", audit
    assert audit["is_pinned"] is True, audit
    assert audit["resolved_spedas_agent_kit_commit"] == "4d3e9a737e8bdd17988fb1f8f233e42aeaaa5baa", audit
    assert audit["mcp_requirement"] == "mcp>=1.26.0,<2", audit
    assert audit["mcp_has_upper_bound"] is True, audit
    assert audit["spedas_agent_kit_extras"] == [], audit
    assert audit["analysis_extra_enabled"] is False, audit
    assert audit["entrypoint"] == "spedas-agent-kit", audit
    print("PASS: dependency audit parses a pinned full SHA + bounded mcp req")


def test_dependency_audit_detects_floating_and_unbounded() -> None:
    # A floating source (no @ref) and an open-ended mcp floor must be flagged.
    server = {
        "args": [
            "--with", "mcp>=1.26.0",
            "--from", "git+https://github.com/spedas/spedas_agent_kit.git",
            "spedas-agent-kit",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["pinned_ref"] is None, audit
    assert audit["ref_kind"] == "floating", audit
    assert audit["is_pinned"] is False, audit
    assert audit["resolved_spedas_agent_kit_commit"] is None, audit
    assert audit["mcp_has_upper_bound"] is False, audit
    print("PASS: dependency audit flags floating source + unbounded mcp")


def test_dependency_audit_does_not_treat_ssh_userinfo_as_pin() -> None:
    # user@host in an SSH URL is not a ref pin. The ref delimiter must come after
    # the repository path.
    server = {
        "args": [
            "--with", "mcp~=1.26.0",
            "--from", "git+ssh://git@github.com/spedas/spedas_agent_kit.git",
            "spedas-agent-kit",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["configured_git_url"] == "git+ssh://git@github.com/spedas/spedas_agent_kit.git", audit
    assert audit["pinned_ref"] is None, audit
    assert audit["ref_kind"] == "floating", audit
    assert audit["is_pinned"] is False, audit
    assert audit["mcp_requirement"] == "mcp~=1.26.0", audit
    assert audit["mcp_has_upper_bound"] is True, audit
    print("PASS: dependency audit rejects SSH userinfo as a pin and handles ~=")


def test_dependency_audit_direct_ref_with_ssh_userinfo_and_ref() -> None:
    # Preserve the issue #3 userinfo guard for SSH URLs:
    # git@github.com is not a pin, but a final @<sha> after the repo path is.
    server = {
        "args": [
            "--with", "mcp>=1.26.0,<2",
            "--from", "git+ssh://git@github.com/spedas/spedas_agent_kit.git@4d3e9a737e8bdd17988fb1f8f233e42aeaaa5baa",
            "spedas-agent-kit",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["configured_git_url"] == "git+ssh://git@github.com/spedas/spedas_agent_kit.git", audit
    assert audit["pinned_ref"] == "4d3e9a737e8bdd17988fb1f8f233e42aeaaa5baa", audit
    assert audit["ref_kind"] == "commit", audit
    assert audit["is_pinned"] is True, audit
    assert audit["spedas_agent_kit_extras"] == [], audit
    assert audit["analysis_extra_enabled"] is False, audit
    print("PASS: dependency audit handles SSH userinfo with final ref")


def test_dependency_audit_tag_ref_is_pinned_not_commit() -> None:
    # A tag pin is reproducible-ish (pinned) but not a content-addressed commit.
    server = {
        "args": [
            "--with", "mcp==1.26.0",
            "--from", "git+https://github.com/spedas/spedas_agent_kit.git@v0.2.0",
            "spedas-agent-kit",
        ],
    }
    audit = smoke._parse_dependency_audit(server)
    assert audit["pinned_ref"] == "v0.2.0", audit
    assert audit["ref_kind"] == "tag", audit
    assert audit["is_pinned"] is True, audit
    assert audit["resolved_spedas_agent_kit_commit"] is None, audit
    # exact == also counts as upper-bounded for the protocol dep.
    assert audit["mcp_has_upper_bound"] is True, audit
    print("PASS: dependency audit treats a tag ref as pinned (not a commit)")


def main() -> int:
    test_all_groups_present()
    test_missing_geometry_group_detected()
    test_optional_tiers_absent_on_base_surface()
    test_optional_tier_detected_when_unlocked()
    test_base_tools_are_subset_of_groups()
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
