#!/usr/bin/env python3
"""Runnable example: call a key SPEDAS MCP workflow tool end to end.

This is the smallest *useful* thing you can run against the packaged plugin
without Claude Code in the loop: it launches the configured ``spedas`` MCP
server exactly as ``.mcp.json`` declares it, then calls the read-only
``spedas_overview`` planning tool and prints the result.

Issue #19 asked for at least one runnable example for a key MCP workflow so a
scientist can confirm the plugin works and adapt it. ``spedas_overview`` is the
natural entry point: it is the workflow-layer tool Claude reaches for first, it
takes no credentials, and it fetches no science data and downloads no SPICE
kernels — so this example is safe to run anywhere ``uvx`` and the network are
available.

Like ``scripts/smoke_mcp_runtime.py``, this example is deliberately:

* **no-credential** — it passes no API keys or tokens;
* **no-data-fetch** — ``spedas_overview`` summarizes capabilities, it does not
  download CDAWeb/PDS products or SPICE kernels;
* **cache-isolated** — the data/kernel cache directories are redirected into a
  temporary folder unless you already set them in your environment, so running
  the example never writes to your real ``~/.cache/spedas/*``.

Usage::

    python examples/run_overview.py                 # human-readable summary
    python examples/run_overview.py --json           # raw tool result as JSON
    python examples/run_overview.py --timeout 300     # allow a slow first uvx build

The first run resolves and builds the SPEDAS MCP server from git HEAD via
``uvx`` (2-5 minutes); subsequent runs are fast. This mirrors how Claude Code
starts the same server from ``.mcp.json``.
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

# examples/ sits one level under the repo root; .mcp.json lives at the root.
ROOT = Path(__file__).resolve().parents[1]

# The key workflow tool this example demonstrates. Read-only and credential-free.
OVERVIEW_TOOL = "spedas_overview"


def _load_server_config() -> dict[str, Any]:
    """Read the packaged spedas server definition from .mcp.json."""
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


def _server_env(server: dict[str, Any], tmp: Path) -> dict[str, str]:
    """Build the child env, isolating data/kernel caches into a temp dir.

    Mirrors scripts/smoke_mcp_runtime.py: the packaged .mcp.json points the
    caches at the user's real ``~/.cache/spedas/*`` for normal plugin use, but a
    standalone example should be hermetic unless the caller deliberately set a
    cache variable in their environment.
    """
    env = os.environ.copy()
    configured = server.get("env") or {}
    if not isinstance(configured, dict):
        raise SystemExit("spedas MCP server env must be an object when present")
    for key, value in configured.items():
        if isinstance(key, str) and isinstance(value, str):
            env[key] = _expand(value)

    isolated = {
        "XHELIO_CDAWEB_CACHE_DIR": tmp / "cdaweb",
        "PDSMCP_CACHE_DIR": tmp / "pds",
        "XHELIO_SPICE_KERNEL_DIR": tmp / "spice",
    }
    for key, path in isolated.items():
        if key not in os.environ:
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
    return env


async def _read_message(reader: asyncio.StreamReader) -> dict[str, Any]:
    # MCP stdio framing: one JSON-RPC object per line. Reading it directly keeps
    # this example free of any extra client dependency.
    line = await reader.readline()
    if not line:
        raise RuntimeError("MCP server closed stdout before responding")
    return json.loads(line.decode("utf-8"))


async def _send_message(writer: asyncio.StreamWriter, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    writer.write(body + b"\n")
    await writer.drain()


async def _request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await _send_message(
        writer,
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )
    while True:
        message = await _read_message(reader)
        if message.get("id") == request_id:
            if "error" in message:
                raise RuntimeError(f"MCP {method} failed: {message['error']}")
            return message.get("result") or {}


async def _call_overview(
    command: str, args: list[str], env: dict[str, str], timeout: float
) -> dict[str, Any]:
    """Initialize the server and call spedas_overview, returning the tool result."""
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
        init = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "spedas-overview-example", "version": "0.1.0"},
        }
        await asyncio.wait_for(_request(proc.stdout, proc.stdin, 1, "initialize", init), timeout)
        await _send_message(
            proc.stdin,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        result = await asyncio.wait_for(
            _request(
                proc.stdout,
                proc.stdin,
                2,
                "tools/call",
                {"name": OVERVIEW_TOOL, "arguments": {}},
            ),
            timeout,
        )
        return result
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), 5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        stderr = (await proc.stderr.read()).decode("utf-8", errors="replace") if proc.stderr else ""
        if proc.returncode not in (0, -15, None) and stderr:
            print(stderr[-4000:], file=sys.stderr)


def _result_to_text(result: dict[str, Any]) -> str:
    """Flatten an MCP tools/call result into printable text.

    MCP returns ``content`` as a list of typed blocks; the overview tool emits
    text blocks. Fall back to JSON if the shape is unexpected so the example is
    robust to upstream changes (the tool surface is unpinned — see CHANGELOG).
    """
    content = result.get("content")
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        text = "\n".join(p for p in parts if p)
        if text:
            return text
    return json.dumps(result, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the raw tool result as JSON")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="per-request timeout in seconds (allow time for the first uvx build)",
    )
    args = parser.parse_args()

    server = _load_server_config()
    command, command_args = _server_command(server)
    with tempfile.TemporaryDirectory(prefix="spedas-overview-example-") as tmpdir:
        env = _server_env(server, Path(tmpdir))
        result = asyncio.run(_call_overview(command, command_args, env, args.timeout))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Called MCP tool: {OVERVIEW_TOOL}\n")
        print(_result_to_text(result))
    # MCP signals tool-level failure via isError; surface it as a non-zero exit.
    return 1 if result.get("isError") else 0


if __name__ == "__main__":
    raise SystemExit(main())
