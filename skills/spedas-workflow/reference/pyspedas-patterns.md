# PySPEDAS patterns

> **These recipes need a local PySPEDAS install the plugin does not provide.**
> PySPEDAS and `pytplot` are *not* installed by `spedas_claude` and are *not*
> available in Claude's MCP tool runtime. Run them in your own Python environment
> after `pip install pyspedas` (or `uv pip install pyspedas`). A
> `ModuleNotFoundError: No module named 'pyspedas'` means PySPEDAS is missing from
> *that* environment — it is not a plugin bug. The MCP tool layer (see the rest of
> this skill folder) is the part this plugin wires up and needs no Python env of
> your own. See the README's "Architecture: two independent layers" section.

## Safe loading pattern

- Use a narrow `trange` first.
- Use mission-specific options (`probe`, `datatype`, `level`, `data_rate`) explicitly.
- Use `time_clip=True` when available.
- Print or inspect `tplot_names()` before assuming variable names.
- Keep cache/output roots explicit for reproducibility.

## Minimal examples

MMS FGM metadata-sized interval:

```python
import pyspedas
from pytplot import tplot_names
pyspedas.mms.fgm(
    trange=["2015-10-16/13:06", "2015-10-16/13:08"],
    probe="1",
    data_rate="srvy",
    level="l2",
    time_clip=True,
)
print(tplot_names())
```

OMNI upstream context:

```python
pyspedas.omni.data(trange=["2015-10-16", "2015-10-17"], level="hro", time_clip=True)
```

## Do not

- Do not paste large arrays into chat.
- Do not widen intervals until the loader/variables are proven.
- Do not treat missing variables as user error; classify metadata gaps and archive limitations.
