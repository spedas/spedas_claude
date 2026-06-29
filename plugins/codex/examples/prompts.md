# Example prompts

## Overview

```text
Use SPEDAS to explain what data sources are available and which tool I should use
first for a solar-wind interval near Earth.
```

Expected flow: `spedas_overview` -> `search_spedas_data_sources` -> optional
`plan_spedas_observation`.

## MMS interval planning

```text
Plan an MMS analysis for 2015-10-16 13:00-14:00 UTC. Do not download data yet;
choose candidate CDAWeb/PDS/SPICE sources and list the next safe MCP calls.
```

Expected flow: workflow tools first, then unified data-layer browse/load calls.

## Juno / Jupiter comparison

```text
Compare CDAWeb, PDS, and SPICE for a Juno magnetic-field analysis near Jupiter.
Tell me which source_type should be used for measurements and which for geometry.
```

Expected flow: `compare_cdaweb_pds_spice`, then source-specific data-layer calls.
