---
description: Guided analysis selection — map a science question (+ fetched artifacts) to an MCP tool chain, required preprocessing, and sanity checks.
argument-hint: "[science question] [artifact paths] [mission/frame]"
---

# SPEDAS guided analysis selection

You have data (or a plan to fetch it) and need to know **which transformation answers
the question**. This command drives the recipe table in
[`skills/spedas-workflow/reference/analysis-recipes.md`](../skills/spedas-workflow/reference/analysis-recipes.md)
to recommend a concrete, ready-to-run MCP tool chain. It is **orchestration only** —
it selects and sequences tools; it performs no compute itself.

## What this command does

1. **Ask** the science question and the available artifacts (paths to already-fetched
   files) and frame/mission if not given.
2. **Recommend** the MCP tool chain from the analysis-recipe reference (e.g. fetch **B**
   → `generate_fac_matrix` → `dynamic_power_spectrum`/`wavelet_transform` →
   `render_tplot`). Note: some pyspedas analyses (e.g. `twavpol` polarization,
   `find_magnetic_nulls`) have **no dedicated proposed MCP tool** — recommend the
   pyspedas fallback for those rather than naming a non-existent tool.
3. **Name the required preprocessing** (uniform cadence, NaN gap-fill, despike) before
   the analysis step — most multi-spacecraft/spectral methods fail silently on gappy or
   non-uniform input.
4. **List the physical sanity checks** to run before trusting the result.
5. **Emit ready-to-run MCP calls** with the artifact paths filled in, routing all bulk
   outputs to files and surfacing artifact paths to the user.

## Tool-maturity guardrail (do not overclaim)

The transformation/plotting tools are **proposed analysis-layer MCP tools**
(`spedas_agent_kit #12–#22`) and may **not** be released yet. For every recommended step:

- Tag current vs. proposed tools (the recipe reference marks proposed ones
  `[proposed: spedas_agent_kit #NN]`).
- **Confirm a proposed tool is live** via `spedas_overview` / the active tool list
  before presenting it as runnable.
- If a tool is not available, give the **pyspedas fallback** (run the named function in
  the user's own Python env — see
  [`skills/spedas-workflow/reference/pyspedas-patterns.md`](../skills/spedas-workflow/reference/pyspedas-patterns.md))
  and say so explicitly. Never imply an unreleased tool is callable.

## Selection flow

For the parsed science question, walk the recipe reference:

- **Boundary normal / LMN** (magnetopause, bow shock, current sheet) →
  `analyze_minvar_coordinates`.
- **Field-aligned (∥/⊥) decomposition** → `generate_fac_matrix`, then rotate.
- **Frame change of a time series** (GSE/GSM/SM/…) → `transform_timeseries_coordinates`.
- **Pulsations / turbulence (time-frequency)** → `dynamic_power_spectrum` /
  `wavelet_transform`.
- **Plasma moments (n, V, T, P, q)** → `compute_particle_moments`.
- **Energy / pitch-angle spectra** → `compute_particle_spectra` (pitch-angle needs a FAC
  reference).
- **L-shell / field model** → `calculate_lshell` / `evaluate_magnetic_field`.
- **Render** → `render_tplot`.

Always precede the analysis step with the **data-preparation** chain
(`interp_gap`, `reduce_tres`/`avg_data`, `yclip`/`deflag`) where the recipe requires it,
and finish with the recipe's physical sanity checks. For fully worked, event-class
examples, point the user to the canonical workflows:
[`mms-magnetopause-workflow.md`](../skills/spedas-workflow/reference/mms-magnetopause-workflow.md),
[`themis-substorm-workflow.md`](../skills/spedas-workflow/reference/themis-substorm-workflow.md),
[`rbsp-radiation-belt-workflow.md`](../skills/spedas-workflow/reference/rbsp-radiation-belt-workflow.md).

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Parse `$ARGUMENTS` as the analysis request. Expected (free-form, all optional):

- **science question** — what to measure or decide (e.g. `find the magnetopause normal`,
  `is there a field-aligned electron beam`, `Pi2 onset time`).
- **artifact paths** — paths to already-fetched data files to analyze.
- **mission / frame** — mission/instrument and coordinate frame if relevant (e.g.
  `MMS FGM`, `GSM`).

Example: `/analyze find the magnetopause normal ./run/mms1_fgm.csv MMS GSE`.
If the question is missing, ask for it. If no artifacts are named, ask which fetched
files to use (or route the user to `/data` / `/workflow` to fetch first). Keep all bulk
outputs in files and report artifact paths, not raw arrays.
