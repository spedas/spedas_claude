#!/usr/bin/env python3
"""Runtime smoke-test the packaged SPEDAS MCP server configuration.

This is intentionally a no-credential, no-interactive-UI, no-data-fetch smoke.
It reads the repo's .mcp.json, starts the configured ``spedas`` stdio MCP server,
performs MCP ``initialize`` and ``tools/list`` JSON-RPC calls, verifies the core
SPEDAS tool surface, then exits. Cache directories are isolated in a temporary
folder unless the caller already set them.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Shared stdio MCP client helpers (protocol-version source-of-truth, framing,
# failure surfacing), kept in lockstep with examples/run_overview.py (#25, #26).
sys.path.insert(0, str(ROOT / "scripts"))
import mcp_client_common as mcp_client  # noqa: E402

# Tool groups, aligned with the reference docs under
# skills/spedas-workflow/reference/. The smoke verifies that each advertised
# group is actually present at runtime, not just that the total tool count
# matches. This catches a backend that silently drops the geometry/SPICE family
# or the unified facade while still exposing "enough" tools to pass a count
# check. See tool-examples.md, geometry-spice.md, backend-compatibility.md.
TOOL_GROUPS: dict[str, list[str]] = {
    # Science workflow / planning layer (no backend equivalents).
    "workflow": [
        "spedas_overview",
        "search_spedas_data_sources",
        "plan_spedas_observation",
        "compare_cdaweb_pds_spice",
        "create_spedas_analysis_bundle",
    ],
    # Unified public facade: source_type-parameterized data layer.
    "unified_data": [
        "browse_data_sources",
        "load_data_source",
        "browse_data_parameters",
        "fetch_data_product",
        "manage_data_cache",
    ],
    # Dedicated geometry/SPICE tools (#7/#8): metadata + gated kernel surface.
    "geometry_spice": [
        "list_spice_missions",
        "get_ephemeris",
        "compute_distance",
        "transform_coordinates",
        "list_coordinate_frames",
        "manage_spice_kernels",
    ],
    # Backend compatibility/maintenance tools (#18): CDAWeb + PDS.
    "backend_cdaweb": [
        "browse_observatories",
        "load_observatory",
        "browse_parameters",
        "fetch_data",
        "manage_cdaweb_cache",
    ],
    "backend_pds": [
        "browse_pds_missions",
        "load_pds_mission",
        "browse_pds_parameters",
        "fetch_pds_data",
        "manage_pds_cache",
    ],
}

# Core tools that must always be present (the unified facade + workflow layer).
# Kept as a named constant for backward-compatible JSON output.
EXPECTED_CORE_TOOLS = [
    "spedas_overview",
    "browse_data_sources",
    "load_data_source",
    "browse_data_parameters",
    "fetch_data_product",
    "manage_data_cache",
    "search_spedas_data_sources",
    "plan_spedas_observation",
    "compare_cdaweb_pds_spice",
    "create_spedas_analysis_bundle",
]


def _check_groups(tools: list[str]) -> dict[str, dict[str, Any]]:
    """For each advertised tool group, report which members are present/missing."""
    present = set(tools)
    report: dict[str, dict[str, Any]] = {}
    for group, members in TOOL_GROUPS.items():
        missing = [name for name in members if name not in present]
        report[group] = {
            "expected": members,
            "missing": missing,
            "ok": not missing,
        }
    return report


# A full git commit SHA is 40 hex chars (or 64 for SHA-256). Anything shorter or
# non-hex after the ``@`` is treated as a tag/branch ref, which is still pinned
# (deterministic) but not a content-addressed commit.
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_MCP_REQ_RE = re.compile(r"^mcp(?=[<>=!~])")


def _split_git_url_ref(from_value: str) -> tuple[str, str | None]:
    """Split a pip/uv git URL into (url_without_ref, ref).

    A real pin is the final ``@<ref>`` after the repository path. Userinfo/SSH
    forms such as ``git+ssh://git@github.com/spedas/spedas_mcp.git`` also contain
    ``@`` before the final slash; those must NOT be treated as pinned refs.
    """
    if not from_value.startswith("git+"):
        return from_value, None
    base, sep, fragment = from_value.partition("#")
    at = base.rfind("@")
    last_slash = base.rfind("/")
    if at > last_slash:
        ref = base[at + 1 :] or None
        url = base[:at]
        if sep:
            url = f"{url}#{fragment}"
        return url, ref
    return from_value, None


def _is_mcp_requirement(compact: str) -> bool:
    return compact == "mcp" or bool(_MCP_REQ_RE.match(compact))


def _mcp_has_upper_bound(compact: str) -> bool:
    return "==" in compact or "<" in compact or "~=" in compact


def _parse_dependency_audit(server: dict[str, Any]) -> dict[str, Any]:
    """Derive a compact dependency-audit object from the configured server args.

    This is issue #3's audit trail: from ``.mcp.json`` alone (no network) we can
    report the configured ``spedas_mcp`` git URL, the pinned ref and whether it is
    a full commit SHA / tag / floating default branch, the MCP protocol
    requirement and whether it carries an upper bound, and the console entrypoint.

    Because the default source is pinned to a full SHA, the parsed ``@<sha>`` is
    the resolved ``spedas_mcp`` commit — no ``uv pip show`` / network call is
    needed in the normal smoke path.
    """
    args = server.get("args") or []
    args = [a for a in args if isinstance(a, str)]

    def _value_after(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return None

    # --from carries the git source (and optional @ref); the trailing bare arg is
    # the console entrypoint.
    from_value = _value_after("--from") or ""
    git_url, pinned_ref = _split_git_url_ref(from_value)

    is_spedas_mcp_source = "github.com/spedas/spedas_mcp" in from_value

    if pinned_ref is None:
        ref_kind = "floating"          # no @ref -> resolves default branch HEAD each run
    elif _FULL_SHA_RE.match(pinned_ref):
        ref_kind = "commit"            # content-addressed, fully reproducible
    else:
        ref_kind = "tag"               # tag/branch name: pinned but mutable upstream

    # --with carries the MCP protocol requirement, e.g. "mcp>=1.26.0,<2".
    mcp_requirement: str | None = None
    for a in args:
        compact = a.replace(" ", "")
        if _is_mcp_requirement(compact):
            mcp_requirement = a
            break
    has_upper_bound = bool(mcp_requirement) and _mcp_has_upper_bound(mcp_requirement.replace(" ", ""))

    entrypoint = args[-1] if args else None

    return {
        "configured_git_url": git_url or None,
        "from_arg": from_value or None,
        "is_spedas_mcp_source": is_spedas_mcp_source,
        "pinned_ref": pinned_ref,
        "ref_kind": ref_kind,
        "is_pinned": ref_kind != "floating",
        "resolved_spedas_mcp_commit": pinned_ref if ref_kind == "commit" else None,
        "mcp_requirement": mcp_requirement,
        "mcp_has_upper_bound": has_upper_bound,
        "entrypoint": entrypoint,
    }


def _cache_diagnostics(env: dict[str, str], tmp: Path) -> dict[str, Any]:
    """Report resolved cache paths, temp-isolation status, and writability for the
    smoke subprocess (issue #5 diagnostics).

    For each SPEDAS data/kernel cache var plus UV/XDG/TMP, record the path that was
    handed to the subprocess, whether the smoke substituted a temp-isolation
    override (i.e. the resolved path lives under this run's temp dir), and whether
    that path is writable. This is purely diagnostic — it does not fetch data.
    """
    tmp_resolved = str(tmp.resolve())
    keys = [
        "XHELIO_CDAWEB_CACHE_DIR",
        "PDSMCP_CACHE_DIR",
        "XHELIO_SPICE_KERNEL_DIR",
        "UV_CACHE_DIR",
        "XDG_CACHE_HOME",
        "TMPDIR",
    ]
    report: dict[str, Any] = {}
    for key in keys:
        raw = env.get(key)
        if not raw:
            report[key] = {"resolved": None, "set": False}
            continue
        path = Path(raw)
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = raw
        report[key] = {
            "resolved": resolved,
            "set": True,
            "temp_isolated": resolved.startswith(tmp_resolved),
            # Caller-provided (process env) values are not auto-isolated; the
            # data-cache vars are isolated to tmp unless the caller set them.
            "from_caller_env": key in os.environ and os.environ.get(key) == raw,
            "writable": _is_writable_dir(path),
        }
    return report


def _load_server_config() -> dict[str, Any]:
    data = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    servers = data.get("mcpServers") or data.get("mcp_servers")
    if not isinstance(servers, dict) or "spedas" not in servers:
        raise SystemExit(".mcp.json must define a spedas MCP server")
    server = servers["spedas"]
    if not isinstance(server, dict):
        raise SystemExit("spedas MCP server config must be an object")
    return server


def _expand(value: str) -> str:
    # Support the common plugin form ${HOME}/... plus ordinary shell-style vars.
    return os.path.expandvars(value)


def _server_command(server: dict[str, Any]) -> tuple[str, list[str]]:
    command = server.get("command")
    args = server.get("args") or []
    if not isinstance(command, str) or not command:
        raise SystemExit("spedas MCP server config must provide a command")
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise SystemExit("spedas MCP server args must be a list of strings")
    return _expand(command), [_expand(item) for item in args]


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".spedas-smoke-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _prefer_temp_if_unwritable(env: dict[str, str], key: str, candidate: Path, fallback: Path) -> None:
    current = os.environ.get(key)
    if current:
        expanded = Path(_expand(current))
        if not _is_writable_dir(expanded):
            fallback.mkdir(parents=True, exist_ok=True)
            env[key] = str(fallback)
        return
    if not _is_writable_dir(candidate):
        fallback.mkdir(parents=True, exist_ok=True)
        env[key] = str(fallback)


def _server_env(server: dict[str, Any], tmp: Path) -> dict[str, str]:
    env = os.environ.copy()
    configured = server.get("env") or {}
    if not isinstance(configured, dict):
        raise SystemExit("spedas MCP server env must be an object when present")
    for key, value in configured.items():
        if isinstance(key, str) and isinstance(value, str):
            env[key] = _expand(value)

    # The packaged .mcp.json points at normal user caches for real plugin use.
    # Runtime smoke tests should be hermetic unless the caller explicitly set a
    # cache variable in the process environment. This keeps CI/Codex sandboxes
    # from writing to user caches and avoids false failures when HOME is read-only.
    isolated_data_caches = {
        "XHELIO_CDAWEB_CACHE_DIR": tmp / "cdaweb",
        "PDSMCP_CACHE_DIR": tmp / "pds",
        "XHELIO_SPICE_KERNEL_DIR": tmp / "spice",
    }
    for key, path in isolated_data_caches.items():
        if key not in os.environ:
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)

    _prefer_temp_if_unwritable(env, "UV_CACHE_DIR", Path.home() / ".cache" / "uv", tmp / "uv-cache")
    _prefer_temp_if_unwritable(env, "XDG_CACHE_HOME", Path.home() / ".cache", tmp / "xdg-cache")
    tmp_candidate = Path(os.environ.get("TMPDIR", tempfile.gettempdir()))
    _prefer_temp_if_unwritable(env, "TMPDIR", tmp_candidate, tmp / "tmp")
    return env


async def _smoke(command: str, args: list[str], env: dict[str, str], timeout: float) -> list[str]:
    proc = await asyncio.create_subprocess_exec(
        command,
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        # Shared helper always supplies protocolVersion from env, the MCP
        # library constant, or its documented fallback; never duplicate a
        # per-script protocol literal here (#25).
        init = mcp_client.initialize_params("spedas-plugin-runtime-smoke")
        await asyncio.wait_for(mcp_client.request(proc.stdout, proc.stdin, 1, "initialize", init), timeout)
        await mcp_client.send_message(proc.stdin, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        result = await asyncio.wait_for(mcp_client.request(proc.stdout, proc.stdin, 2, "tools/list"), timeout)
        tools = result.get("tools") or []
        return [tool.get("name") for tool in tools if isinstance(tool, dict) and isinstance(tool.get("name"), str)]
    finally:
        # Report server stderr on any abnormal exit, even when stderr is empty (#26).
        stderr = await mcp_client.drain_process(proc)
        mcp_client.report_stderr(proc.returncode, stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--timeout", type=float, default=180.0, help="per-request timeout in seconds")
    parser.add_argument(
        "--skip-group-check",
        action="store_true",
        help=(
            "only verify core tools, not the geometry/SPICE and unified-vs-backend "
            "tool groups; group lines are then shown as 'skipped (not checked)' so "
            "the output matches the exit code"
        ),
    )
    args = parser.parse_args()

    server = _load_server_config()
    command, command_args = _server_command(server)
    dependency_audit = _parse_dependency_audit(server)
    with tempfile.TemporaryDirectory(prefix="spedas-plugin-smoke-") as tmpdir:
        tmp = Path(tmpdir)
        env = _server_env(server, tmp)
        cache_diagnostics = _cache_diagnostics(env, tmp)
        # Turn timeouts / server crashes / closed-stdout into a one-line message
        # and non-zero exit instead of a raw traceback (#26).
        tools = mcp_client.run_client(
            _smoke(command, command_args, env, args.timeout),
            context="initialize/tools-list",
        )

    missing = [name for name in EXPECTED_CORE_TOOLS if name not in tools]
    groups = _check_groups(tools)
    missing_groups = [name for name, info in groups.items() if not info["ok"]]
    groups_ok = args.skip_group_check or not missing_groups
    ok = not missing and groups_ok

    payload = {
        "ok": ok,
        "tool_count": len(tools),
        "tools": tools,
        "expected_core_tools": EXPECTED_CORE_TOOLS,
        "missing_core_tools": missing,
        "tool_groups": groups,
        "missing_groups": missing_groups,
        "group_check_enforced": not args.skip_group_check,
        "command": [command, *command_args],
        "dependency_audit": dependency_audit,
        "cache_diagnostics": cache_diagnostics,
        "note": "initialize + tools/list only; no private credentials, interactive UI, data fetch, or SPICE kernel download",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"SPEDAS plugin MCP runtime smoke: {'OK' if payload['ok'] else 'FAIL'}")
        print(f"tool_count: {payload['tool_count']}")
        # Issue #3 audit trail: surface the configured source/pin in human mode too.
        da = dependency_audit
        print(f"spedas_mcp source: {da['from_arg']}")
        print(
            f"  pinned: {da['is_pinned']} (ref_kind={da['ref_kind']}, "
            f"resolved_commit={da['resolved_spedas_mcp_commit']})"
        )
        print(
            f"  mcp requirement: {da['mcp_requirement']} "
            f"(upper_bound={da['mcp_has_upper_bound']})"
        )
        for name, info in groups.items():
            # With --skip-group-check the group result does not affect the exit
            # code, so reporting "MISSING ..." would contradict a passing run (#33).
            # Show the groups as explicitly skipped instead.
            if args.skip_group_check:
                status = "skipped (not checked)"
            else:
                status = "ok" if info["ok"] else "MISSING " + ",".join(info["missing"])
            print(f"  group {name}: {status}")
        if missing:
            print("missing core tools: " + ", ".join(missing), file=sys.stderr)
        if missing_groups and not args.skip_group_check:
            print("incomplete tool groups: " + ", ".join(missing_groups), file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
