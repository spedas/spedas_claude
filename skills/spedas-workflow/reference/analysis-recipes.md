# Analysis recipes: science question → pyspedas → MCP tool chain

After you have **fetched** a data product (via `fetch_data_product` / the unified
data layer), this reference bridges the next cliff: which transformation answers a
given science question, which pyspedas function implements it, and which MCP tool
exposes (or will expose) it.

## Read this first: which MCP tools are real today

The SPEDAS MCP surface is split into two maturity tiers. Label every recipe step
by its tier so you never imply an unreleased tool is callable:

- **Current MCP tools** — discovery, planning, and fetch. These ship in the 26-tool
  `spedas_mcp` surface today: `search_spedas_data_sources`, `plan_spedas_observation`,
  `compare_cdaweb_pds_spice`, `create_spedas_analysis_bundle`, `browse_data_sources`,
  `load_data_source`, `browse_data_parameters`, `fetch_data_product`,
  `manage_data_cache`, and the geometry/SPICE family. They produce the **input files**
  every recipe below consumes.
- **Proposed analysis-layer MCP tools** — the transformation/plotting layer
  (`spedas_mcp` issues #12–#22). These are **designed but not necessarily released**.
  Each is tagged below as `[proposed: spedas_mcp #NN]`. Until a tool lands, use the
  **PySPEDAS fallback** (run the named pyspedas function in your own Python env — see
  `pyspedas-patterns.md`) and say so explicitly. **Do not claim a `[proposed]` tool is
  available**; confirm with `spedas_overview` / the live tool list first.

Tool names follow the `spedas_mcp` issue proposals and may change before release;
treat them as the *expected* names, not a guarantee.

## How to use this file

1. Find the science question in the recipe tables.
2. Run the listed **preprocessing** first (see the data-preparation section) — most
   multi-spacecraft and spectral methods silently produce garbage on gappy or
   non-uniform input.
3. Chain the analysis tool(s); if the tool is `[proposed]` and not yet live, drop to
   the pyspedas fallback in your own environment.
4. Render with `render_tplot` `[proposed: spedas_mcp #20]` (fallback: pyspedas
   `tplot()`/`specplot()` with the Agg backend).
5. Run the **physical sanity checks** before trusting the result.
6. Save artifacts + provenance (`artifact-provenance.md`); reply with paths, not arrays.

The interactive form of this table is the `/analyze` command
([`commands/analyze.md`](../../../commands/analyze.md)), which walks the same
question → preprocessing → tool-chain → sanity-check flow and emits ready-to-run
MCP calls.

---

## Recipe table: science question → function → MCP tool

| Science question | pyspedas function (module) | MCP tool | Notes |
|---|---|---|---|
| Rotate a vector time series between geomagnetic frames (GSE/GSM/SM/GEI/GEO/MAG/J2000) | `cotrans()` (`cotrans_tools/cotrans.py`) | `transform_timeseries_coordinates` `[proposed: spedas_mcp #12]` | Distinct from SPICE `transform_coordinates`, which is a *single static* vector. |
| Build field-aligned coordinates (∥/⊥ to **B**) | `fac_matrix_make()` (`cotrans_tools/fac_matrix_make.py`) | `generate_fac_matrix` `[proposed: spedas_mcp #13]` | Position-dependent modes (`rgeo`, `mphism`, …) need a position series. |
| Find a boundary normal / LMN frame (magnetopause, bow shock, current sheet) | `minvar()` / `minvar_matrix_make()` (`cotrans_tools/minvar.py`) | `analyze_minvar_coordinates` `[proposed: spedas_mcp #14]` | Returns eigenvalues + normal; check the intermediate/min eigenvalue ratio. |
| Wave polarization / ellipticity / wave-normal angle | `twavpol()` (`analysis/twavpol.py`) | *(no dedicated proposed tool yet)* — fallback to pyspedas | Pair with FAC rotation first; see particle/wave caveats below. |
| Dynamic power spectrum (Pi2/Pc pulsations, foreshock turbulence) | `dpwrspc()`/`tdpwrspc` (`tplot_tools/tplot_math/dpwrspc.py`) | `dynamic_power_spectrum` `[proposed: spedas_mcp #15]` | Welch / sliding Hanning window. |
| Wavelet / time-frequency map (chorus, EMIC packets, onset) | `wavelet()` + `wave_signif()` (`analysis/wavelet.py`) | `wavelet_transform` `[proposed: spedas_mcp #15]` | Set `compute_significance` for Torrence & Compo bands. |
| Tsyganenko/IGRF field model + field-line tracing | `tt89/tt96/tt01/tts04`, `tigrf`, `ttrace2endpoint()` (`geopack/`) | `evaluate_magnetic_field` `[proposed: spedas_mcp #16]` | T01/TS04 need solar-wind/geomagnetic indices. |
| McIlwain L-shell + ionospheric footprint | `calculate_lshell()` (`geopack/calculate_lshell.py`) | `calculate_lshell` `[proposed: spedas_mcp #17]` | IGRF default is parameter-free and cheap. |
| Plasma moments (n, V, T, P tensor, q) from a 3D distribution | `moments_3d()` (`particles/moments/moments_3d.py`) | `compute_particle_moments` `[proposed: spedas_mcp #18]` | Supply spacecraft potential + energy range; see particle workflow below. |
| Energy / pitch-angle / azimuth spectrograms from a 3D distribution | `spd_pgs_make_e_spec()` / `_phi_` / `_theta_` (`particles/spd_part_products/`) | `compute_particle_spectra` `[proposed: spedas_mcp #19]` | Pitch-angle spectra need a magnetic-field reference (FAC). |
| Magnetic topology / null detection (multi-spacecraft) | `find_magnetic_nulls()`, `lingradest()` (`analysis/`) | *(no dedicated proposed tool yet)* — fallback to pyspedas | Requires ≥4 spacecraft, gap-filled, uniform-cadence input. |
| Render multi-panel time series + spectrograms to PNG | `tplot()` / `specplot()` (`tplot_tools/MPLPlotter/`) | `render_tplot` `[proposed: spedas_mcp #20]` | Returns a PNG path only; Agg backend, `display=False`. |

> Some recipes have **no dedicated proposed MCP tool yet** (e.g. `twavpol`,
> `find_magnetic_nulls`). For these, the only route today is the pyspedas fallback in
> your own environment. Do not invent an MCP tool name for them.

---

## Data preparation (run *before* the analysis step)

Multi-spacecraft inversions and spectral methods assume **uniform cadence and no
NaNs**. Skipping these steps is the most common cause of silently wrong results.

| Preprocessing need | pyspedas function (module) | When it is required |
|---|---|---|
| Fill NaN gaps before any multi-spacecraft analysis | `interp_gap()` / `tinterpol` (`analysis/interpolate.py`) | **Required** before curlometer, `find_magnetic_nulls`, `lingradest` — they fail or bias on NaNs. |
| Downsample MMS burst / put all probes on a common cadence | `reduce_tres()`, `avg_data()` (`analysis/`) | Required when combining instruments/probes at different rates; reduces cost. |
| Despike / clip out-of-range values | `yclip()`, `deflag()` (`analysis/`) | Required before gradient methods; spikes dominate finite differences. |
| Time-domain filtering (band isolation) | `time_domain_filter()` (`analysis/`) | Optional; isolate a band before polarization/spectra. |
| Numerical derivative | `deriv_data()` (`analysis/`) | For dB/dt, current proxies. |

Preprocessing prerequisites for the canonical multi-spacecraft inversions:

- **Curlometer / `find_magnetic_nulls` / `lingradest`** require: (1) all spacecraft on
  a **common, uniform time base** (`reduce_tres`/`avg_data` + `tinterpol`), (2) **NaNs
  filled** (`interp_gap`), (3) spikes removed (`yclip`/`deflag`). Verify spacecraft
  separation is small vs. the structure scale before trusting gradients.

There is no dedicated proposed MCP tool for these preprocessing steps yet; run them
in pyspedas (fallback) and record the cadence/gap-fill choices in provenance.

---

## Particle-analysis workflow

Particle products are the subtlest part of the chain. Use this subsection to pick the
right moment/spectrum and to decide when to trust it.

### Which moment output matters

`compute_particle_moments` `[proposed: spedas_mcp #18]` (fallback: `moments_3d()`)
returns several quantities — choose by question:

- **Density (n)** — continuity, boundary identification, mass loading. Most robust
  moment; least sensitive to the high-energy tail.
- **Velocity (V)** — bulk flow, reconnection jets, convection. Sensitive to
  spacecraft-potential correction and to missing low-energy bins.
- **Temperature / pressure tensor (T, P)** — anisotropy, heating, pressure balance.
  The tensor (not just scalar T) is needed for agyrotropy/anisotropy work.
- **Heat flux (q)** — energy transport; the **highest-order**, **noisiest** moment.
  Trust only with good counting statistics and a clean high-energy tail.

### Energy vs. pitch-angle vs. 2D slices

`compute_particle_spectra` `[proposed: spedas_mcp #19]` (fallback:
`spd_pgs_make_*_spec()`):

- **Energy spectrum** (energy vs. time) — beams, acceleration, spectral hardening.
- **Pitch-angle spectrum** (PA vs. time) — anisotropy, field-aligned beams, loss-cone
  signatures. **Requires a magnetic-field reference (FAC frame).**
- **2D distribution slices** — detailed structure (counter-streaming, ring/shell
  distributions) at single times; expensive, use sparingly.

### Reading rotation frames

- **BV / BE / perp planes** — orient slices relative to **B** and bulk-velocity / **E**.
- **FAC (∥/⊥)** — parallel vs. perpendicular dynamics; build with `generate_fac_matrix`
  `[proposed: spedas_mcp #13]` first, then rotate the vector/distribution.
- State which frame a result is in; a "perpendicular" anisotropy is meaningless without
  naming the reference.

### When to trust particle results

- **NaN / zero-bin masking** — inactive/zero-count bins must be masked, not averaged in,
  or moments and spectra bias low. (The pyspedas spec/moment routines mask; confirm the
  MCP tool reports it did.)
- **Spacecraft-potential correction** — pass the measured `sc_potential_v`; an
  uncorrected potential shifts the low-energy cutoff and biases density/velocity.
- **Energy-range gating** — restrict to the populations you mean (e.g. exclude
  photoelectrons); record the range used.
- **Counting statistics** — high moments (q) and fine PA structure need adequate counts;
  burst mode helps. Note the data rate in provenance.

---

## Physical sanity checks (apply to every recipe)

- **Field magnitudes** — magnetospheric |B| ~ 1–100+ nT (higher near Earth/at low
  altitude); solar-wind |B| ~ a few nT. A result orders of magnitude off signals a
  unit/frame/scaling bug.
- **MVA normal stability** — trust an LMN normal only when the
  intermediate/minimum eigenvalue ratio is comfortably > 1 (well-determined min-variance
  direction) and the normal is stable across nearby windows.
- **Frame consistency** — confirm the coordinate frame of inputs matches what the tool
  expects (don't feed GSM where GSE is assumed).
- **Cadence/gap** — re-check that preprocessing actually delivered uniform cadence and
  no NaNs before believing a multi-spacecraft inversion.

## Artifact discipline

Every step emits a **file path**, not inline arrays. Route bulk outputs to disk, save
the provenance bundle (`artifact-provenance.md`, templates in `templates/provenance/`),
and reply conclusion-first with paths. See the canonical event workflows
([`mms-magnetopause-workflow.md`](mms-magnetopause-workflow.md),
[`themis-substorm-workflow.md`](themis-substorm-workflow.md),
[`rbsp-radiation-belt-workflow.md`](rbsp-radiation-belt-workflow.md)) for fully worked
plan → fetch → analyze → plot chains, and
[`mission-loaders.md`](mission-loaders.md) for the mission/instrument/dataset map.
