# SPEDAS science workflow

For a science request, call:

1. `search_spedas_data_sources` for candidate sources.
2. `plan_spedas_observation` for target/interval/source choices.
3. `compare_cdaweb_pds_spice` if the archive choice is unclear.
4. `create_spedas_analysis_bundle` to record a reusable plan/provenance scaffold.

Report assumptions, interval, source_type, source_id/dataset_id, parameters, and
remaining validation needed before real downloads.
