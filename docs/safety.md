# Fetch & kernel safety boundary

This plugin exposes the full SPEDAS MCP tool surface (26 tools), including tools
that perform **real network downloads**: mission data products and SPICE kernels.
This document defines the safety boundary, the opt-in language to use, and what to
do before enabling real fetches. It addresses issue #6 (fetch/kernel safety) and is
the runbook the (currently intentional-empty) `hooks/hooks.json` plan refers to.

## The boundary: discovery is safe, fetch is opt-in

| Always safe (metadata/planning) | Opt-in (network, can be large) |
|---|---|
| `spedas_overview`, `search_spedas_data_sources`, `plan_spedas_observation`, `compare_cdaweb_pds_spice`, `create_spedas_analysis_bundle` | `fetch_data_product` (unified) |
| `browse_data_sources`, `load_data_source`, `browse_data_parameters` | `fetch_data` (CDAWeb backend) |
| `list_spice_missions`, `list_coordinate_frames`, `get_ephemeris`, `compute_distance`, `transform_coordinates` (using already-present kernels) | `fetch_pds_data` (PDS backend) |
| `manage_data_cache(action="status")`, `manage_spice_kernels(action="status")` | `manage_spice_kernels(action="load"/download paths)` — SPICE kernels are often 100 MB–1+ GB each |

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

## Before you enable real fetches (checklist)

1. **Plan first.** Run the planning/browse tools and confirm dataset id, parameters,
   and the *narrowest* useful time range.
2. **Pick and verify the cache root.** Confirm `XHELIO_CDAWEB_CACHE_DIR` /
   `PDSMCP_CACHE_DIR` / `XHELIO_SPICE_KERNEL_DIR` resolve to a writable directory
   (see [`configuration.md`](configuration.md)). A misconfigured cache means every
   run re-downloads — the fastest way to get rate-limited.
3. **Estimate size.** For SPICE especially, prefer the smallest kernel set; check
   `manage_spice_kernels(action="status")` for what is already cached.
4. **Get explicit opt-in** using the language above and record it.
5. **Start a provenance run directory** from [`../templates/provenance/`](../templates/provenance/)
   so the fetch and its outputs are recorded.

## Enforcement plan & `hooks/hooks.json`

`hooks/hooks.json` ships as an **intentional empty placeholder** (`{"hooks": []}`).
This is a deliberate, documented choice, not a regression — the validator asserts it
stays a valid placeholder so an accidental malformed hook fails CI.

We do **not** ship an active `PreToolUse` gate by default because a hook that blocks
or rewrites tool calls changes the user's runtime behavior, and this plugin should
not mutate that behavior without the user opting in. Instead:

- The **prose discipline above** is the default boundary (the skill and commands
  teach metadata-first, plan-before-fetch).
- Per-CLI you can scope tools explicitly with `--allowedTools` (see the README's
  "safe first live CLI check"): allow only discovery/planning tools for a dry run.
- For users who *want* a runtime gate, a ready-to-enable example hook is provided —
  **disabled by default** — at
  [`../hooks/examples/pretooluse-fetch-guard.md`](../hooks/examples/pretooluse-fetch-guard.md).
  It matches the fetch/kernel tools and warns before they run. Copy it into
  `hooks/hooks.json` *only if you want it*; read its caveats first.

If a future version ships an active gate, it must be opt-in (off by default) and
documented here.

## See also

- [`configuration.md`](configuration.md) — cache/kernel directories the fetches write to.
- [`../skills/spedas-workflow/SKILL.md`](../skills/spedas-workflow/SKILL.md) — the metadata-first default workflow.
- [`../skills/spedas-workflow/reference/troubleshooting.md`](../skills/spedas-workflow/reference/troubleshooting.md) — rate limits, 429s, kernel/network failures.
- [`../templates/provenance/`](../templates/provenance/) — record what you fetched and why.
