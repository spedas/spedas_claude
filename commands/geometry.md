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
  kernel inspection/download surface.

Recommended order: start with the two `list_*` tools to confirm targets/frames,
then do the geometry you need. Separate geometry lookups from measurement-data
fetches, and **avoid large kernel downloads without confirming cache and scope** —
keep `manage_spice_kernels` downloads explicit and narrowly scoped.

For copy-ready argument examples, return-shape notes, and the
metadata-vs-download distinction, see
`skills/spedas-workflow/reference/geometry-spice.md`.
