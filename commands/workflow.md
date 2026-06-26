---
description: Plan a SPEDAS science workflow (sources, target/interval, archive choice, reusable bundle).
argument-hint: "[target] [interval] [science goal]"
---

# SPEDAS science workflow

For a science request, call:

1. `search_spedas_data_sources` for candidate sources.
2. `plan_spedas_observation` for target/interval/source choices.
3. `compare_cdaweb_pds_spice` if the archive choice is unclear.
4. `create_spedas_analysis_bundle` to record a reusable plan/provenance scaffold.

Report assumptions, interval, source_type, source_id/dataset_id, parameters, and
remaining validation needed before real downloads.

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Parse `$ARGUMENTS` as the science request to plan. Expected (free-form, all
optional):

- **target** — mission/spacecraft or body (e.g. `PSP`, `MMS1`, `Earth`).
- **interval** — ISO time or range (e.g. `2024-06-25` or
  `2024-06-25/2024-06-26`).
- **science goal** — what to measure or compare.

Example: `/workflow PSP 2024-06-25/2024-06-26 magnetic field at perihelion`.
If arguments are missing, state the assumptions you make and confirm before any
fetch.
