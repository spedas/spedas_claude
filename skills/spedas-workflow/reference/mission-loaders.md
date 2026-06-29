# Mission-loader cheatsheet (instruments + canonical load patterns)

A quick map from **mission → instruments → CDAWeb dataset IDs → MCP fetch pattern**,
so you can go from "I want MMS FPI ion moments" to a concrete `fetch_data_product`
call without trial-and-error browsing.

## How to read this file (and how to verify IDs)

The MCP fetches via **CDAWeb** (not the pyspedas mission loaders directly), so the
unit you pass is a **CDAWeb dataset ID** plus parameter (variable) names, not a
pyspedas `probe`/`datatype`/`level` signature. This file maps the pyspedas loader
conventions onto CDAWeb dataset IDs.

> **Dataset IDs drift.** CDAWeb dataset IDs change with reprocessing, level, and
> cadence, and not every ID below is guaranteed current. Treat the IDs as **strong
> starting guesses**, and **confirm before fetching** with the discovery steps:
>
> 1. `browse_data_sources(source_type="cdaweb")` — list observatories/datasets.
> 2. `load_data_source(source_type="cdaweb", source_id=<mission/observatory>)` —
>    enumerate that mission's datasets.
> 3. `browse_data_parameters(source_type="cdaweb", dataset_id=<id>)` — confirm the
>    dataset exists and list its real variable names.
> 4. Only then `fetch_data_product(...)` (opt-in network download; keep the window
>    narrow). See [`tool-examples.md`](tool-examples.md) and the metadata-first /
>    opt-in fetch rules in [`../../../docs/safety.md`](../../../docs/safety.md).

The canonical fetch pattern is:

```text
fetch_data_product(
    source_type="cdaweb",
    dataset_id="<CONFIRMED_DATASET_ID>",
    parameters=["<var1>", "<var2>"],
    trange=["<start>", "<stop>"],   # narrow window
)
```

Always `browse_data_parameters` first to get the **exact** variable names — they vary
by level/rate and are easy to guess wrong.

---

## MMS — Magnetospheric Multiscale (4 spacecraft, `mms1`–`mms4`)

**Instruments:** FGM (fluxgate mag), SCM (search-coil), EDP (E-field double probe),
EDI (electron drift), FPI (Fast Plasma Investigation: DIS ions / DES electrons),
HPCA (ion composition), EIS / FEEPS (energetic particles), ASPOC (potential control).
pyspedas: `pyspedas.projects.mms`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| FGM survey L2 | `MMS1_FGM_SRVY_L2` | `mms1_fgm_b_gse_srvy_l2`, `..._b_gsm_srvy_l2` |
| FGM burst L2 | `MMS1_FGM_BRST_L2` | burst-cadence **B** vectors |
| FPI DIS (ions) moments, fast | `MMS1_FPI_FAST_L2_DIS-MOMS` | number density, bulk velocity, temperature |
| FPI DES (electrons) moments, fast | `MMS1_FPI_FAST_L2_DES-MOMS` | electron moments |
| FPI distributions (burst) | `MMS1_FPI_BRST_L2_DIS-DIST` / `..._DES-DIST` | 3D distributions for `compute_particle_*` |
| EDP E-field | `MMS1_EDP_FAST_L2_DCE` | DC E-field |

Notes: data rates are `srvy`/`fast`/`brst`; pick `brst` only for short, science-rich
intervals. Distributions (`*-DIST`) feed the proposed particle tools
(`compute_particle_moments` / `compute_particle_spectra`); moments (`*-MOMS`) are
pre-computed. Replace `MMS1`/`mms1` with the probe you need.

## THEMIS / ARTEMIS (5 probes `tha`–`the`; `thb`/`thc` = ARTEMIS at the Moon)

**Instruments:** FGM (fluxgate), SCM (search-coil), EFI (E-field), ESA (electrostatic
analyzer, ions+electrons), SST (solid-state telescope, energetic), plus ground
magnetometer (GMAG) and all-sky imager (ASI) arrays. pyspedas: `pyspedas.projects.themis`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| FGM L2 | `THA_L2_FGM` | `tha_fgs_gse`, `tha_fgs_gsm`, `tha_fgl_*` |
| ESA L2 (plasma moments) | `THA_L2_ESA` | density, velocity, temperature |
| SST L2 (energetic) | `THA_L2_SST` | energetic ion/electron fluxes |
| Ground magnetometer | `THG_L2_MAG_<SITE>` | ground **B** (substorm onset, Pi2) |

Notes: probe letter (`a`–`e`) selects the spacecraft; ground arrays (`THG_*`) are keyed
by station code. For substorm timing combine a ground GMAG chain with probe FGM/ESA —
see [`themis-substorm-workflow.md`](themis-substorm-workflow.md).

## PSP — Parker Solar Probe

