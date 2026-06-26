# SPEDAS Claude Code plugin

`spedas_claude` is a standalone Claude Code plugin wrapper for the official
[SPEDAS MCP](https://github.com/spedas/spedas_mcp). It does not duplicate the
science tooling. Instead, it packages the MCP connection, a Claude-facing
workflow skill, and slash-command style prompts so Claude Code can use SPEDAS as
a heliophysics research assistant.

```text
Claude Code -> spedas_claude plugin -> spedas MCP server -> CDAWeb / PDS / SPICE backends
```

## Architecture: two independent layers (read this first)

This plugin touches **two layers that are installed and run differently**. Keeping
them straight avoids the most common "is this a plugin bug?" confusion.

| | MCP tool layer (this plugin wires it up) | PySPEDAS layer (you manage it) |
|---|---|---|
| What it is | The `spedas` MCP server's tools (`spedas_overview`, `browse_data_sources`, `get_ephemeris`, …) | The [PySPEDAS](https://github.com/spedas/pyspedas) Python package + `pytplot` |
| Who installs it | `uvx` resolves `spedas_mcp` automatically on first run (see `.mcp.json`) | **You**, in your own Python environment (`pip install pyspedas`) |
| Where it runs | A subprocess Claude Code starts; Claude calls it as MCP tools | Your local Python interpreter / notebook / script — **not** inside this plugin |
| What this repo provides | The MCP wiring, the workflow skill, and the slash commands | Only *recipes* and *patterns*; **no** PySPEDAS install |

**The plugin does not install PySPEDAS or `pytplot`, and Claude's tool runtime does
not provide them.** The PySPEDAS code blocks in the skill and in
[`reference/pyspedas-patterns.md`](skills/spedas-workflow/reference/pyspedas-patterns.md)
are recipes you run in *your own* Python environment. If you run them somewhere
without PySPEDAS installed you will get `ModuleNotFoundError: No module named
'pyspedas'` — that is an environment-scoping gap, not a plugin defect. Install it
with `pip install pyspedas` (or `uv pip install pyspedas`) in the environment
where you intend to run those recipes.

Most of this plugin's value is in the **MCP tool layer**, which needs no Python
environment of your own beyond `uvx`. Reach for the PySPEDAS layer only when you
explicitly want local Python/tplot workflows.

## What this repo provides

- `.claude-plugin/plugin.json` — plugin metadata and resource declarations.
- `.mcp.json` — starts the `spedas` MCP server from `spedas/spedas_mcp` via `uvx`.
- `skills/spedas-workflow/SKILL.md` — scientific workflow guidance for agents.
- `commands/` — Claude Code command prompts: `overview`, `data`, `workflow`, `geometry`.
  Each carries YAML frontmatter (`description`, `argument-hint`) and substitutes
  invocation arguments via `$ARGUMENTS`, so you can call them parameterized, e.g.
  `/geometry PSP HCI 2024-06-25` or `/data cdaweb mms1_fgm_srvy_l2`.
- `hooks/hooks.json` — placeholder for future safety/provenance hooks.
- `scripts/validate_plugin.py` — offline packaging validator (run in CI).
- `scripts/smoke_mcp_runtime.py` — real stdio MCP runtime smoke (verifies tool groups).
- `scripts/test_smoke_groups.py` — offline self-tests for the smoke's tool-group check.
- `skills/spedas-workflow/reference/` — per-tool examples, geometry/SPICE, and
  unified-vs-backend guides.

## Requirements

- Claude Code with plugin + MCP support.
- [`uv`/`uvx`](https://docs.astral.sh/uv/) available on `PATH`.
- Network access **the first time** `uvx` installs `spedas_mcp` from GitHub. After
  that, the resolved environment is cached by `uv`.
- Python 3.10+ for the validation scripts (the MCP server itself requires 3.10+).

### Optional (only for the PySPEDAS layer)

- [PySPEDAS](https://github.com/spedas/pyspedas) + `pytplot`, installed **by you**
  in your own Python environment (`pip install pyspedas`). This plugin does **not**
  install them and the MCP tool layer does **not** need them. See
  [Architecture: two independent layers](#architecture-two-independent-layers-read-this-first)
  above — the PySPEDAS recipes in the skill are for *your* local Python, not the
  plugin's runtime.

### Where the rest is documented

- Cache/temp/network **environment variables** (mandatory vs. optional vs. advanced):
  [`docs/configuration.md`](docs/configuration.md).
- **Fetch/kernel safety** boundary, opt-in language, and what to do before enabling
  real downloads: [`docs/safety.md`](docs/safety.md).
- **Failure taxonomy / triage runbook** (which error is which, where to file it):
  [`skills/spedas-workflow/reference/troubleshooting.md`](skills/spedas-workflow/reference/troubleshooting.md).
- **Provenance templates** for reproducible runs:
  [`templates/provenance/`](templates/provenance/).

## First-run flow

### 1. Clone

```bash
git clone https://github.com/spedas/spedas_claude.git
cd spedas_claude
```

### 2. Validate the packaging (offline, no network)

```bash
python scripts/validate_plugin.py
```

Expected success output:

```text
SPEDAS Claude plugin wrapper validation OK
  manifest: .claude-plugin/plugin.json
  skills:   skills
  commands: commands
```

This checks that every resource the plugin *advertises* in
`.claude-plugin/plugin.json` (skills, commands including `commands/geometry.md`,
hooks, and `.mcp.json`) actually resolves relative to the plugin root, that the
`spedas` MCP server points at `github.com/spedas/spedas_mcp`, and that skill
frontmatter is well-formed. It makes packaging mistakes fail loudly.

### 3. Runtime smoke (starts the real MCP server)

```bash
python scripts/smoke_mcp_runtime.py --json
```

This starts the configured `spedas` stdio MCP server via `uvx`, performs
`initialize` + `tools/list`, and verifies both the core SPEDAS tools **and** the
advertised tool groups (workflow, unified data layer, geometry/SPICE, CDAWeb and
PDS backends) are present — not just that the count is high enough. It uses
**no** private credentials, interactive UI, data fetch, or SPICE kernel
download, and isolates SPEDAS data/kernel caches in a temp directory. It still
uses your normal `uv` build cache unless you set `UV_CACHE_DIR` yourself; the
first run can be slow because `uvx` resolves `spedas_mcp` from GitHub.

Expected success (`ok: true`, `tool_count: 26`, empty `missing_core_tools`, empty
`missing_groups`):

```json
{
  "ok": true,
  "tool_count": 26,
  "missing_core_tools": [],
  "missing_groups": [],
  ...
}
```

Pass `--skip-group-check` to verify only the core tools (e.g. while a backend is
mid-migration). For copy-ready tool arguments and return shapes, see the skill
reference docs:
[`tool-examples.md`](skills/spedas-workflow/reference/tool-examples.md),
[`geometry-spice.md`](skills/spedas-workflow/reference/geometry-spice.md), and
[`backend-compatibility.md`](skills/spedas-workflow/reference/backend-compatibility.md).

To go one step further and actually *call* a workflow tool (not just list the
surface), run the example in [`examples/run_overview.py`](examples/run_overview.py).
It starts the same server and calls the read-only `spedas_overview` planning
tool — no credentials, no data fetch, SPEDAS data/kernel caches isolated — so
you can confirm the plugin works end to end and adapt it. The example still uses
your normal `uv` build cache unless you set `UV_CACHE_DIR` yourself:

```bash
python examples/run_overview.py            # human-readable summary
python examples/run_overview.py --json      # raw tool result
```

### 4. Use it from Claude Code

Enable the plugin (point Claude Code at this directory as a plugin dir), then try:

```text
Use SPEDAS to give me an overview of available data sources, then plan a small
MMS solar-wind interval analysis without downloading data yet.
```

Expected behavior:

1. Claude calls `spedas_overview`.
2. Claude uses workflow tools such as `search_spedas_data_sources` and
   `plan_spedas_observation`.
3. Claude prefers unified data-layer tools such as `browse_data_sources` and
   `load_data_source` before any real fetch.

A safe first live CLI check (metadata/planning only, no fetch):

```bash
claude -p \
  --plugin-dir . \
  --mcp-config .mcp.json \
  --allowedTools mcp__spedas__spedas_overview,mcp__spedas__browse_data_sources,mcp__spedas__plan_spedas_observation \
  "Use the SPEDAS MCP for a safe metadata-only MMS planning smoke. Do not fetch data or download kernels."
```

## How the plugin's resources are resolved

Claude Code loads a plugin's resources by **convention** and by **explicit
declaration**:

- By convention, Claude Code auto-discovers root-level `commands/`, `skills/`,
  `hooks/hooks.json`, and `.mcp.json`.
- When `.claude-plugin/plugin.json` declares path keys (`skills`, `commands`,
  `hooks`, `mcpServers`) — as this plugin does — **those paths are resolved
  relative to the plugin root** (the directory that contains `.claude-plugin/`),
  not relative to the `.claude-plugin/` directory.

So `"skills": "./skills"` means `<plugin-root>/skills`, and the directories in
this repo live at the root accordingly. `scripts/validate_plugin.py` enforces
this: any declared resource that does not resolve to an existing file/dir under
the plugin root is a hard error.

> If a future version of Claude Code changes this resolution rule, the validator
> is the single place to update — it encodes the assumption explicitly rather
> than leaving it implicit in the layout.

## How `spedas_mcp` is resolved (reproducibility)

`.mcp.json` installs and runs the MCP server with:

```jsonc
"command": "uvx",
"args": ["--with", "mcp>=1.26.0",
         "--from", "git+https://github.com/spedas/spedas_mcp.git",
         "spedas-mcp"]
```

- **Source:** the official `git+https://github.com/spedas/spedas_mcp.git`,
  default branch. `uvx` resolves and caches it on first run.
- **MCP protocol dependency:** `mcp>=1.26.0` (floor, matching `spedas_mcp`'s own
  `pyproject.toml`).
- **Entry point:** the `spedas-mcp` console script.

This default intentionally **floats** on the `spedas_mcp` default branch so a
plain clone + smoke works without coordinating tags across two repos. For a fully
reproducible/pinned deployment, append an exact git ref to the `--from` URL, e.g.

```jsonc
"--from", "git+https://github.com/spedas/spedas_mcp.git@<commit-or-tag>"
```

See [`docs/dependencies.md`](docs/dependencies.md) for the recorded resolved
source/HEAD and the exact pinning recipe, and the caveat about which ref to pin.

## Local validation (summary)

```bash
python scripts/validate_plugin.py        # offline packaging validation
python scripts/test_validate_plugin.py   # validator self-tests (negative cases)
python scripts/test_smoke_groups.py      # offline tool-group check self-tests
python scripts/smoke_mcp_runtime.py --json  # real MCP runtime smoke (needs uvx + first-run network)
```

CI (`.github/workflows/validate.yml`) runs all three.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `validate_plugin.py` reports a declared path does not resolve | a resource was moved/renamed but `.claude-plugin/plugin.json` still points at the old path, or the path was written relative to `.claude-plugin/` | move the resource to the plugin root, or correct the path key (paths are plugin-root-relative) |
| `validate_plugin.py`: `spedas server must install from github.com/spedas/spedas_mcp` | `.mcp.json` points at a fork/wrong repo | restore the official `--from` URL |
| `smoke_mcp_runtime.py` hangs or times out on first run | `uvx` is resolving `spedas_mcp` from GitHub with no/blocked network | ensure network access for the first run; raise `--timeout`; pre-warm with `uvx --from git+https://github.com/spedas/spedas_mcp.git spedas-mcp --help` |
| `smoke_mcp_runtime.py`: `command not found: uvx` | `uv` not installed / not on `PATH` | install `uv` via the official uv installation guide: https://docs.astral.sh/uv/getting-started/installation/ |
| `missing_core_tools` non-empty | the resolved `spedas_mcp` version changed its tool surface | confirm the `spedas_mcp` HEAD; pin a known-good ref (see dependencies doc) |
| Claude Code does not see the slash commands/skill | plugin dir not enabled, or resources not at the plugin root | re-enable the plugin dir; run `validate_plugin.py` to confirm layout |

## Relationship to `spedas_mcp`

The runtime tools live in `spedas_mcp`. This plugin is a thin Claude Code shell.
The public mental model is a unified SPEDAS data layer organized by data source
(`cdaweb`, `pds`, `spice`), plus a science workflow layer. The lower-level
`xhelio-*` packages are implementation details of `spedas_mcp`.
