# Contributing to spedas-claude

Thanks for helping improve the SPEDAS Claude Code plugin. This repo is a **thin
wrapper** around the official [SPEDAS Agent Kit MCP server](https://github.com/spedas/spedas_agent_kit):
it packages the MCP connection, a workflow skill, and slash commands. It does
**not** contain the scientific tooling itself.

## Where to file what

Knowing which layer a problem lives in saves everyone triage time. There are two:

| Symptom | Layer | Where it belongs |
|---|---|---|
| Plugin won't load, a command/skill/doc is wrong, MCP wiring (`.mcp.json`) is broken, CI/packaging issue | **plugin wrapper** (this repo) | [Open an issue here](https://github.com/spedas/spedas_claude/issues) |
| A `spedas_*` MCP tool returns wrong data, crashes, or is missing | **science tooling** | [spedas/spedas_agent_kit](https://github.com/spedas/spedas_agent_kit/issues) |
| `ModuleNotFoundError: pyspedas`, PySPEDAS recipe fails in your Python env | **your environment** | This is expected — the plugin does not install PySPEDAS. See the README "two layers" section. |

When in doubt, file here and we will redirect.

## Naming

Three names refer to this project, on purpose — please keep them consistent:

- **`spedas-claude`** — the plugin manifest `name`
  (`.claude-plugin/plugin.json`). Claude Code uses this identifier. The
  validator (`scripts/validate_plugin.py`) enforces it.
- **`spedas_claude`** — the repository / Python-style identifier
  (`github.com/spedas/spedas_claude`).
- **"SPEDAS Claude Code plugin"** — the human-readable README title.

Do not "fix" one into another; they are the manifest, the repo, and the prose
title respectively.

## Development setup

You need Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (for the runtime
smoke). No other dependencies — the validators are pure-Python and offline.

```bash
git clone https://github.com/spedas/spedas_claude.git
cd spedas_claude

# Offline packaging validation (fast, runs on every OS in CI):
python scripts/validate_plugin.py
python scripts/test_validate_plugin.py
python scripts/test_smoke_groups.py

# Runtime smoke: launches the real spedas-agent-kit server (needs uv + network):
python scripts/smoke_mcp_runtime.py --json --timeout 300
```

## Before you open a PR

1. Run the four commands above; they must all pass. CI runs the first three on
   `{ubuntu, macos, windows} × {3.11, 3.12, 3.13}` and the smoke on Linux.
2. Run `git diff --check` to catch whitespace errors.
3. If you change behavior, add or update a test (`scripts/test_*.py`) and a
   `CHANGELOG.md` entry under **[Unreleased]**.
4. Fill in the pull request template (affected tools, platform/version, repro).

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

Do **not** file security issues as public GitHub issues. See
[SECURITY.md](SECURITY.md) for responsible disclosure.
