#!/usr/bin/env python3
"""Shared stdio MCP client helpers for the example and runtime smoke.

``examples/run_overview.py`` and ``scripts/smoke_mcp_runtime.py`` both speak the
same minimal JSON-RPC-over-stdio dialect to the packaged ``spedas`` MCP server.
Keeping the protocol-version source-of-truth, the line framing, and the failure
surfacing in one module means the two scripts stay in lockstep instead of drifting
apart (issues #25, #26).

Design constraints (unchanged from the two original scripts):

* **No hard dependency on the ``mcp`` Python package.** The wrapper repo ships no
  ``mcp`` install; the server is resolved at runtime via ``uvx --with mcp>=1.26.0``
  (see ``.mcp.json`` / ``docs/dependencies.md``). So this module *opportunistically*
  imports ``mcp`` for its protocol-version constant but never requires it.
* **One JSON object per line** stdio framing, no extra client dependency.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Any


def negotiated_protocol_version() -> str | None:
    """Resolve the MCP handshake ``protocolVersion`` without hardcoding it.

    Source of truth is the ``mcp`` library that the server itself runs against
    (``mcp>=1.26.0`` in ``.mcp.json`` / ``docs/dependencies.md``). If that library
    happens to be importable in this interpreter we use its
    ``LATEST_PROTOCOL_VERSION`` so the client and server can never drift to a
    stale pinned constant (issue #25).

    If ``mcp`` is not importable here — the common case, since the wrapper repo
    does not depend on it — we return ``None``. A ``None`` value means "omit the
    field": the MCP spec lets the server fall back to its own latest supported
    protocol version, which is exactly what we want rather than asserting a guess.
    """
    try:
        from mcp.types import LATEST_PROTOCOL_VERSION  # type: ignore
    except Exception:
        return None
    return LATEST_PROTOCOL_VERSION if isinstance(LATEST_PROTOCOL_VERSION, str) else None


def initialize_params(client_name: str, client_version: str = "0.1.0") -> dict[str, Any]:
    """Build the ``initialize`` params, including ``protocolVersion`` only if known.

    Omitting the field (rather than hardcoding ``2024-11-05``) lets the server
    negotiate when this interpreter cannot supply the library's current value.
    """
    params: dict[str, Any] = {
        "capabilities": {},
        "clientInfo": {"name": client_name, "version": client_version},
    }
    version = negotiated_protocol_version()
    if version is not None:
        params["protocolVersion"] = version
    return params


async def read_message(reader: asyncio.StreamReader) -> dict[str, Any]:
    # MCP stdio framing: one JSON-RPC object per line.
    line = await reader.readline()
    if not line:
        raise RuntimeError("MCP server closed stdout before responding")
    return json.loads(line.decode("utf-8"))


async def send_message(writer: asyncio.StreamWriter, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    writer.write(body + b"\n")
    await writer.drain()


async def request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    request_id: int,
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await send_message(
        writer,
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )
    while True:
        message = await read_message(reader)
        if message.get("id") == request_id:
            if "error" in message:
                raise RuntimeError(f"MCP {method} failed: {message['error']}")
            return message.get("result") or {}


async def drain_process(proc: asyncio.subprocess.Process) -> str:
    """Terminate the server if still running and return its captured stderr.

    Printing the diagnostic is left to the caller via :func:`report_stderr` so the
    example and smoke can phrase their abnormal-exit message identically.
    """
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    return (await proc.stderr.read()).decode("utf-8", errors="replace") if proc.stderr else ""


def report_stderr(returncode: int | None, stderr: str) -> None:
    """Print server stderr on *any* abnormal exit, even when stderr is empty.

    The old guard ``returncode not in (...) and stderr`` swallowed the most
    confusing case — a non-zero exit with no stderr — leaving the user with
    silence (issue #26). Treat 0 / SIGTERM(-15) / "still running"(None) as normal;
    everything else reports, falling back to a synthetic line when stderr is empty.
    """
    if returncode in (0, -15, None):
        return
    print(stderr[-4000:] or f"(server exited {returncode} with no stderr)", file=sys.stderr)


def run_client(coro: Any, *, context: str) -> Any:
    """Run an async MCP client coroutine, turning expected failures into a concise
    one-line message + non-zero exit instead of a raw traceback (issue #26).

    ``context`` names the operation for the message, e.g. "initialize/overview".
    """
    try:
        return asyncio.run(coro)
    except (TimeoutError, asyncio.TimeoutError):
        raise SystemExit(f"MCP server timed out during {context}")
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"MCP server failed during {context}: {exc}")
