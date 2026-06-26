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
        # protocolVersion sourced from the mcp library when available, else
        # omitted so the server negotiates — never a stale hardcoded constant (#25).
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
    with tempfile.TemporaryDirectory(prefix="spedas-plugin-smoke-") as tmpdir:
        env = _server_env(server, Path(tmpdir))
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
        "note": "initialize + tools/list only; no private credentials, interactive UI, data fetch, or SPICE kernel download",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"SPEDAS plugin MCP runtime smoke: {'OK' if payload['ok'] else 'FAIL'}")
        print(f"tool_count: {payload['tool_count']}")
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
