# Provenance run templates

Lightweight scaffolding for the five-file provenance bundle the skill mandates per
real data run (issue #14). Copy this folder into a fresh run directory and fill in
the blanks — do not hand-build the files from memory.

## Why

Reproducible, citable heliophysics workflows need consistent provenance. Manual
creation means missed fields and per-researcher variation. These templates fix the
shape so a re-runner (or journal reviewer) can rely on it.

## Files

| File | Purpose |
|---|---|
| `request.json` | The science question, time range, source/parameters, and **explicit** allowed side effects (fetch opt-in). |
| `tool_calls.jsonl` | One JSON object per line: each MCP/PySPEDAS call + arguments + a result summary. |
| `environment.txt` | Reproducibility-critical versions. Populate with `capture_environment.sh`. |
| `artifacts_manifest.json` | Output paths, sizes, SHA-256 hashes, descriptions. |
| `provenance.md` | Source datasets/files, caveats, rate limits, missing metadata, validation status. |

## Workflow

```bash
# 1. Make a run directory and copy the templates in.
mkdir -p runs/2015-10-16-mms-magnetopause
cp -r templates/provenance/* runs/2015-10-16-mms-magnetopause/
cd runs/2015-10-16-mms-magnetopause

# 2. Capture the environment (records the reproducibility-critical bits).
./capture_environment.sh > environment.txt   # or: bash capture_environment.sh > environment.txt

# 3. Fill request.json BEFORE fetching; record opt-in in allowed_side_effects.
# 4. Append a line to tool_calls.jsonl for each call as you go.
# 5. After producing outputs, fill artifacts_manifest.json (use sha256sum/shasum).
# 6. Summarize sources, caveats, and validation status in provenance.md.
```

## The one field that matters most

`environment.txt` is useless for reproducibility unless it records the resolved
**`spedas_agent_kit` commit**. `capture_environment.sh` resolves the upstream HEAD for
you. What else to record depends on the layer you used; follow the
artifact-first guidance in [`../../skills/spedas-workflow/SKILL.md`](../../skills/spedas-workflow/SKILL.md)
and record whether the run was MCP-only, PySPEDAS-backed, or mixed.

These templates are intentionally minimal. There is no required generator or hook —
fill them by hand or wire them into your own tooling.
