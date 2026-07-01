# Provenance — FILL: run title

## Science result (conclusion first)

FILL: one-paragraph summary of what was found. Paths, not raw arrays.

## Sources

- Source category: FILL (cdaweb / pds / spice)
- Dataset/product id(s): FILL
- Parameters/variables: FILL
- Time range: FILL (start / stop, ISO8601)
- Coordinate frame: FILL or n/a

## Layer used

- [ ] MCP-only (only `spedas` MCP tools were called)
- [ ] PySPEDAS (local `pyspedas`/`pytplot` recipes were run)

> If PySPEDAS was used, `environment.txt` must additionally record local
> `python --version` and `pyspedas`/`pytplot` versions. Follow the
> artifact-first guardrails in `skills/spedas-workflow/SKILL.md`.

## Caveats & data gaps

FILL: missing variables, partial PDS labels, unavailable kernels, archive rate
limits/429s hit, anything a re-runner must know. Classify failures inline
with enough archive/cache/kernel context for a re-runner to reproduce them.

## Validation status

FILL: how the result was sanity-checked (cross-checked against OMNI, expected
signature present, units verified, etc.), and what is still unverified.

## Reproduce

FILL: exact steps / tool calls (see `tool_calls.jsonl`) and the resolved
`spedas_agent_kit` commit (see `environment.txt`).
