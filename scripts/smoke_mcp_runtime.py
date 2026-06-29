#!/usr/bin/env python3
"""Runtime smoke-test the packaged SPEDAS Agent Kit MCP server configuration.

This is intentionally a no-credential, no-interactive-UI, no-data-fetch smoke.
It reads the repo's .mcp.json, starts the configured ``spedas`` stdio MCP server,
performs MCP ``initialize`` and ``tools/list`` JSON-RPC calls, verifies the base
(default) SPEDAS tool surface, reports which optional/gated tiers are unlocked,
then exits. Cache directories are isolated in a temporary folder unless the
caller already set them.
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
# The Agent Kit tool surface is TIERED, not a flat list. Only the base/default
# tools are unconditionally advertised. Optional families are gated:
#   - analysis  -> registered only when the ``[analysis]`` extra is installed.
#   - datasource (HAPI/FDSN) -> hidden from list_tools unless
#     ``SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1`` (#87/#145 demoted these from core).
#   - compat (legacy CDAWeb/PDS) -> hidden unless
#     ``SPEDAS_AGENT_KIT_COMPAT_TOOLS=1``.
# The default Claude wrapper ships the BASE surface only (its .mcp.json requests
# no extras and sets none of the gate flags), so the smoke asserts the 13 base
# tools and treats the gated families as conditionally-present, never as core.
TOOL_GROUPS: dict[str, list[str]] = {
    # Science workflow / planning layer (base).
    "workflow": [
        "spedas_overview",
        "search_spedas_data_sources",
        "plan_spedas_observation",
        "compare_cdaweb_pds_spice",
        "create_spedas_analysis_bundle",
    ],
    # Unified public facade: source_type-parameterized data layer (base).
    "unified_data": [
        "browse_data_sources",
        "load_data_source",
        "browse_data_parameters",
        "fetch_data_product",
        "manage_data_cache",
    ],
    # Current SPICE/geometry core tools (base). Catalog/cache inspection is
    # routed through the unified facade (browse/load_data_source,
    # manage_data_cache).
    "geometry_spice": [
        "get_ephemeris",
        "compute_distance",
        "transform_coordinates",
    ],
}

# Base/default tools that MUST be present for the current pinned spedas_agent_kit
# server with no extras and no gate flags. This is the 13-tool base surface at
# commit e504dae. Optional analysis tools, HAPI/FDSN datasource tools, and the
# legacy CDAWeb/PDS compat tools are NOT in this list because they are gated off
# by default (see OPTIONAL_TIERS).
BASE_EXPECTED_TOOLS = [
    "spedas_overview",
    "search_spedas_data_sources",
    "plan_spedas_observation",
    "compare_cdaweb_pds_spice",
    "create_spedas_analysis_bundle",
    "browse_data_sources",
    "load_data_source",
    "browse_data_parameters",
    "fetch_data_product",
    "manage_data_cache",
    "get_ephemeris",
    "compute_distance",
    "transform_coordinates",
]

# Backwards-compatible alias; the default wrapper surface is the base surface.
EXPECTED_CORE_TOOLS = BASE_EXPECTED_TOOLS

# Optional tool tiers and how they are unlocked. Reported for visibility only:
# the smoke never requires them in the default surface, but it labels any that
# DO appear (e.g. a deployment that installs [analysis] or sets a gate flag) so
# the surface stays auditable.
#   - analysis     : +13 tools when ``spedas-agent-kit[analysis]`` is installed.
#   - datasource   : +4 HAPI/FDSN tools when SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1.
#   - compat       : +8 legacy CDAWeb/PDS tools when SPEDAS_AGENT_KIT_COMPAT_TOOLS=1.
OPTIONAL_TIERS: dict[str, dict[str, Any]] = {
    "analysis": {
        "unlock": "install spedas-agent-kit[analysis]",
        "tools": [
            "transform_timeseries_coordinates",
            "generate_fac_matrix",
            "tvector_rotate",
            "analyze_minvar_coordinates",
            "dynamic_power_spectrum",
            "wavelet_transform",
            "evaluate_magnetic_field",
            "calculate_lshell",
            "build_particle_distribution_artifact",
            "load_particle_distribution_artifact",
            "compute_particle_moments",
            "compute_particle_spectra",
            "render_tplot",
        ],
    },
    "datasource": {
        "unlock": "SPEDAS_AGENT_KIT_DATASOURCE_TOOLS=1",
        "tools": [
            "browse_hapi_catalog",
            "fetch_hapi_data",
            "browse_fdsn_datasets",
            "fetch_fdsn_data",
        ],
    },
    "compat": {
        "unlock": "SPEDAS_AGENT_KIT_COMPAT_TOOLS=1",
        "tools": [
            "browse_observatories",
            "load_observatory",
            "browse_parameters",
            "fetch_data",
            "browse_pds_missions",
            "load_pds_mission",
            "browse_pds_parameters",
            "fetch_pds_data",
        ],
    },
}


def _check_groups(tools: list[str]) -> dict[str, dict[str, Any]]:
    """For each advertised base tool group, report which members are present/missing."""
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


def _check_optional_tiers(tools: list[str]) -> dict[str, dict[str, Any]]:
    """Report which optional (gated) tiers are present in the live surface.

    The default Claude wrapper ships none of these, so they are NEVER required
    and never affect the exit code. This is purely an audit of what extras/gate
    flags a given deployment unlocked: a tier counts as ``enabled`` only when
    ALL of its tools are advertised, ``partial`` if some are, ``absent`` if none.
    """
    present = set(tools)
    report: dict[str, dict[str, Any]] = {}
    for tier, spec in OPTIONAL_TIERS.items():
        members = spec["tools"]
        found = [name for name in members if name in present]
        if not found:
            status = "absent"
        elif len(found) == len(members):
            status = "enabled"
        else:
            status = "partial"
        report[tier] = {
            "unlock": spec["unlock"],
            "expected": members,
            "present": found,
            "status": status,
        }
    return report


# A full git commit SHA is 40 hex chars (or 64 for SHA-256). Anything shorter or
# non-hex after the ``@`` is treated as a tag/branch ref, which is still pinned
# (deterministic) but not a content-addressed commit.
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_MCP_REQ_RE = re.compile(r"^mcp(?=[<>=!~])")
_DIRECT_GIT_REQ_RE = re.compile(
    r"^(?P<package>[A-Za-z0-9_.-]+)(?:\[(?P<extras>[^\]]*)\])?@(?P<url>git\+.+)$"
)


def _extract_git_source_and_extras(from_value: str) -> tuple[str, set[str]]:
    """Return the git URL inside a uv/pip ``--from`` value and requested extras."""
    compact = from_value.replace(" ", "")
    match = _DIRECT_GIT_REQ_RE.match(compact)
    if not match:
        return from_value.strip(), set()
    extras = {
        item.strip().lower().replace("_", "-")
        for item in (match.group("extras") or "").split(",")
        if item.strip()
    }
    return match.group("url"), extras


def _split_git_url_ref(from_value: str) -> tuple[str, str | None]:
    """Split a pip/uv git source into (url_without_ref, ref).

    A real pin is the final ``@<ref>`` after the repository path. Userinfo/SSH
    forms such as ``git+ssh://git@github.com/spedas/spedas_agent_kit.git`` also contain
    ``@`` before the final slash; those must NOT be treated as pinned refs. The
    input may be a bare git URL or a PEP 508 direct reference with extras.
    """
    git_source, _ = _extract_git_source_and_extras(from_value)
    if not git_source.startswith("git+"):
        return git_source, None
    base, sep, fragment = git_source.partition("#")
    at = base.rfind("@")
    last_slash = base.rfind("/")
    if at > last_slash:
        ref = base[at + 1 :] or None
        url = base[:at]
        if sep:
            url = f"{url}#{fragment}"
        return url, ref
    return git_source, None


def _is_mcp_requirement(compact: str) -> bool:
    return compact == "mcp" or bool(_MCP_REQ_RE.match(compact))


def _mcp_has_upper_bound(compact: str) -> bool:
    return "==" in compact or "<" in compact or "~=" in compact


def _parse_dependency_audit(server: dict[str, Any]) -> dict[str, Any]:
    """Derive a compact dependency-audit object from the configured server args.

    This is issue #3's audit trail: from ``.mcp.json`` alone (no network) we can
    report the configured ``spedas_agent_kit`` git URL, the pinned ref and whether it is
    a full commit SHA / tag / floating default branch, the MCP protocol
    requirement and whether it carries an upper bound, and the console entrypoint.

    Because the default source is pinned to a full SHA, the parsed ``@<sha>`` is
    the resolved ``spedas_agent_kit`` commit — no ``uv pip show`` / network call is
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
    _, spedas_agent_kit_extras = _extract_git_source_and_extras(from_value)

    is_spedas_agent_kit_source = "github.com/spedas/spedas_agent_kit" in from_value

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
        "is_spedas_agent_kit_source": is_spedas_agent_kit_source,
        "pinned_ref": pinned_ref,
        "ref_kind": ref_kind,
        "is_pinned": ref_kind != "floating",
        "resolved_spedas_agent_kit_commit": pinned_ref if ref_kind == "commit" else None,
        "mcp_requirement": mcp_requirement,
        "mcp_has_upper_bound": has_upper_bound,
        "spedas_agent_kit_extras": sorted(spedas_agent_kit_extras),
        "analysis_extra_enabled": "analysis" in spedas_agent_kit_extras,
        "entrypoint": entrypoint,
    }


