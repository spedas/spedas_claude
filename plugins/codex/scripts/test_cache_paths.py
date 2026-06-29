#!/usr/bin/env python3
"""Network-free, filesystem-free cross-platform cache-path tests (issue #5).

These exercise the *pure* cache-path analysis helpers in ``smoke_mcp_runtime`` by
simulating different operating-system environments from a single host OS:

- POSIX / macOS with ``HOME`` set (the happy path),
- native Windows with ``USERPROFILE`` / ``LOCALAPPDATA`` and **no** ``HOME``,
- ``HOME`` unset on POSIX,
- a literal unresolved ``${HOME}`` reaching the server,
- a Windows absolute path with mixed separators.

The point is that ``${HOME}`` portability is verified the same way on every CI
runner (ubuntu/macos/windows) without starting the MCP server, writing to disk, or
hitting the network. Run with plain ``python scripts/test_cache_paths.py`` — no
pytest, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import smoke_mcp_runtime as smoke  # noqa: E402


# Mirror the packaged .mcp.json so a drift between this test and the real config is
# caught by test_matches_packaged_mcp_json below rather than hidden by a hard-code.
_PACKAGED_CACHE = {
    "XHELIO_CDAWEB_CACHE_DIR": "${HOME}/.cache/spedas/cdaweb",
    "PDSMCP_CACHE_DIR": "${HOME}/.cache/spedas/pds",
    "XHELIO_SPICE_KERNEL_DIR": "${HOME}/.cache/spedas/spice/kernels",
}


def test_posix_home_expands() -> None:
    a = smoke.analyze_cache_path("${HOME}/.cache/spedas/cdaweb", {"HOME": "/home/jdoe"})
    assert a["expanded"] == "/home/jdoe/.cache/spedas/cdaweb", a
    assert a["is_unresolved"] is False, a
    assert a["unresolved_vars"] == [], a
    assert a["looks_absolute"] is True, a
    assert a["caveats"] == [], a
    print("PASS: ${HOME} expands on POSIX with HOME set")


def test_macos_home_expands() -> None:
    a = smoke.analyze_cache_path("${HOME}/.cache/spedas/pds", {"HOME": "/Users/jdoe"})
    assert a["expanded"] == "/Users/jdoe/.cache/spedas/pds", a
    assert a["is_unresolved"] is False, a
    print("PASS: ${HOME} expands on macOS")


def test_native_windows_home_unset_is_flagged() -> None:
    # Native Windows: HOME unset, USERPROFILE present. The packaged ${HOME} value
    # cannot resolve from these env vars -> must be flagged as unresolved.
    env = {
        "USERPROFILE": r"C:\Users\jdoe",
        "LOCALAPPDATA": r"C:\Users\jdoe\AppData\Local",
    }
    a = smoke.analyze_cache_path("${HOME}/.cache/spedas/cdaweb", env)
    assert a["is_unresolved"] is True, a
    assert "${HOME}" in a["unresolved_vars"], a
    assert any("unresolved variable" in c for c in a["caveats"]), a
    print("PASS: native Windows (HOME unset, USERPROFILE set) flags literal ${HOME}")


def test_windows_userprofile_form_expands() -> None:
    # The documented Windows-friendly form: %USERPROFILE% or ${USERPROFILE}. Both
    # must resolve against a Windows-style environment.
    env = {"USERPROFILE": r"C:\Users\jdoe"}
    a_pct = smoke.analyze_cache_path("%USERPROFILE%/.cache/spedas/cdaweb", env)
    assert a_pct["is_unresolved"] is False, a_pct
    assert a_pct["expanded"].startswith(r"C:\Users\jdoe"), a_pct
    a_brace = smoke.analyze_cache_path("${USERPROFILE}/.cache/spedas/cdaweb", env)
    assert a_brace["is_unresolved"] is False, a_brace
    print("PASS: %USERPROFILE% and ${USERPROFILE} both expand on Windows env")


def test_home_unset_on_posix_collapses_root() -> None:
    # HOME unset (not even USERPROFILE): ${HOME} stays literal -> unresolved.
    a = smoke.analyze_cache_path("${HOME}/.cache/spedas/cdaweb", {})
    assert a["is_unresolved"] is True, a
    assert "${HOME}" in a["unresolved_vars"], a
    print("PASS: HOME unset on POSIX leaves ${HOME} unresolved (flagged)")


def test_literal_unresolved_passed_through() -> None:
    # Simulates Claude Code passing the value WITHOUT expanding it at all: the env
    # has HOME but the analysis is run against an env that lacks it, modelling a
    # loader that never substituted. The literal must be detected, not silently
    # accepted as a relative path.
    a = smoke.analyze_cache_path("${HOME}/.cache/spedas/cdaweb", {"NOTHOME": "/x"})
    assert a["is_unresolved"] is True, a
    assert a["looks_absolute"] is False, a  # a literal ${HOME}/... is not absolute
    print("PASS: literal unresolved ${HOME} is detected, not treated as absolute")


def test_windows_mixed_separators_caveat() -> None:
    # A Windows drive path mixing '\' and '/' is accepted by Python but rejected by
    # some C/Fortran/SPICE loaders -> caveat, but not 'unresolved'.
    a = smoke.analyze_cache_path(r"C:\Users\jdoe/.cache/spedas/cdaweb", {})
    assert a["is_unresolved"] is False, a
    assert a["path_flavor"]["has_drive_letter"] is True, a
    assert any("mixed path separators" in c for c in a["caveats"]), a
    print("PASS: mixed-separator Windows path raises a flavor caveat (not unresolved)")


def test_absolute_paths_are_clean() -> None:
    for raw in ("/Users/you/.cache/spedas/cdaweb", "C:/Users/you/AppData/Local/spedas/cdaweb"):
        a = smoke.analyze_cache_path(raw, {})
        assert a["is_unresolved"] is False, a
        assert a["looks_absolute"] is True, a
        assert a["caveats"] == [], a
    print("PASS: absolute POSIX and forward-slash Windows paths analyse clean")


def test_offline_diagnostics_posix_ok() -> None:
    server = {"env": dict(_PACKAGED_CACHE)}
    diag = smoke.offline_cache_diagnostics(server, {"HOME": "/home/jdoe"})
    assert diag["any_unresolved"] is False, diag
    for key in _PACKAGED_CACHE:
        assert diag["vars"][key]["configured"] is True, diag
        assert diag["vars"][key]["is_unresolved"] is False, diag
    print("PASS: offline_cache_diagnostics resolves packaged vars on POSIX")


def test_offline_diagnostics_windows_flags_unresolved() -> None:
    server = {"env": dict(_PACKAGED_CACHE)}
    diag = smoke.offline_cache_diagnostics(server, {"USERPROFILE": r"C:\Users\jdoe"})
    assert diag["any_unresolved"] is True, diag
    assert all(diag["vars"][key]["is_unresolved"] for key in _PACKAGED_CACHE), diag
    print("PASS: offline_cache_diagnostics flags packaged ${HOME} on native Windows")


def test_offline_diagnostics_handles_missing_and_nonstring_env() -> None:
    assert smoke.offline_cache_diagnostics({}, {"HOME": "/h"})["any_unresolved"] is False
    diag = smoke.offline_cache_diagnostics({"env": {"XHELIO_CDAWEB_CACHE_DIR": 123}}, {})
    assert diag["vars"]["XHELIO_CDAWEB_CACHE_DIR"]["configured"] is False, diag
    print("PASS: offline_cache_diagnostics tolerates absent/non-string env entries")


def test_matches_packaged_mcp_json() -> None:
    # Guard against drift: the env this test simulates must equal what .mcp.json
    # actually ships, so a future cache-var change can't silently bypass these tests.
    import json

    data = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    servers = data.get("mcpServers") or data.get("mcp_servers")
    shipped = servers["spedas"]["env"]
    for key, value in _PACKAGED_CACHE.items():
        assert shipped.get(key) == value, (
            f"packaged .mcp.json {key}={shipped.get(key)!r} differs from the value "
            f"these tests simulate ({value!r}); update test_cache_paths.py"
        )
    print("PASS: simulated cache vars match the packaged .mcp.json")


def main() -> int:
    test_posix_home_expands()
    test_macos_home_expands()
    test_native_windows_home_unset_is_flagged()
    test_windows_userprofile_form_expands()
    test_home_unset_on_posix_collapses_root()
    test_literal_unresolved_passed_through()
    test_windows_mixed_separators_caveat()
    test_absolute_paths_are_clean()
    test_offline_diagnostics_posix_ok()
    test_offline_diagnostics_windows_flags_unresolved()
    test_offline_diagnostics_handles_missing_and_nonstring_env()
    test_matches_packaged_mcp_json()
    print("\nAll cache-path tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
