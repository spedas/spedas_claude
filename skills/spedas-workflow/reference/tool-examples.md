# SPEDAS Agent Kit MCP tool examples (arguments and return shapes)

Concrete, copy-ready argument examples for the SPEDAS Agent Kit MCP tools, with notes on
what each call returns and which calls touch the network. This covers the
**unified public facade** — the science workflow tools and the unified data
layer. For source-specific (CDAWeb/PDS/SPICE) low-level tools, see
[`backend-compatibility.md`](backend-compatibility.md); for geometry/SPICE
tools, see [`geometry-spice.md`](geometry-spice.md).

Arguments below match the pinned `spedas_agent_kit` tool schemas (17 base tools as of this
writing; verify with `python3 scripts/smoke_mcp_runtime.py --json`). Optional
arguments show their schema default. **Only fetch tools download measurement data**. SPICE kernel downloads happen only when geometry calls explicitly set `allow_kernel_download=True`; examples here otherwise stay metadata/planning-safe.

> Notation: `tool(args…)` is the MCP tool call. In Claude Code the underlying
> tool id is `mcp__spedas__<tool>`. Times are ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`)
> or PySPEDAS-style (`2015-10-16/13:06`); the server accepts both.

---

## Workflow layer (plan before you load)

### `spedas_overview()`

No arguments. Always call this first in a new session.

```jsonc
spedas_overview()
```

Returns: a structured description of the MCP capability layers (workflow,
unified data, geometry/SPICE, compatibility) and the recommended call order. Use
it to decide the next one or two tools — no network, no data.

### `search_spedas_data_sources(question, target?, observables?)`

Recommends whether a request should start with CDAWeb, PDS, SPICE, or a mix.

```jsonc
search_spedas_data_sources(
  question="magnetopause crossing fields and plasma for MMS",
  target="MMS1",                       // optional, default null
  observables=["B", "Ni", "Vi"]        // optional list, default null
)
```

Returns: a recommendation object naming candidate `source_type` categories and a
short rationale per source. Metadata only — no datasets are fetched.

### `plan_spedas_observation(science_goal, start?, stop?, target?, observables?, data_sources?)`

The main planning tool. Only `science_goal` is required.

```jsonc
plan_spedas_observation(
  science_goal="Identify magnetopause crossing signatures",
  start="2015-10-16T13:00:00Z",        // optional
  stop="2015-10-16T13:10:00Z",         // optional
  target="MMS1",                       // optional
  observables=["B", "ion moments"],    // optional list
  data_sources=["cdaweb", "spice"]     // optional; omit to let the planner choose
)
```

Returns: a plan describing recommended `source_type`(s), candidate
datasets/parameters, the interval, and the geometry-vs-measurement split. It does
**not** fetch data or download kernels — it tells you which tools to call next.

### `compare_cdaweb_pds_spice(science_goal?)`

```jsonc
compare_cdaweb_pds_spice(
  science_goal="Juno magnetic field near Jupiter with geometry context"
)
```

Returns: a comparison of the three archive roles for the stated goal (what each
provides, what it cannot). Use when the archive choice is ambiguous. No fetch.

### `create_spedas_analysis_bundle(study_name, output_dir, science_goal?, target?, start?, stop?, data_sources?)`

Writes a small request/provenance scaffold to disk (an artifact, per the
artifact-first rule) — it does **not** load science data.

```jsonc
create_spedas_analysis_bundle(
  study_name="mms_magnetopause_20151016",
  output_dir="/tmp/spedas-studies/mms_mp",   // required: where the bundle is written
  science_goal="Magnetopause crossing characterization",
  target="MMS1",
  start="2015-10-16T13:00:00Z",
  stop="2015-10-16T13:10:00Z",
  data_sources=["cdaweb", "spice"]
)
```

Returns: the bundle path(s) and a summary of the recorded request/plan. Files
land under `output_dir`. Safe to call; the only side effect is writing the
scaffold.

---

## Unified data layer (browse → load → browse params → fetch → cache)

These take a `source_type` of `"cdaweb"`, `"pds"`, or `"spice"` instead of
source-specific tool names. This is the **preferred** surface for new workflows.

### `browse_data_sources(source_type?, query?)`

```jsonc
browse_data_sources(source_type="all")                 // default: all categories
browse_data_sources(source_type="cdaweb", query="MMS") // optional text filter
```

Returns: a compact catalog of source categories / observatories / missions
matching the filter. Metadata only.

### `load_data_source(source_type, source_id)`

```jsonc
load_data_source(source_type="cdaweb", source_id="MMS1")
load_data_source(source_type="pds",    source_id="JUNO")
load_data_source(source_type="spice",  source_id="PSP")
```

Returns: scoped context for that observatory/mission (available
datasets/instruments, hints, relevant frames for SPICE). No measurement data is
loaded — this is a context/prompt load, mirroring the xhelio `load_*` pattern.

### `browse_data_parameters(source_type, dataset_id, dataset_ids?)`

```jsonc
browse_data_parameters(
  source_type="cdaweb",
  dataset_id="MMS1_FGM_SRVY_L2"
)
// or several datasets at once (use dataset_ids instead of dataset_id):
browse_data_parameters(
  source_type="cdaweb",
  dataset_ids=["MMS1_FGM_SRVY_L2", "MMS1_FPI_FAST_L2_DIS-MOMS"]
)
```

Returns: the variable/parameter list and metadata (names, units, descriptions)
for the dataset(s). Use it to confirm exact parameter names **before** any fetch.
Metadata only.

### `fetch_data_product(source_type, dataset_id, parameters, start?, stop?, output_dir?, format?, limit?)` — opt-in download

**This is the one unified tool that downloads data.** Treat it as opt-in: call it
only when the user/task explicitly wants real data, with a narrow interval and an
explicit `output_dir`.

```jsonc
fetch_data_product(
  source_type="cdaweb",
  dataset_id="MMS1_FGM_SRVY_L2",
  parameters=["mms1_fgm_b_gse_srvy_l2"],
  start="2015-10-16T13:05:00Z",
  stop="2015-10-16T13:08:00Z",
  output_dir="/tmp/spedas-fetch/mms_fgm",
  format="csv",        // default "csv"
  limit=null           // optional row cap for a smoke-sized pull
)
```

Returns: artifact paths plus stats/metadata (rows, files, size) — **not** the raw
arrays. SPICE geometry is *not* fetched here; it is routed to the geometry tools
(see [`geometry-spice.md`](geometry-spice.md)). Keep windows minutes-wide for a
first pull and expect public-archive rate limits.

### `manage_data_cache(source_type?, action?, cache_dir?, mission?)`

```jsonc
manage_data_cache(source_type="all", action="status")   // defaults shown
manage_data_cache(source_type="cdaweb", action="status")
```

Returns: cache status (sizes, locations) or the result of a maintenance action by
source. `action` defaults to `"status"`, which is read-only. Confirm scope before
any destructive action.

---

## A safe, no-fetch session walkthrough

```jsonc
spedas_overview()
search_spedas_data_sources(question="MMS magnetopause fields/plasma", target="MMS1")
plan_spedas_observation(
  science_goal="Characterize a magnetopause crossing",
  start="2015-10-16T13:00:00Z", stop="2015-10-16T13:10:00Z",
  target="MMS1", data_sources=["cdaweb", "spice"])
browse_data_sources(source_type="cdaweb", query="MMS")
load_data_source(source_type="cdaweb", source_id="MMS1")
browse_data_parameters(source_type="cdaweb", dataset_id="MMS1_FGM_SRVY_L2")
manage_data_cache(source_type="all", action="status")
// STOP here unless real data is explicitly wanted. Only then:
// fetch_data_product(source_type="cdaweb", dataset_id="MMS1_FGM_SRVY_L2",
//   parameters=["mms1_fgm_b_gse_srvy_l2"],
//   start="2015-10-16T13:05:00Z", stop="2015-10-16T13:08:00Z",
//   output_dir="/tmp/spedas-fetch/mms_fgm")
```

Everything above the `STOP` line is metadata/planning only and safe to run in any
sandbox. Dataset/parameter ids in these examples are illustrative — confirm the
exact ids with `browse_data_sources` / `browse_data_parameters` before fetching.
