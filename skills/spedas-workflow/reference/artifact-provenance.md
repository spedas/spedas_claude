# Artifact and provenance discipline

For each real data run, save a small run directory containing:

- `request.json` — science question, time range, mission/source, parameters, allowed side effects.
- `tool_calls.jsonl` or notes — MCP/PySPEDAS calls and arguments.
- `environment.txt` — package versions, Python version, CLI/runtime if relevant.
- `artifacts_manifest.json` — output paths, sizes, SHA-256 hashes, and descriptions.
- `provenance.md` — source datasets/files, caveats, rate limits, missing metadata, and validation status.

Human-facing replies should summarize the science result and provide paths, not raw CDF/tplot/array content.
