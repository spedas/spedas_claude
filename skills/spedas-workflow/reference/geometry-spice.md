# Geometry and SPICE tools

The current pinned `spedas_mcp` base surface exposes three public geometry/SPICE
tools:

- `get_ephemeris`
- `compute_distance`
- `transform_coordinates`

They answer *"where was the spacecraft / which way does this vector point"*
questions separately from the measurement-data layer. SPICE discovery/cache
context is routed through the unified data facade, not through legacy hidden
list/manage tools. Verify the installed surface with
`python3 scripts/smoke_mcp_runtime.py --json` (this wrapper pins
`spedas_mcp` `5ac9e2087ca7522bff45386c3a8d308e3d9d92b3`).

## Public routing

| Need | Public tool(s) | Notes |
|---|---|---|
| Overview / supported source families | `spedas_overview()` and `browse_data_sources(source_type="spice")` | Metadata/planning only. |
| SPICE source context / cache state | `load_data_source(source_type="spice", source_id=...)`, `browse_data_parameters(source_type="spice", ...)`, `manage_data_cache(source_type="spice", action="status")` | Use the unified facade for discovery/status. |
| Ephemeris / state vector | `get_ephemeris(target, time, ...)` | Single-time state inline; timeseries writes a CSV artifact when `output_file` is set. |
| Distance over time | `compute_distance(target1, target2, time_start, time_end, ...)` | Keep ranges narrow and steps coarse until you know the need. |
| Frame transform | `transform_coordinates(vector, time, from_frame, to_frame, spacecraft?)` | Returns a compact transformed vector. |

**Routing rule:** SPICE *geometry* goes through the geometry tools above, **not**
through `fetch_data_product`. Measurement-data fetches remain CDAWeb/PDS/HAPI/FDSN
workflows.

## Kernel/download boundary

Geometry calls may require SPICE kernels. The current server is guarded: if needed
kernels are absent and `allow_kernel_download` is false, the call returns a
`kernel_download_required` / confirmation-style response instead of silently
downloading 100 MB--1+ GB files. Only pass `allow_kernel_download=True` after
confirming cache directory, mission/time scope, and user opt-in.

For read-only cache status use:

```jsonc
manage_data_cache(source_type="spice", action="status")
```

For cleanup, keep scope explicit:

```jsonc
manage_data_cache(source_type="spice", action="clean", mission="PSP")
```

## Ephemeris: single time vs. timeseries

```jsonc
// Single-time state, inline (safe/compact if kernels are already cached):
get_ephemeris(
  target="PSP",
  time="2021-11-21T08:00:00Z",
  frame="ECLIPJ2000",
  observer="SUN"
)

// Timeseries trajectory -> CSV artifact:
get_ephemeris(
  target="PSP",
  time="2021-11-21T00:00:00Z",
  time_end="2021-11-22T00:00:00Z",
  step="1h",
  frame="ECLIPJ2000",
  observer="SUN",
  output_file="/tmp/spedas-geom/psp_traj.csv"
)
```

## Distance between two targets

```jsonc
compute_distance(
  target1="PSP",
  target2="SUN",
  time_start="2021-11-21T00:00:00Z",
  time_end="2021-11-22T00:00:00Z",
  step="1h"
)
```

Returns a compact distance summary over the range. Keep the range short and the
step coarse until the science need is clear.

## Coordinate transforms

```jsonc
transform_coordinates(
  vector=[1.0, 0.0, 0.0],
  time="2015-10-16T13:06:00Z",
  from_frame="GSE",
  to_frame="GSM",
  spacecraft="MMS1"
)
```

Returns the transformed 3D vector. If a frame/body is unsupported or kernels are
missing, treat the structured error as the next planning step rather than
retrying blindly.

## Safe geometry walkthrough

```jsonc
spedas_overview()
browse_data_sources(source_type="spice")
manage_data_cache(source_type="spice", action="status")
get_ephemeris(target="PSP", time="2021-11-21T08:00:00Z")
compute_distance(target1="PSP", target2="SUN",
                 time_start="2021-11-21T00:00:00Z",
                 time_end="2021-11-21T06:00:00Z", step="1h")
transform_coordinates(vector=[1,0,0], time="2021-11-21T08:00:00Z",
                      from_frame="ECLIPJ2000", to_frame="J2000")
```

This walkthrough stays metadata/cache-aware and does not opt into kernel
downloads. If a call asks for `allow_kernel_download=True`, stop and confirm first.