**Instruments:** FIELDS (MAG + electric fields + RFS radio), SWEAP (SPC Faraday cup,
SPAN-i ions, SPAN-e electrons), IS☉IS (energetic particles). pyspedas:
`pyspedas.projects.psp`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| FIELDS MAG (RTN) | `PSP_FLD_L2_MAG_RTN` | **B** in RTN |
| FIELDS MAG (1-min) | `PSP_FLD_L2_MAG_RTN_1MIN` | downsampled **B** for survey |
| SWEAP SPC moments | `PSP_SWP_SPC_L3I` | proton density, velocity, temperature |
| SWEAP SPAN-i ions | `PSP_SWP_SPI_SF00_L3_MOM` | ion moments |

Notes: PSP fields are usually in **RTN**; state the frame explicitly. Use the `1MIN`
products for context/survey and full-cadence only on perihelion-science windows.

## Wind & ACE — upstream solar-wind monitors (L1)

**Wind instruments:** MFI (mag), SWE (plasma), 3DP (particles).
**ACE instruments:** MAG, SWEPAM (plasma), EPAM/SIS/ULEIS (energetic).
pyspedas: `pyspedas.projects.wind`, `pyspedas.projects.ace`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| Wind MFI | `WI_H0_MFI` (or `WI_H2_MFI` high-res) | `BGSE`, `BGSM` |
| Wind SWE plasma | `WI_K0_SWE` / `WI_H1_SWE` | proton density, speed, thermal speed |
| ACE MAG | `AC_H0_MFI` | `BGSEc`, magnitude |
| ACE SWEPAM plasma | `AC_H0_SWE` | proton density, bulk speed, temperature |

Notes: these are upstream **L1** monitors — apply a propagation lag to Earth and record
the lag/coordinate assumptions as caveats (see the upstream-solar-wind example in
[`science-examples.md`](science-examples.md)). For a pre-merged, time-shifted upstream
series prefer OMNI below.

## OMNI — merged, time-shifted near-Earth solar wind

**Source:** merged multi-spacecraft solar-wind + IMF + indices, propagated to the bow
shock nose. pyspedas: `pyspedas.projects.omni`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| OMNI 1-min (HRO2) | `OMNI_HRO2_1MIN` | `BX_GSE`, `BY_GSM`, `BZ_GSM`, flow speed, density, `SYM_H`, `AE` |
| OMNI 5-min | `OMNI_HRO2_5MIN` | same fields, 5-min cadence |

Notes: OMNI is already time-shifted to Earth — preferred for driver/context. Indices
(`SYM_H`, `AE`, `Kp`) live here and gate storm/substorm event selection.

## RBSP — Van Allen Probes (`rbspa`, `rbspb`)

**Instruments:** EMFISIS (MAG + waves), EFW (E-field/spacecraft potential), ECT suite
(MagEIS, REPT, HOPE — energetic/ring-current particles), RBSPICE. pyspedas:
`pyspedas.projects.rbsp`.

| Product | CDAWeb dataset ID (verify) | Typical variables |
|---|---|---|
| EMFISIS MAG L3 | `RBSP-A_MAGNETOMETER_4SEC-GSM_EMFISIS-L3` | **B** (GSM), magnitude |
| ECT MagEIS L3 | `RBSPA_REL04_ECT-MAGEIS-L3` | energetic electron/ion flux vs. energy |
| ECT REPT L3 | `RBSPA_REL04_ECT-REPT-SCI-L3` | relativistic electron flux |
| ECT HOPE moments | `RBSPA_REL04_ECT-HOPE-MOM-L3` | low-energy ion/electron moments |

Notes: dataset IDs here are especially release-string sensitive (`REL04`, frame/cadence
suffixes) — **always confirm via `browse_data_parameters`**. Radiation-belt analysis maps
flux to L-shell; see [`rbsp-radiation-belt-workflow.md`](rbsp-radiation-belt-workflow.md)
and the proposed `calculate_lshell` tool (`spedas_agent_kit #17`).

---

## Other missions (loader exists; look up IDs on demand)

pyspedas hosts ~38 mission loaders under `pyspedas/projects/`. Beyond the high-value
set above, common ones include **Cluster** (4 s/c, curlometer), **Geotail**, **STEREO**,
**MAVEN**, **Polar**, **DE2**, **ELFIN**, **ERG/Arase**, **Swarm**, **GOES**. For any of
these, run the discovery steps (`browse_data_sources` → `load_data_source` →
`browse_data_parameters`) to get current dataset IDs rather than guessing.

## Reminders

- **Confirm IDs and variable names** with `browse_data_parameters` before fetching;
  the tables above are starting guesses, not guarantees.
- **Keep fetch windows narrow** and treat `fetch_data_product` as an opt-in network
  download (archive rate limits apply).
- **Record the dataset ID, variables, frame, and cadence** in provenance
  ([`artifact-provenance.md`](artifact-provenance.md)).
