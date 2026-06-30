# Fetch & kernel safety boundary

This plugin exposes the SPEDAS Agent Kit MCP primary surface (13 base tools at the pinned
`spedas_agent_kit` commit) with optional analysis tools owned by the Agent Kit core and not requested by default.
Some tools perform **real network downloads**:
mission data products and SPICE kernels. This document defines the safety
boundary, the opt-in language to use, and what to verify before approving real
fetches. It addresses issue #6 (fetch/kernel safety) and is the runbook for the
enabled default `hooks/hooks.json` guard.

> **Caveat:** the tools and their fetch/kernel behavior live in the upstream
> `spedas_agent_kit` server, which `.mcp.json` now resolves from a **pinned commit**
> (`48dc50d9c31ba608019c8ea3ac3d72ac2b5158b8`). The pin makes the tool surface
> stable per install; re-verify this boundary whenever you **bump** the pin, since
> a new commit can alter what counts as a fetch/kernel tool (see
> [`COMPATIBILITY.md`](../COMPATIBILITY.md) and [`dependencies.md`](dependencies.md)).

## The boundary: discovery is safe, fetch is opt-in

| Always safe (metadata/planning) | Opt-in (network, can be large) |
|---|---|
| `spedas_overview`, `search_spedas_data_sources`, `plan_spedas_observation`, `compare_cdaweb_pds_spice`, `create_spedas_analysis_bundle` | `fetch_data_product` (unified) |
| `browse_data_sources`, `load_data_source`, `browse_data_parameters` | `fetch_data_product` (CDAWeb/PDS unified data fetch) |
| `get_ephemeris`, `compute_distance`, `transform_coordinates` with cached kernels / confirmation responses | the same geometry tools with `allow_kernel_download=True` — SPICE kernels are often 100 MB–1+ GB each |
| `manage_data_cache(source_type=..., action="status")` | `fetch_hapi_data`, `fetch_fdsn_data`, or cache cleanup actions such as `manage_data_cache(source_type=..., action="clean")` |

**Default posture:** stay in the left column until the user (or task) explicitly
authorizes a fetch. CDAWeb/PDS enforce rate limits; a careless wide request (e.g.
"all solar-wind data for 2023") can trigger multi-gigabyte downloads or HTTP 429 IP
throttling. This plugin's smoke paths and default examples are all
metadata/planning only — no real fetch, no kernel download.

## Opt-in language

Before any tool in the right column, confirm in plain language and record it in
provenance (`request.json` `allowed_side_effects`). Use wording like:

> "I'm about to fetch real data. Source: `cdaweb`, dataset `MMS1_FGM_SRVY_L2`, time
> range `2015-10-16T13:06Z–13:08Z`, cache root `~/.cache/spedas/cdaweb`. This is a
> network download subject to archive rate limits. OK to proceed?"

For SPICE:

> "This needs SPICE kernel(s) that are not in the cache yet; loading them will
> download ~N MB to `~/.cache/spedas/spice/kernels`. OK to download, or should I
> stay metadata-only?"

Do **not** widen a time range, add probes, or escalate from one dataset to "all"
without a fresh confirmation.

## Before you approve real fetches (checklist)

1. **Plan first.** Run the planning/browse tools and confirm dataset id, parameters,
   and the *narrowest* useful time range.
2. **Pick and verify the cache root.** Confirm `XHELIO_CDAWEB_CACHE_DIR` /
   `PDSMCP_CACHE_DIR` / `XHELIO_SPICE_KERNEL_DIR` resolve to a writable directory
   (see [`configuration.md`](configuration.md)). A misconfigured cache means every
   run re-downloads — the fastest way to get rate-limited.
3. **Estimate size.** For SPICE especially, prefer the smallest kernel set; check
   `manage_data_cache(source_type="spice", action="status")` for what is already cached.
4. **Get explicit opt-in** using the language above and record it.
5. **Start a provenance run directory** from [`../templates/provenance/`](../templates/provenance/)
   so the fetch and its outputs are recorded.

## Enforcement plan & `hooks/hooks.json`

`hooks/hooks.json` now ships an **enabled-by-default `PreToolUse` safety gate** for
issue #6. The hook matches real data-fetch tools and kernel-download-capable geometry
calls, then returns a Claude Code hook response with `permissionDecision: "ask"` so
the call pauses for explicit permission before network or kernel side effects proceed.

The default guard is deliberately narrow:

- metadata/planning/search/status tools remain quiet;
- `fetch_data_product`, `fetch_hapi_data`, `fetch_fdsn_data`, and legacy fetch names
  ask before downloading archive data;
- `get_ephemeris`, `compute_distance`, and `transform_coordinates` ask only when
  `allow_kernel_download: true` is present;
- legacy `manage_spice_kernels` asks for mutating/download actions, but read-only
  status/list actions stay quiet.

Before approving a guarded call, confirm the science question, exact dataset/source
or SPICE target, UTC time span, cache/output location, and provenance plan. If the
hook reports a wide time range, narrow the window or run metadata/browse/discovery
first. For source-specific fetches, prefer the unified `fetch_data_product` workflow
unless the source-specific tool is necessary.

The posture is machine-checked by
[`../hooks/default_posture.json`](../hooks/default_posture.json),
[`../hooks/fetch_guard.py`](../hooks/fetch_guard.py),
[`../scripts/test_fetch_guard.py`](../scripts/test_fetch_guard.py), and
`../scripts/validate_plugin.py`. CI fails if the default hook goes empty, loses the
`PreToolUse` matcher, stops invoking the guard script, or drops one of the guarded
tool names.

If a local installation wants a different posture, edit `hooks/hooks.json` locally;
for the repository default, keep the issue #6 guard enabled.

## See also

- [`configuration.md`](configuration.md) — cache/kernel directories the fetches write to.
- [`../skills/spedas-workflow/SKILL.md`](../skills/spedas-workflow/SKILL.md) — the metadata-first default workflow.
- [`../skills/spedas-workflow/reference/troubleshooting.md`](../skills/spedas-workflow/reference/troubleshooting.md) — rate limits, 429s, kernel/network failures.
- [`../templates/provenance/`](../templates/provenance/) — record what you fetched and why.
