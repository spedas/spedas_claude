---
description: Run the SPEDAS geometry/SPICE workflow (positions, distances, frame transforms).
argument-hint: "[target] [frame] [time]"
---

# SPEDAS geometry / SPICE workflow

Use the public geometry/SPICE tools for spacecraft/body positions, distances, and
coordinate-frame transforms. Geometry is its own workflow: do **not** route it
through `fetch_data_product`.

Current public geometry tools:

- `get_ephemeris(target, time, ...)`
- `compute_distance(target1, target2, time_start, time_end, step?)`
- `transform_coordinates(vector, time, from_frame, to_frame, spacecraft?)`

For discovery/cache context, use the unified facade first:

- `spedas_overview()`
- `browse_data_sources(source_type="spice")`
- `manage_data_cache(source_type="spice", action="status")`

SPICE kernels are often 100 MB--1+ GB. Geometry calls are guarded: if required
kernels are missing, stay metadata-only unless the user explicitly authorizes
`allow_kernel_download=True` for a narrow request.

For copy-ready examples and the kernel-download boundary, see
[`skills/spedas-workflow/reference/geometry-spice.md`](../skills/spedas-workflow/reference/geometry-spice.md).

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Parse `$ARGUMENTS` for the geometry request. Expected (free-form, all optional):

- **target** — spacecraft/body (e.g. `PSP`, `Earth`).
- **frame** — coordinate frame (e.g. `HCI`, `GSE`).
- **time** — ISO time or range (e.g. `2024-06-25` or `2024-06-25/2024-06-26`).

Example: `/geometry PSP HCI 2024-06-25`. Start with overview/source/cache context,
then run a narrow geometry call. If a call asks to download kernels, ask for
confirmation before setting `allow_kernel_download=True`.