# --- Cross-platform cache-path analysis (issue #5) -------------------------------
#
# These helpers are PURE: they take a raw configured value and an explicit
# environment mapping, and never touch the real process environment, the real
# filesystem, or the network. That makes them deterministic to unit-test on any OS
# while *simulating* another OS's environment (native Windows with USERPROFILE and
# no HOME, a missing HOME on POSIX, a literal unresolved ${HOME}, etc.). The runtime
# smoke and the offline ``--cache-diagnostics`` flag both build on them.

# A still-unresolved POSIX-style ``$VAR`` / ``${VAR}`` or Windows-style ``%VAR%``
# reference. If one of these survives expansion, the configured value reached the
# server as a literal token instead of a real path -> caching silently breaks.
_POSIX_VAR_RE = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*")
_WINDOWS_VAR_RE = re.compile(r"%[^%]+%")


def _expand_with(value: str, environ: dict[str, str]) -> str:
    """Expand both ``${VAR}``/``$VAR`` (POSIX) and ``%VAR%`` (Windows) forms against
    an explicit ``environ`` mapping.

    ``os.path.expandvars`` is platform-dependent (it only honours ``%VAR%`` on
    Windows and reads the live process env), which makes it useless for simulating
    another OS in a unit test. This does both syntaxes against the mapping we are
    handed, leaving any unknown variable as its literal token so the caller can
    flag it.
    """

    def _posix(match: "re.Match[str]") -> str:
        token = match.group(0)
        name = token[2:-1] if token.startswith("${") else token[1:]
        return environ.get(name, token)

    def _windows(match: "re.Match[str]") -> str:
        name = match.group(0)[1:-1]
        return environ.get(name, match.group(0))

    return _WINDOWS_VAR_RE.sub(_windows, _POSIX_VAR_RE.sub(_posix, value))


