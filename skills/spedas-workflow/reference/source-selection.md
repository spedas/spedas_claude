# Source selection: CDAWeb, PDS, SPICE

Use the science need to choose source categories:

- **CDAWeb** — time-series space physics products, many mission variables, good for MMS/THEMIS/OMNI/ACE/Wind/PSP solar-wind or field/plasma data.
- **PDS** — planetary mission archives and instrument products, good for Juno/Cassini/planetary datasets where PDS labels/metadata matter.
- **SPICE** — geometry, spacecraft/planet positions, frames, kernels, and coordinate context. Use for planning or geometry; avoid kernel downloads unless explicitly allowed.

Common combinations:

- MMS magnetopause: CDAWeb first; SPICE only if geometry support is clearly available.
- Juno magnetic field near Jupiter: PDS + SPICE.
- PSP perihelion solar wind: CDAWeb + SPICE planning.
- Upstream solar wind comparison: CDAWeb/OMNI + ACE/Wind.

Always record source category, dataset/product id, parameter names, time range, and caveats.
