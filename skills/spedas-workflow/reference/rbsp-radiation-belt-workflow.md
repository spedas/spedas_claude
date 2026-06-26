# Canonical workflow: RBSP radiation-belt analysis

End-to-end recipe for a radiation-belt energization/loss study with the Van Allen
Probes (RBSP), following **plan → fetch → analyze → plot**. Orchestration only.

> **Tool maturity:** discovery/planning/fetch tools are **current**; the analysis-layer
> tools (`calculate_lshell`, `evaluate_magnetic_field`, `compute_particle_spectra`,
> `render_tplot`) are **proposed** (`spedas_mcp #12–#22`) and may not be released — each
> is tagged `[proposed]`. Confirm with `spedas_overview`; otherwise use the pyspedas
> fallback (`pyspedas-patterns.md`). See [`analysis-recipes.md`](analysis-recipes.md) and
> [`mission-loaders.md`](mission-loaders.md).

## 1. Plan

- Restate the event: which probe (`rbspa`/`rbspb`), interval (often one or more orbits or
  a storm main/recovery phase), the population (relativistic electrons, ring-current
  ions), and the success criterion (flux organized cleanly by L-shell; a recognizable
  acceleration/loss signature).
- `plan_spedas_observation` (current); gate storm-phase selection on `SYM_H`/`Kp` from
  OMNI (see [`mission-loaders.md`](mission-loaders.md)).

## 2. Fetch (canonical instruments/datasets)

RBSP dataset IDs are especially release-string sensitive (`REL04`, frame/cadence
suffixes) — **confirm with `browse_data_parameters` before fetching**.

- **Orbit / position** — needed for L-shell mapping (spacecraft position vs. time, GSM).
- **EMFISIS MAG** (field context, model input): `RBSP-A_MAGNETOMETER_4SEC-GSM_EMFISIS-L3`.
- **ECT particle flux** — relativistic electrons: `RBSPA_REL04_ECT-REPT-SCI-L3` and
  `RBSPA_REL04_ECT-MAGEIS-L3`; low-energy/ring-current: `RBSPA_REL04_ECT-HOPE-MOM-L3`.

## 3. Analyze (the chain)

1. **L-shell** — `calculate_lshell` `[proposed: spedas_mcp #17]` (fallback:
   `calculate_lshell()` in `pyspedas/geopack/`) from the position series. Default IGRF is
   parameter-free; distorted models (`t89`/`t96`/`t01`/`ts04`) need geomagnetic
   parameters. This produces the radiation-belt coordinate everything is organized by.
2. **(Optional) field model / footprint** — `evaluate_magnetic_field`
   `[proposed: spedas_mcp #16]` (fallback: geopack `tt*`/`tigrf` + `ttrace2endpoint()`)
   for field strength along the orbit or ionospheric footpoints.
3. **Energy spectra** — `compute_particle_spectra` `[proposed: spedas_mcp #19]`
   (fallback: `spd_pgs_make_e_spec()`) for flux vs. energy vs. time; or use the ECT L3
   flux products directly.
4. **Organize flux by L** — bin/plot flux vs. L-shell and time to expose the
   acceleration (flux growth at fixed L) or loss (dropout) signature.

## 4. Plot

- `render_tplot` `[proposed: spedas_mcp #20]` (fallback: `tplot()`/`specplot()`, Agg,
  `display=False`): stack L-shell vs. time, the electron-flux energy spectrogram, and a
  flux-vs-L view; storm indices (`SYM_H`) as a context panel.
- Save the PNG path.

## 5. Physical sanity checks

- **L-shell range** — RBSP apogee ~5.8 R_E, so L typically spans ~1–6 over an orbit. L
  values far outside (e.g. tens) signal a position-frame or model error.
- **Flux organization** — radiation-belt flux should vary smoothly with L; a clean
  belt/slot/outer-belt structure is the expected pattern. Noise that ignores L means a
  mapping or masking bug.
- **Model choice** — IGRF is robust and cheap; only use distorted Tsyganenko models when
  you have valid geomagnetic parameters for the interval, and record them.
- **Storm phase consistency** — dropouts and acceleration should track storm phase
  (`SYM_H` minimum / recovery); cross-check against OMNI.
- **Particle masking** — confirm zero/inactive bins are masked and the spacecraft
  potential handled (see the particle-analysis subsection of
  [`analysis-recipes.md`](analysis-recipes.md)).

## 6. Artifacts & provenance

Route bulk outputs to files; reply conclusion-first with paths. Record the probe,
dataset IDs (with release strings), the field model + geomagnetic parameters used for
L-shell, energy ranges, and storm indices in the provenance bundle
([`artifact-provenance.md`](artifact-provenance.md)).