def analyze_cache_path(raw: str, environ: dict[str, str]) -> dict[str, Any]:
    """Analyse one configured cache-path string for cross-platform portability.

    Returns the raw value, the expanded value (against ``environ``), the list of
    variable tokens that did NOT resolve, whether the result still looks like an
    unresolved literal, whether it looks absolute, and any path-flavor caveats
    (mixed separators, a drive letter with forward slashes, a POSIX root that
    likely came from an unset ``HOME``). No filesystem or network access.
    """
    expanded = _expand_with(raw, environ)
    unresolved = _POSIX_VAR_RE.findall(expanded) + _WINDOWS_VAR_RE.findall(expanded)
    has_drive = bool(re.match(r"^[A-Za-z]:", expanded))
    has_backslash = "\\" in expanded
    has_forward = "/" in expanded
    looks_absolute = expanded.startswith("/") or has_drive or expanded.startswith("\\\\")

    caveats: list[str] = []
    if unresolved:
        caveats.append(
            "unresolved variable(s) "
            + ",".join(unresolved)
            + " — value reached the server as a literal, caching disabled"
        )
    if has_drive and has_forward and has_backslash:
        caveats.append(
            "mixed path separators on a Windows drive path — some C/Fortran/SPICE "
            "loaders reject '\\' mixed with '/'"
        )
    # A value that expanded to a leading-slash root with nothing before it usually
    # means ${HOME} expanded to empty (HOME unset on native Windows) -> wrong root.
    if not unresolved and not has_drive and expanded.startswith("/."):
        caveats.append(
            "path collapsed to a '/.<something>' root — a base variable likely "
            "expanded to empty (e.g. HOME unset on native Windows)"
        )

    return {
        "raw": raw,
        "expanded": expanded,
        "unresolved_vars": unresolved,
        "is_unresolved": bool(unresolved),
        "looks_absolute": looks_absolute,
        "path_flavor": {
            "has_drive_letter": has_drive,
            "has_backslash": has_backslash,
            "has_forward_slash": has_forward,
        },
        "caveats": caveats,
    }


