# Canonical workflow: MMS magnetopause crossing

End-to-end recipe for a magnetopause (or current-sheet/bow-shock) boundary analysis
with MMS, following **plan → fetch → analyze → plot**. Orchestration only: this
references MCP tools and pyspedas functions; the plugin performs no compute itself.

> **Tool maturity:** discovery/planning/fetch tools are **current**; the analysis-layer
> tools (`generate_fac_matrix`, `analyze_minvar_coordinates`, particle moments/spectra,
> `render_tplot`) are **proposed** (`spedas_mcp #12–#22`) and may not be released —
> each is tagged `[proposed]`. Confirm with `spedas_overview` / the live tool list; if a
> tool is not yet available, use the pyspedas fallback in your own environment
> (`pyspedas-patterns.md`). See [`analysis-recipes.md`](analysis-recipes.md) for the
> full tool↔function map and [`mission-loaders.md`](mission-loaders.md) for dataset IDs.

## 1. Plan

- Restate the event: spacecraft (which MMS probes), interval (keep it tight around the
  crossing), expected signature (rotation in **B**, density/velocity jump, magnetic
  shear), success criterion (a stable boundary normal + thickness estimate).
- `plan_spedas_observation` (current) for MMS + CDAWeb; `create_spedas_analysis_bundle`
  to scaffold a reusable plan/provenance directory.
- Canonical example interval (starter): 2015-10-16 ~13:06 UT (a well-studied MMS
  magnetopause crossing).

## 2. Fetch (canonical instruments/datasets)

Confirm dataset IDs/variables with `browse_data_parameters` before fetching
(IDs drift — see [`mission-loaders.md`](mission-loaders.md)). Keep the window narrow;
`fetch_data_product` is an opt-in download.

- **FGM** (boundary normal needs the **B** vector): `MMS1_FGM_SRVY_L2` (or `_BRST_L2`
  for fine structure) → `mms1_fgm_b_gse_srvy_l2`.
- **FPI** (the density/velocity jump): ion moments `MMS1_FPI_FAST_L2_DIS-MOMS`,
  electron moments `..._DES-MOMS`; for recomputing moments/spectra fetch the
  distributions `MMS1_FPI_BRST_L2_DIS-DIST`.
- Fetch the same products for each probe you intend to use.

## 3. Analyze (the chain)

1. **Preprocess** (required before MVA and any multi-spacecraft step): put probes on a
   common uniform cadence (`reduce_tres`/`avg_data` + `tinterpol`) and fill NaN gaps
   (`interp_gap`); despike (`yclip`/`deflag`). No dedicated MCP tool yet — pyspedas
   fallback. See the data-preparation section of [`analysis-recipes.md`](analysis-recipes.md).
2. **Boundary normal (LMN)** — `analyze_minvar_coordinates`
   `[proposed: spedas_mcp #14]` (fallback: `minvar()`) on the FGM **B** series across
   the crossing. Read the eigenvalues + normal vector.
3. **(Optional) Field-aligned frame** — `generate_fac_matrix`
   `[proposed: spedas_mcp #13]` (fallback: `fac_matrix_make()`) if you need ∥/⊥
   decomposition of fluctuations.
4. **Plasma moments** across the boundary — `compute_particle_moments`
   `[proposed: spedas_mcp #18]` (fallback: `moments_3d()`) from the distributions, with
   the spacecraft potential and an energy range; confirm the density/velocity jump.
5. **(Optional) Multi-spacecraft** — with 4 probes, gradient/curlometer or timing gives
   boundary motion and thickness (pyspedas fallback; preprocessing in step 1 is
   mandatory).

## 4. Plot

- `render_tplot` `[proposed: spedas_mcp #20]` (fallback: pyspedas `tplot()`/`specplot()`,
  Agg backend, `display=False`): stack **B** in LMN, |B|, density, and bulk velocity;
  the boundary should show the **B** rotation aligned with the density/velocity change.
- Save the PNG path; do not inline the figure data.

## 5. Physical sanity checks

- **|B| range** — magnetopause |B| ~ tens of nT; an order-of-magnitude miss = unit/frame bug.
- **Normal stability** — trust the LMN normal only when the intermediate/minimum
  eigenvalue ratio is comfortably > 1 and the normal is stable across nearby MVA windows.
  A degenerate ratio means the boundary normal is ill-determined — say so.
- **Coincidence** — the **B** rotation, the density jump, and the velocity change should
  line up in time; if not, re-check the interval or the frame.
- **Frame** — confirm GSE vs. GSM consistency between FGM and any model/position inputs.

## 6. Artifacts & provenance

Route all bulk outputs to files; reply conclusion-first with paths. Save the provenance
bundle (`artifact-provenance.md`, templates in `templates/provenance/`) recording the
dataset IDs, variables, frame, MVA windows, eigenvalue ratios, spacecraft potential, and
preprocessing (cadence/gap-fill) choices.
