# SPEDAS geometry / SPICE workflow

Use SPICE through the unified data layer when possible (`source_type="spice"`).
For geometry tasks, first discover supported missions/kernels, then create a
plan that separates geometry lookup from measurement-data fetches. Avoid large
kernel downloads without confirming cache and scope.
