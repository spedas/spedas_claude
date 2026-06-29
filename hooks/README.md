# Hooks

`hooks/hooks.json` ships with an **enabled-by-default `PreToolUse` safety gate**
for issue #6. It runs before SPEDAS MCP calls that can perform real archive data
fetches or large SPICE kernel downloads.

## Default guard

The shipped hook matches:

- data/archive downloads: `fetch_data_product`, `fetch_hapi_data`, `fetch_fdsn_data`
  plus legacy `fetch_data` / `fetch_pds_data` names;
- legacy SPICE cache mutation: `manage_spice_kernels` (read-only status/list actions
  stay quiet);
- geometry tools (`get_ephemeris`, `compute_distance`, `transform_coordinates`) only
  when the tool input explicitly sets `allow_kernel_download: true`.

The companion script is [`fetch_guard.py`](fetch_guard.py). It is dependency-free,
reads Claude Code's hook JSON from stdin, writes a `PreToolUse` JSON response with
`permissionDecision: "ask"`, and exits `0`. It does **not** download data, mutate
files, or call the MCP server. Metadata/planning tools remain frictionless; the gate
only asks for confirmation at the moment a potentially expensive fetch/kernel action
would run.

Before approving a guarded call, confirm the science question, exact dataset/source
or SPICE target, UTC time range, cache/output location, and provenance plan. The guard
adds extra wording for wide time ranges and nudges source-specific fetches back toward
the unified `fetch_data_product` workflow unless the source-specific call is needed.

The enabled posture is machine-checked by [`default_posture.json`](default_posture.json)
and `scripts/validate_plugin.py`: CI fails if `hooks/hooks.json` goes empty, loses the
`PreToolUse` matcher, stops invoking `hooks/fetch_guard.py`, drops a guarded tool, or
points at missing docs/tests.

## Reference / compatibility example

[`examples/pretooluse-fetch-guard.md`](examples/pretooluse-fetch-guard.md) shows the
same JSON wiring in a copyable form. [`examples/fetch_guard.py`](examples/fetch_guard.py)
is a compatibility wrapper for older copied configs that used the former example path;
it delegates to the default guard.

See [`../docs/safety.md`](../docs/safety.md) for the full metadata-first,
plan-before-fetch boundary.
