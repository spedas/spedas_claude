# Troubleshooting runbook & failure taxonomy

This is the actionable form of the five-class failure taxonomy in `SKILL.md`
(issue #13). For each class it gives representative signals, a quick decision flow,
diagnostic commands, where to file the issue, and which provenance artifacts to
attach. The goal: classify a new error in under a minute and route it to the right
repo with the right evidence.

## Quick decision tree

```
Error appears
│
├─ Server never started / "command not found: uvx" / no tools listed
│      └─► A. MCP wrapper / startup issue        (file: spedas_claude)
│
├─ Server started, a TOOL returned an error or wrong shape
│   ├─ message is about params/planning/source mapping/unknown source_type
│   │      └─► B. SPEDAS Agent Kit MCP tool issue           (file: spedas_agent_kit)
│   ├─ message is "no such variable / dataset / kernel / missing PDS label"
│   │      └─► C. Backend / data gap              (file: backend archive or spedas_agent_kit)
│   └─ message is timeout / HTTP 429 / connection reset / archive down
│          └─► D. External service limit          (no bug to file; retry/narrow)
│
└─ Everything "works" but the instructions/method were unclear or wrong
       └─► E. Docs / skills gap                    (file: spedas_claude or spedas_agent_kit)
```

First triage command for A vs. B/C: run the offline validator and the runtime
smoke (below). If the smoke can't even list tools, you are in class A. If it lists
17 base tools cleanly but a real call fails, you are in B/C/D.

```bash
python3 scripts/validate_plugin.py            # packaging/layout only (offline)
python3 scripts/smoke_mcp_runtime.py --json   # starts the real server, lists tools
```

---

## A. MCP wrapper / startup issue → file in `spedas_claude`

The plugin config or process startup is wrong; you usually see this *before* any
science tool runs.

| Signal | Likely cause | Fix |
|---|---|---|
| `command not found: uvx` | `uv` not installed / not on `PATH` | install `uv` via the official uv installation guide (https://docs.astral.sh/uv/getting-started/installation/); reopen shell |
| Smoke hangs/times out on first run | `uvx` resolving the pinned `spedas_agent_kit` commit from GitHub with no/blocked network | allow network for first run; raise `--timeout`; pre-warm (`uvx --with 'mcp>=1.26.0,<2' --from git+https://github.com/spedas/spedas_agent_kit.git@e504dae10f428bfc2f67dd0c3fcdb9d8613b0d40 spedas-agent-kit --help`, matching `.mcp.json`) |
| `Failed to spawn` / `Permission denied` writing cache or temp | `UV_CACHE_DIR` / `XDG_CACHE_HOME` / `TMPDIR` or a cache dir is read-only / over quota | point them at a writable path ([`configuration.md`](../../../docs/configuration.md)); the smoke auto-falls-back, real runs do not |
| `No solution found` / cannot resolve `spedas_agent_kit` | wrong/inaccessible `--from` URL, or a pinned ref that no longer exists | restore the official URL in `.mcp.json`; re-check any `@ref` pin |
| `missing_base_tools` non-empty in the smoke | resolved `spedas_agent_kit` HEAD changed its base tool surface | confirm/pin a known-good `spedas_agent_kit` ref ([`dependencies.md`](../../../docs/dependencies.md)) |
| Claude Code doesn't show the slash commands/skill | plugin dir not enabled, or resources not at the plugin root | re-enable the plugin dir; run `validate_plugin.py` to confirm the layout/resource paths |
| `validate_plugin.py`: a declared path does not resolve | a resource moved/renamed but `.claude-plugin/plugin.json` still points at the old path | correct the path key (paths are plugin-root-relative) or move the resource |
| `ModuleNotFoundError: No module named 'pyspedas'` | the **PySPEDAS layer is not installed** — separate from the MCP layer | not an MCP bug: `pip install pyspedas` in *your* Python env (see README "Architecture: two independent layers") |

**Attach:** `environment.txt` (uv/uvx version, OS, resolved `spedas_agent_kit` commit),
the exact `.mcp.json` `command`/`args`, and the smoke's JSON output.
**File at:** https://github.com/spedas/spedas_claude/issues

## B. SPEDAS Agent Kit MCP tool issue → file in `spedas_agent_kit`

The server runs and lists tools, but a tool's *behavior* is wrong: bad parameter
mapping, planning semantics, an unexpected error shape, or `unknown source_type`.

| Signal | Likely cause |
|---|---|
| `unknown source_type: ...` | passed a `source_type` outside `cdaweb`/`pds`/`spice` |
| `SPICE is geometry/ephemeris, not a measurement product fetch` | called `fetch_data_product(source_type="spice")` — use `get_ephemeris`/`compute_distance`/`transform_coordinates` |
| `fetch_data_product` rejects `limit` for PDS | PDS path doesn't support `limit`; narrow `start`/`stop`/`parameters` |
| Planning/compare tool returns an unexpected/empty shape | tool-side logic in `spedas_agent_kit` |

Isolate facade vs. backend: if the unified tool misbehaves, try the equivalent
backend tool (see [`backend-compatibility.md`](backend-compatibility.md)). If the
backend tool works and the facade doesn't, the bug is in the facade layer.

**Attach:** the exact tool name + arguments (from `tool_calls.jsonl`), the returned
JSON, and the resolved `spedas_agent_kit` commit.
**File at:** https://github.com/spedas/spedas_agent_kit/issues

## C. Backend / data gap → file at the backend archive (or `spedas_agent_kit`)

The tool worked but the *data* is missing or incomplete at the source.

| Signal | Source | Note |
|---|---|---|
| "no such variable" / empty parameter list for a known dataset | CDAWeb | confirm the dataset id and variable names with `browse_data_parameters` first; the CDAWeb backend bootstraps bundled observatory + metadata into its cache on first access — a stale/empty cache can look like a gap |
| Missing/partial PDS label or metadata fields | PDS | PDS labels vary by dataset; record the gap, don't treat it as user error |
| Kernel not available for a target/time | SPICE | the needed kernel isn't cached or published; see class D if it's a download failure |

**Attach:** `provenance.md` (dataset/product id, time range, the exact missing
field) plus `tool_calls.jsonl`. For CDAWeb cache-bootstrap suspicion, include the
cache root and whether it was writable.
**File at:** the relevant archive (CDAWeb/PDS/NAIF) — or `spedas_agent_kit` if you think
the backend mishandled present data.

## D. External service limit → usually no bug to file

Transient network/archive conditions.

| Signal | Action |
|---|---|
| `HTTP 429` / "Too Many Requests" | you're rate-limited; stop, wait, and **narrow** the request. A misconfigured cache (re-downloading every run) is the usual root cause — verify the cache dir ([`configuration.md`](../../../docs/configuration.md)) |
| Connection timeout / reset, archive 5xx | retry later; raise client timeouts; the archive may be down |
| Kernel download fails mid-transfer | re-run; confirm `XHELIO_SPICE_KERNEL_DIR` is writable and has space |

**Attach (only if it recurs and looks systemic):** timestamps, the request, and the
HTTP status. Otherwise this is operational, not a bug.
**File at:** the relevant archive (CDAWeb/PDS/NAIF) if an outage/limit is systemic;
or https://github.com/spedas/spedas_agent_kit/issues if the limit *handling itself* (retry,
backoff, error shape) looks wrong.

## E. Docs / skills gap → file in `spedas_claude` (or `spedas_agent_kit`)

The tool works but the instructions or scientific method were unclear, missing, or
wrong. This is a real, fileable class — first-user friction is a defect.

**Attach:** which doc/skill/command misled you and what you expected.
**File at:** `spedas_claude` for plugin docs/skill/command issues; `spedas_agent_kit` for
tool-description/semantic doc issues.

---

## Provenance evidence by class (what to attach)

The provenance bundle ([`artifact-provenance.md`](artifact-provenance.md),
templates in [`templates/provenance/`](../../../templates/provenance/)) makes a bug
report actionable. Most-valuable file per class:

| Class | Most valuable artifact(s) |
|---|---|
| A. MCP wrapper / startup | `environment.txt` (uv/uvx + resolved `spedas_agent_kit` commit), `.mcp.json`, smoke JSON |
| B. SPEDAS Agent Kit MCP tool | `tool_calls.jsonl` (exact args) + returned JSON + `spedas_agent_kit` commit |
| C. Backend / data gap | `provenance.md` (dataset id, time range, missing field) + `tool_calls.jsonl` |
| D. External service limit | timestamps + request + HTTP status (only if systemic) |
| E. Docs / skills gap | the misleading doc reference + expected-vs-actual |

The single field that unblocks A/B/C fastest is the **resolved `spedas_agent_kit`
commit** — capture it (see [`dependencies.md`](../../../docs/dependencies.md) and
`capture_environment.sh`).
