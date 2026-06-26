# Hooks

`hooks.json` ships as an **intentional empty placeholder**:

```json
{ "hooks": [] }
```

This is a deliberate, documented choice (issue #6), **not** a missing feature. The
plugin enforces its "metadata-first, plan-before-fetch" discipline through prose in
the skill/commands and through per-CLI `--allowedTools` scoping, rather than a
default hook that would change your runtime behavior without you opting in. The
validator (`scripts/validate_plugin.py`) asserts this file stays a valid placeholder
so an accidental malformed hook fails CI.

## Want a runtime fetch/kernel warning?

An **opt-in, disabled-by-default** example is provided:

- [`examples/pretooluse-fetch-guard.md`](examples/pretooluse-fetch-guard.md) —
  how to enable a `PreToolUse` reminder before the network-download tools
  (`fetch_data_product`, `fetch_data`, `fetch_pds_data`, `manage_spice_kernels`).
- [`examples/fetch_guard.py`](examples/fetch_guard.py) — the companion guard
  script. It is advisory only: it prints a reminder and exits 0, performs no
  network access, and writes no files.

Copy the JSON from the example doc into `hooks.json` only if you want it. See
[`../docs/safety.md`](../docs/safety.md) for the full fetch/kernel safety boundary.
