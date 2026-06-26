# Canonical workflow: THEMIS substorm

End-to-end recipe for substorm onset/timing analysis with THEMIS probes + ground
magnetometers, following **plan → fetch → analyze → plot**. Orchestration only.

> **Tool maturity:** discovery/planning/fetch tools are **current**; the analysis-layer
> tools (`dynamic_power_spectrum`, `wavelet_transform`, `render_tplot`, and any
> neutral-sheet/field-model step) are **proposed** (`spedas_mcp #12–#22`) and may not be
> released — each is tagged `[proposed]`. Confirm with `spedas_overview`; otherwise use
> the pyspedas fallback (`pyspedas-patterns.md`). See
> [`analysis-recipes.md`](analysis-recipes.md) and
> [`mission-loaders.md`](mission-loaders.md).

> **Note on neutral-sheet location:** the gap issue mentions a neutral-sheet/locator
> step. There is **no dedicated `spedas_mcp #12–#22` tool** for neutral-sheet location
> as of this writing; pyspedas exposes `neutral_sheet()` (`pyspedas/analysis/`). Treat
> neutral-sheet location as a **pyspedas fallback** unless a future MCP tool is confirmed
> live — do not assume an MCP tool name for it.

## 1. Plan

- Restate the event: which probes (tail-season conjunctions), interval bracketing the
  expected onset, and a ground-station chain near the expected auroral footprint.
- Success criterion: a consistent onset time across ground Pi2 onset, probe dipolarization
  (B_z increase), and flow/particle injection.
- `plan_spedas_observation` (current); gate event selection on indices (`AE`, `SYM_H`)
  from OMNI — see [`mission-loaders.md`](mission-loaders.md).

## 2. Fetch (canonical instruments/datasets)

Confirm IDs/variables with `browse_data_parameters` first.

- **Ground magnetometers** (Pi2 onset timing): `THG_L2_MAG_<SITE>` for a latitude/longitude
  chain of stations.
- **Probe FGM** (dipolarization, B_z): `THA_L2_FGM` (and other probes `b`–`e`).
- **Probe ESA/SST** (injection, plasma): `THA_L2_ESA`, `THA_L2_SST`.
- **OMNI** context/driver: `OMNI_HRO2_1MIN` (`BZ_GSM`, `AE`).

## 3. Analyze (the chain)

1. **Preprocess** — uniform cadence + gap fill across probes/stations
   (`reduce_tres`/`avg_data` + `tinterpol` + `interp_gap`; pyspedas fallback).
2. **Pi2 onset timing** — `dynamic_power_spectrum` `[proposed: spedas_mcp #15]`
   (fallback: `dpwrspc()`) on ground **B** to localize Pi2 pulsation power in time;
   compare onset across the station chain. Use `wavelet_transform`
   `[proposed: spedas_mcp #15]` (fallback: `wavelet()` + `wave_signif()`) for
   time-localized wave packets and significance bands.
3. **Dipolarization** — inspect probe FGM B_z for the sharp increase; cross-time with the
   Pi2 onset.
4. **Neutral-sheet context (optional)** — `neutral_sheet()` (pyspedas fallback) to
   estimate the probe's position relative to the current sheet; no confirmed MCP tool.
5. **Injection** — ESA/SST flux increase confirms particle injection at onset.

## 4. Plot

- `render_tplot` `[proposed: spedas_mcp #20]` (fallback: `tplot()`/`specplot()`, Agg,
  `display=False`): a stacked panel of ground-B dynamic spectra (Pi2), probe B_z
  (dipolarization), and ESA/SST flux, time-aligned so the onset cascade is visible.
- Save the PNG path.

## 5. Physical sanity checks

- **Onset ordering** — Pi2 onset, dipolarization, and injection should be causally
  consistent in time (within propagation/expansion delays). A large inconsistency means
  re-check station selection or interval.
- **Pi2 band** — Pi2 power sits in the ~6–25 mHz (~40–150 s) range; a spectrogram peak far
  outside that band is suspect.
- **|B| / B_z ranges** — tail-region values; a dipolarization is a *jump* in B_z, not a
  baseline offset.
- **Driver consistency** — onset should follow a period of southward IMF (`BZ_GSM < 0`)
  and elevated `AE`; if the driver is absent, reconsider the classification.

## 6. Artifacts & provenance

Route bulk outputs to files; reply conclusion-first with paths. Record station list,
dataset IDs, probe set, the onset times derived from each diagnostic, spectral window
parameters, and the driver indices in the provenance bundle
([`artifact-provenance.md`](artifact-provenance.md)).
