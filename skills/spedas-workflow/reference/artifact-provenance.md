# Artifact and provenance discipline

For each real data run, save a small run directory containing:

- `request.json` — science question, time range, mission/source, parameters, allowed side effects.
- `tool_calls.jsonl` or notes — MCP/PySPEDAS calls and arguments.
- `environment.txt` — package versions, Python version, CLI/runtime if relevant.
- `artifacts_manifest.json` — output paths, sizes, SHA-256 hashes, and descriptions.
- `provenance.md` — source datasets/files, caveats, rate limits, missing metadata, and validation status.

Human-facing replies should summarize the science result and provide paths, not raw CDF/tplot/array content.

## Ready-made templates

Do not hand-build these files from memory. Copy the scaffolding in
[`templates/provenance/`](../../../templates/provenance/) (repo root) into your
run directory and fill in the blanks. That folder ships all five files plus
`capture_environment.sh`, which records the reproducibility-critical bits
(`environment.txt`) for you. See `templates/provenance/README.md` for the
copy-and-fill workflow.

## What `environment.txt` must record (differs by layer)

`environment.txt` is only useful if it captures the layer(s) the run actually used.
The two layers (see the README's "Architecture: two independent layers") are
recorded differently:

- **MCP-only run** (you only called `spedas` MCP tools): record the resolved
  `spedas_mcp` source and commit/version, the `uv`/`uvx` version, the OS, and the
  cache/kernel directories in effect. The *Python packages in your local shell are
  irrelevant* — the server runs in its own `uvx`-managed environment. The
  single most important field is the resolved `spedas_mcp` commit (see
  [`docs/dependencies.md`](../../../docs/dependencies.md) for how to pin/record it).
- **PySPEDAS run** (you ran local `pyspedas`/`pytplot` recipes): additionally record
  your local `python --version`, `pip freeze` (at least `pyspedas`/`pytplot`/`numpy`
  versions), and the OS. PySPEDAS is *your* install, so this is what a re-runner
  needs to reproduce it.

`capture_environment.sh` writes the common fields and notes which layer was used;
add the layer-specific lines above as applicable.