# The cache/kernel variables the SPEDAS backends actually read (issue #5/#17). The
# offline diagnostic reports these from .mcp.json directly, no server start needed.
_CONFIGURED_CACHE_KEYS = (
    "XHELIO_CDAWEB_CACHE_DIR",
    "PDSMCP_CACHE_DIR",
    "XHELIO_SPICE_KERNEL_DIR",
)


def offline_cache_diagnostics(server: dict[str, Any], environ: dict[str, str]) -> dict[str, Any]:
    """Analyse the cache vars configured in ``.mcp.json`` against an environment,
    without starting the server, touching the disk, or fetching anything.

    This is the cheap cross-platform check (issue #5): it runs identically on
    ubuntu/macos/windows CI to prove how the packaged ``${HOME}/.cache/...`` values
    resolve on each OS, and flags any value that survived as an unresolved literal.
    ``environ`` is passed in so the same call can simulate native Windows (no HOME,
    has USERPROFILE) from any host OS.
    """
    configured = server.get("env") or {}
    if not isinstance(configured, dict):
        raise SystemExit("spedas MCP server env must be an object when present")
    per_var: dict[str, Any] = {}
    any_unresolved = False
    for key in _CONFIGURED_CACHE_KEYS:
        raw = configured.get(key)
        if not isinstance(raw, str):
            per_var[key] = {"configured": False}
            continue
        analysis = analyze_cache_path(raw, environ)
        analysis["configured"] = True
        any_unresolved = any_unresolved or analysis["is_unresolved"]
        per_var[key] = analysis
    return {
        "vars": per_var,
        "any_unresolved": any_unresolved,
        "note": (
            "offline: expands .mcp.json cache vars against the given environment; "
            "no server start, no filesystem write, no network"
        ),
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


def _run_cache_diagnostics(server: dict[str, Any], json_output: bool, report_only: bool = False) -> int:
    """Offline issue-#5 cache-path check against the current environment.

    Does NOT start the server, write to disk, or hit the network. Returns 0 when
    every configured cache var expanded to a real path (no unresolved literal),
    1 otherwise — unless ``report_only`` is set, in which case it always returns 0
    and only reports (per-OS CI evidence, where an unresolved ${HOME} on native
    Windows is expected, not a failure). This is the cheap check the CI wrapper
    matrix runs on every OS.
    """
    diag = offline_cache_diagnostics(server, os.environ.copy())
    resolved = not diag["any_unresolved"]
    ok = True if report_only else resolved
    if json_output:
        print(json.dumps(
            {"ok": ok, "resolved": resolved, "report_only": report_only,
             "configured_cache_diagnostics": diag},
            indent=2,
        ))
    else:
        if resolved:
            header = "OK"
        else:
            header = "UNRESOLVED (report-only)" if report_only else "FAIL"
        print(f"SPEDAS cache-path diagnostics (offline): {header}")
        for key, info in diag["vars"].items():
            if not info.get("configured"):
                print(f"  {key}: (not configured in .mcp.json)")
                continue
            print(f"  {key}:")
            print(f"    raw      : {info['raw']}")
            print(f"    expanded : {info['expanded']}")
            if info["is_unresolved"]:
                print(
                    "    UNRESOLVED: "
                    + ",".join(info["unresolved_vars"])
                    + " — value reached the server as a literal; caching disabled",
                    file=sys.stderr,
                )
            for caveat in info["caveats"]:
                if not info["is_unresolved"]:
                    print(f"    caveat   : {caveat}")
        if not resolved:
            msg = (
                "one or more cache paths did not resolve in this environment; "
                "set an absolute cache dir (see docs/configuration.md)"
            )
            if report_only:
                # Per-OS CI evidence: native Windows has no HOME, so the packaged
                # ${HOME} value is expected to be unresolved here. Report, don't fail.
                print(f"note (report-only): {msg}")
            else:
                print(msg, file=sys.stderr)
    return 0 if ok else 1


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
    parser.add_argument(
        "--cache-diagnostics",
        action="store_true",
        help=(
            "offline issue-#5 check: analyse how .mcp.json's cache vars expand in "
            "the CURRENT environment without starting the server, touching the disk, "
            "or fetching. Cheap enough to run on ubuntu/macos/windows CI. Exits "
            "non-zero if any configured cache path survived as an unresolved literal."
        ),
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "with --cache-diagnostics, always exit 0 and only REPORT the analysis. "
            "Use this for per-OS CI evidence gathering, where an unresolved ${HOME} "
            "on a native-Windows runner (HOME legitimately unset) is expected output, "
            "not a build failure."
        ),
    )
    args = parser.parse_args()

    server = _load_server_config()

    if args.cache_diagnostics:
        return _run_cache_diagnostics(
            server, json_output=args.json, report_only=args.report_only
        )

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

    missing = [name for name in BASE_EXPECTED_TOOLS if name not in tools]
    groups = _check_groups(tools)
    missing_groups = [name for name, info in groups.items() if not info["ok"]]
    groups_ok = args.skip_group_check or not missing_groups
    # Optional tiers are reported for visibility only; they never gate ``ok``.
    optional_tiers = _check_optional_tiers(tools)
    ok = not missing and groups_ok

    payload = {
        "ok": ok,
        "tool_count": len(tools),
        "tools": tools,
        "base_expected_tools": BASE_EXPECTED_TOOLS,
        "missing_base_tools": missing,
        "optional_tiers": optional_tiers,
        "tool_groups": groups,
        "missing_groups": missing_groups,
        "group_check_enforced": not args.skip_group_check,
        "command": [command, *command_args],
        "dependency_audit": dependency_audit,
        "cache_diagnostics": cache_diagnostics,
        # How the packaged .mcp.json cache vars expand in THIS (host) environment,
        # independent of the temp-isolation the smoke applies to its subprocess.
        # Surfaces an unresolved ${HOME} or a wrong root on the real OS (issue #5).
        "configured_cache_diagnostics": offline_cache_diagnostics(server, os.environ.copy()),
        "note": "initialize + tools/list only; no private credentials, interactive UI, data fetch, or SPICE kernel download",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"SPEDAS plugin MCP runtime smoke: {'OK' if payload['ok'] else 'FAIL'}")
        print(f"tool_count: {payload['tool_count']}")
        # Issue #3 audit trail: surface the configured source/pin in human mode too.
        da = dependency_audit
        print(f"spedas_agent_kit source: {da['from_arg']}")
        print(
            f"  pinned: {da['is_pinned']} (ref_kind={da['ref_kind']}, "
            f"resolved_commit={da['resolved_spedas_agent_kit_commit']})"
        )
        print(
            f"  mcp requirement: {da['mcp_requirement']} "
            f"(upper_bound={da['mcp_has_upper_bound']})"
        )
        print(
            "  extras: "
            f"{','.join(da['spedas_agent_kit_extras']) or '(none)'} "
            f"(analysis={da['analysis_extra_enabled']})"
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
        for tier, info in optional_tiers.items():
            # Optional tiers are informational only (never gate the exit code);
            # show which extras/gate flags this deployment unlocked.
            print(f"  optional {tier}: {info['status']} (unlock: {info['unlock']})")
        if missing:
            print("missing base tools: " + ", ".join(missing), file=sys.stderr)
        if missing_groups and not args.skip_group_check:
            print("incomplete tool groups: " + ", ".join(missing_groups), file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
