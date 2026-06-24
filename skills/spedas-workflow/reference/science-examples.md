# Starter science examples

## MMS magnetopause

Question: identify magnetic-field/plasma signatures around 2015-10-16T13:06Z.

Start with `plan_spedas_observation` for MMS and CDAWeb. Then inspect FGM/FPI variables before any fetch.

## Juno PDS + SPICE

Question: plan a Juno magnetic-field analysis near Jupiter with geometry context.

Start with `compare_cdaweb_pds_spice` or `plan_spedas_observation` with sources `pds` and `spice`. Load PDS mission metadata before fetch.

## PSP perihelion

Question: plan solar-wind context near a Parker Solar Probe perihelion.

Use CDAWeb for fields/plasma metadata and SPICE for heliocentric geometry planning.

## THEMIS substorm

Question: compare magnetotail field/plasma signatures over a narrow interval.

Use CDAWeb discovery first; then decide probe(s), cadence, and variables.

## Upstream solar wind comparison

Question: compare ACE/Wind/OMNI context for a magnetospheric event.

Use CDAWeb/OMNI discovery and record propagation/coordinate assumptions as caveats.
