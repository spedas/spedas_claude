# Geometry and SPICE tools

The SPEDAS MCP exposes six dedicated geometry/SPICE tools. They answer
*"where was the spacecraft / which way does this vector point"* questions —
ephemerides, distances, coordinate-frame transforms — separately from the
measurement-data layer. This document names the real tools, shows safe examples,
and draws the line between **metadata/planning** (cheap, no download) and
**kernel/data downloads** (gated, opt-in).

Tool names and arguments match the live `spedas_mcp` schemas (verify with
`python3 scripts/smoke_mcp_runtime.py --json`).

## The six geometry/SPICE tools

| Tool | Required args | Touches network? | Purpose |
|---|---|---|---|
| `list_spice_missions` | — | metadata | List supported spacecraft/bodies with NAIF IDs and kernel status. |
| `list_coordinate_frames` | — | metadata | List supported coordinate frames and usage notes. |
| `get_ephemeris` | `target`, `time` | may load kernels | Single-time state inline, or a timeseries trajectory written to CSV. |
| `compute_distance` | `target1`, `target2`, `time_start`, `time_end` | may load kernels | Distance between two targets over a time range. |
| `transform_coordinates` | `vector`, `time`, `from_frame`, `to_frame` | may load kernels | Transform a 3D vector between SPICE frames. |
| `manage_spice_kernels` | `action` | yes for download/clean | Inspect/list/clean kernels; the explicit kernel-download surface. |

**Routing rule:** SPICE *geometry* goes through these tools, **not** through
`fetch_data_product`. `fetch_data_product` is for CDAWeb/PDS measurement
products; it deliberately routes SPICE requests here.

## Metadata/planning first (no downloads)

Start every geometry task with the two list tools. They never download kernels
and are safe in any sandbox:

```jsonc
list_spice_missions()        // -> supported targets, NAIF IDs, which kernels are present
list_coordinate_frames()     // -> frame names (e.g. ECLIPJ2000, J2000, IAU_*, mission frames) + notes
```

Use the results to confirm that your target and frames are supported, and to see
whether the needed kernels are already cached, **before** requesting any geometry
that may trigger a kernel load.

## Ephemeris: single time vs. timeseries

`get_ephemeris` has two modes. A single-time query returns the state inline (a
small object — safe to read in chat). A timeseries query (`time_end` + `step`
set) writes a CSV artifact instead of inlining a large array.

```jsonc
// Single-time state, inline (safe, small):
get_ephemeris(
  target="PSP",
  time="2021-11-21T08:00:00Z",
  frame="ECLIPJ2000",     // default "ECLIPJ2000"
  observer="SUN"          // default "SUN"
)

// Timeseries trajectory -> CSV artifact (note output_file + time_end + step):
get_ephemeris(
  target="PSP",
  time="2021-11-21T00:00:00Z",
  time_end="2021-11-22T00:00:00Z",   // presence of time_end makes it a timeseries
  step="1h",                          // default "1h"
  frame="ECLIPJ2000",
  observer="SUN",
  output_file="/tmp/spedas-geom/psp_traj.csv"
)
```

Returns: the inline state (single-time) or the CSV path plus row/step summary
(timeseries) — never a dumped array. Choose a coarse `step` and a narrow span for
a first look.

## Distance between two targets

```jsonc
compute_distance(
  target1="PSP",
  target2="SUN",
  time_start="2021-11-21T00:00:00Z",
  time_end="2021-11-22T00:00:00Z",
  step="1h"               // default "1h"
)
```

Returns: a compact distance summary (e.g. min/max/at-times) over the range. Keep
the range short and the step coarse to avoid large outputs and unnecessary kernel
coverage.

## Coordinate transforms

```jsonc
transform_coordinates(
  vector=[1.0, 0.0, 0.0],
  time="2015-10-16T13:06:00Z",
  from_frame="GSE",
  to_frame="GSM",
  spacecraft="MMS1"        // optional, default null; needed for spacecraft-relative frames
)
```

Returns: the transformed 3D vector (small, inline). Use `list_coordinate_frames`
first to confirm both `from_frame` and `to_frame` are supported.

## Kernels: the gated download surface

`manage_spice_kernels` is where kernel inspection and downloads are explicit.
Start with a read-only `status`/`list` action; only request a download with a
clear scope and after confirming cache location.

```jsonc
manage_spice_kernels(action="status")                         // read-only inventory
manage_spice_kernels(action="list", mission="PSP")            // what PSP kernels exist/are cached
// Downloads are explicit and scoped — confirm before running:
manage_spice_kernels(action="download", mission="PSP",
                     filenames=["spk_psp_xxx.bsp"])            // example; gate on user intent
```

Returns: kernel inventory/status, or the result of the requested action.
**Avoid large kernel downloads without confirming cache directory and scope.**
The runtime smoke and validators never trigger downloads.

For *data-layer* cache status of the SPICE source (sizes/locations), you can also
use the unified `manage_data_cache(source_type="spice", action="status")`; use
`manage_spice_kernels` for kernel-specific inspection/maintenance.

## Safe geometry walkthrough (no downloads)

```jsonc
list_spice_missions()
list_coordinate_frames()
get_ephemeris(target="PSP", time="2021-11-21T08:00:00Z")     // single-time, inline
compute_distance(target1="PSP", target2="SUN",
                 time_start="2021-11-21T00:00:00Z",
                 time_end="2021-11-21T06:00:00Z", step="1h")
transform_coordinates(vector=[1,0,0], time="2021-11-21T08:00:00Z",
                      from_frame="ECLIPJ2000", to_frame="J2000")
manage_spice_kernels(action="status")
```

Each call above is metadata/geometry only. Kernel downloads happen only via an
explicit `manage_spice_kernels(action="download", …)` you choose to run.
