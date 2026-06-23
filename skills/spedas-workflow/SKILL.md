---
name: spedas-workflow
description: Use SPEDAS MCP to discover heliophysics data sources, plan observations, fetch compact data products, and keep provenance/artifacts explicit.
---

# SPEDAS workflow skill

Use this skill when a user asks Claude Code or Codex to work with SPEDAS, PySPEDAS,
CDAWeb, PDS, SPICE geometry, or multi-mission heliophysics data discovery.

## Mental model

Treat `spedas_mcp` as one SPEDAS interface, not as three unrelated backend MCPs.
The public structure is:

1. **Science workflow layer** — formulate and compare analysis plans.
2. **Unified data layer** — browse/load/fetch/manage data by `source_type`.
3. **Data-source categories** — `cdaweb`, `pds`, `spice`.
4. **Internal backends** — `xhelio-cdaweb`, `xhelio-pds`, `xhelio-spice` are implementation details.

## Preferred MCP tools

Start with:

- `spedas_overview` — learn available layers/tools.
- `search_spedas_data_sources` — search likely CDAWeb/PDS/SPICE sources for a science query.
- `plan_spedas_observation` — turn a target/interval/phenomenon into an observation plan.
- `compare_cdaweb_pds_spice` — decide which archive/source type is appropriate.
- `create_spedas_analysis_bundle` — create a reusable plan/provenance scaffold.

Then use the unified data layer:

- `browse_data_sources(source_type="all"|"cdaweb"|"pds"|"spice")`
- `load_data_source(source_type, source_id)`
- `browse_data_parameters(source_type, dataset_id, ...)`
- `fetch_data_product(source_type, ...)`
- `manage_data_cache(source_type, action, ...)`

Compatibility/low-level tools may exist for CDAWeb/PDS/SPICE, but prefer the unified
`data_*` tools unless debugging or maintaining the MCP itself.

## Artifact discipline

- Do not paste large arrays, full CDF contents, or long tplot dumps into chat.
- Prefer artifact paths, compact summaries, hashes, variable names, time ranges, and provenance.
- For real downloads, use narrow time intervals first and say whether the call is networked.
- Preserve cache/output directories in a predictable project-local or user-cache location.

## Failure handling

When a tool fails, classify the failure before retrying:

- **MCP/tool bug** — wrong argument schema, impossible route, serialization issue.
- **Backend data gap** — dataset metadata missing, archive label incomplete, unsupported mission.
- **External-service limitation** — network timeout/rate limit/remote archive unavailable.
- **Documentation gap** — tool can work but names/arguments do not tell the agent what to do.

Report exact tool name, arguments, error text, time range, and source_type.
