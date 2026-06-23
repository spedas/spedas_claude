# SPEDAS data-layer workflow

Use unified data-layer tools:

1. `browse_data_sources(source_type="all"|"cdaweb"|"pds"|"spice")`
2. `load_data_source(source_type, source_id)`
3. `browse_data_parameters(source_type, dataset_id, ...)`
4. `fetch_data_product(source_type, ...)` only after confirming scope/cache/output.
5. `manage_data_cache(source_type, ...)` for cache inspection or cleanup.

Keep fetches narrow. Return artifact paths and provenance, not large raw arrays.
