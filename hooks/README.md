# Hooks

`hooks.json` ships as an **intentional empty placeholder**:

```json
{ "hooks": [] }
```

This is a deliberate, documented choice (issue #6), **not** a missing feature. The
plugin enforces its "metadata-first, plan-before-fetch" discipline through prose in
the skill/commands and through per-CLI `--allowedTools` scoping, rather than a
default hook that would change your runtime behavior without you opting in. An
enabled-by-default `PreToolUse` gate is a maintainer/product decision, so **#6 stays
open** for a stronger default enforcement; this release only contracts the empty
posture as intentional.

The empty posture is **machine-checked, not just prose**: a sidecar contract,
[`default_posture.json`](default_posture.json), records
`"spedas_default_hook_posture": "deferred"` plus the rationale, the issue link, and
the opt-in example. The validator (`scripts/validate_plugin.py`) asserts that, while
`hooks.json` is empty, the sidecar exists and is consistent (declares the deferred
intent, names issue #6, points at an opt-in example that really exists, and lists
docs that really exist) — so an empty array can never be silently read as a
regression, and a malformed/half-edited hook still fails CI. The sidecar is **not** a
Claude Code hook file; it is kept separate so the hook schema stays minimal.

## Want a runtime fetch/kernel warning?

An **opt-in, disabled-by-default** example is provided:

- [`examples/pretooluse-fetch-guard.md`](examples/pretooluse-fetch-guard.md) —
  how to enable a `PreToolUse` reminder before network-download tools and geometry calls that set `allow_kernel_download=True`
  (`fetch_data_product`, `fetch_hapi_data`, `fetch_fdsn_data`, `get_ephemeris`, `compute_distance`, `transform_coordinates`).
- [`examples/fetch_guard.py`](examples/fetch_guard.py) — the companion guard
  script. It is advisory only: it prints a reminder and exits 0, performs no
  network access, and writes no files.

Copy the JSON from the example doc into `hooks.json` only if you want it. See
[`../docs/safety.md`](../docs/safety.md) for the full fetch/kernel safety boundary.
