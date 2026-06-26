---
description: Run the SPEDAS geometry/SPICE workflow (positions, distances, frame transforms).
argument-hint: "[target] [frame] [time]"
---

# SPEDAS geometry / SPICE workflow

Use the dedicated geometry/SPICE tools for spacecraft/body positions, distances,
and coordinate-frame transforms. Geometry is its own tool family — do **not**
route it through `fetch_data_product`.

The six tools:

- `list_spice_missions()` — supported targets, NAIF IDs, kernel status (metadata).
- `list_coordinate_frames()` — supported frames and usage notes (metadata).
- `get_ephemeris(target, time, …)` — single-time state inline, or a timeseries
  trajectory written to CSV (`time_end` + `step` + `output_file`).
- `compute_distance(target1, target2, time_start, time_end, step?)` — distance
  over a range.
- `transform_coordinates(vector, time, from_frame, to_frame, spacecraft?)` —
  transform a 3D vector between frames.
- `manage_spice_kernels(action, mission?, filenames?)` — the explicit, gated
  kernel inspection/load/maintenance surface.

Recommended order: start with the two `list_*` tools to confirm targets/frames,
then do the geometry you need. Separate geometry lookups from measurement-data
fetches, and **avoid large kernel loads/downloads without confirming cache and scope** —
keep `manage_spice_kernels(action="load"|"clean"|"purge")` explicit and narrowly scoped.

SPICE kernels are often 100 MB–1+ GB each. Loading/downloading them is an
**opt-in** action — confirm the cache directory and scope first. See the kernel
safety boundary in [`docs/safety.md`](../docs/safety.md).

For copy-ready argument examples, return-shape notes, and the
metadata-vs-download distinction, see
[`skills/spedas-workflow/reference/geometry-spice.md`](../skills/spedas-workflow/reference/geometry-spice.md).

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Parse `$ARGUMENTS` for the geometry request. Expected (free-form, all optional):

- **target** — spacecraft/body (e.g. `PSP`, `Earth`); confirm via
  `list_spice_missions()`.
- **frame** — coordinate frame (e.g. `HCI`, `GSE`); confirm via
  `list_coordinate_frames()`.
- **time** — ISO time or range (e.g. `2024-06-25` or `2024-06-25/2024-06-26`).

Example: `/geometry PSP HCI 2024-06-25`. Confirm targets/frames with the
`list_*` tools first, and keep `manage_spice_kernels(action="load"|...)` opt-in
and narrowly scoped even when arguments request a position. If arguments are
missing, ask for target, frame, and time.
