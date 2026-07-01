# Environment & cache configuration

This document lists **every environment variable** the `spedas_claude` plugin and
the `spedas` MCP server actually respect, grouped by how often you need them. It
addresses issues #5 (cross-platform cache paths / `${HOME}` expansion) and #17
(documenting the configurable variables and explaining the leaked `XHELIO_*` /
`PDSMCP_*` names).

Everything here was verified against the current `spedas_agent_kit` server entrypoint
and the `xhelio-cdaweb` / `xhelio-pds` / `xhelio-spice` backends — these are the
*only* variables those code paths read. No variable is invented; if the server
does not read it, it is not listed.

## TL;DR

- **You usually need to set nothing.** The packaged `.mcp.json` already points the
  three cache directories at `${HOME}/.cache/spedas/...`. If those defaults work
  for you, skip the rest.
- The variable **names are fixed by the upstream server** (`spedas_agent_kit`) and its
  backends. We cannot rename them to drop the `XHELIO_*` / `PDSMCP_*` prefixes
  without breaking the server. They are documented here so the leak is explained
  rather than surprising — see [Naming](#naming-why-you-see-xhelio_-and-pdsmcp_).

## 1. Mandatory setup

**None.** No environment variable is required. `uvx` resolves `spedas_agent_kit` on first
run, and each backend falls back to a sensible default cache directory if you set
nothing (see the defaults column below). The only hard requirement is `uv`/`uvx`
on `PATH` (see the README Requirements section).

## 2. Optional: cache & kernel isolation

These three variables redirect where the server stores downloaded/cached data.
Set them when you want caches off your home directory (HPC scratch, a shared
volume, a project-local cache, or an air-gapped mirror). Each can be set either as
an environment variable **or** as a server CLI flag in `.mcp.json`'s `args`.

| Purpose | Environment variable | Equivalent server CLI flag | Default if unset |
|---|---|---|---|
| CDAWeb cache root | `XHELIO_CDAWEB_CACHE_DIR` | `--cdaweb-cache-dir` | `~/.cdawebmcp/` |
| PDS (PPI) cache root | `PDSMCP_CACHE_DIR` | `--pds-cache-dir` | `~/.pdsmcp/` |
| SPICE kernel cache | `XHELIO_SPICE_KERNEL_DIR` | `--spice-kernel-dir` | `~/.xhelio_spice/kernels/` |

> **The "Default if unset" column shows the bare upstream-tool defaults, which apply
> only if you remove the corresponding env vars from the packaged `.mcp.json`.** Out
> of the box those vars are set, so the packaged setup actually caches under
> `${HOME}/.cache/spedas/...` (see the `.mcp.json` block below), **not** under
> `~/.cdawebmcp/` / `~/.pdsmcp/` / `~/.xhelio_spice/kernels/`.

The packaged [`.mcp.json`](../.mcp.json) sets all three under one tree:

```jsonc
"env": {
  "XHELIO_CDAWEB_CACHE_DIR": "${HOME}/.cache/spedas/cdaweb",
  "PDSMCP_CACHE_DIR":        "${HOME}/.cache/spedas/pds",
  "XHELIO_SPICE_KERNEL_DIR": "${HOME}/.cache/spedas/spice/kernels"
}
```

Notes that matter for reproducibility:

- The **CDAWeb backend bootstraps** bundled observatory + metadata files into its
  cache root on first access. Pointing `XHELIO_CDAWEB_CACHE_DIR` at a fresh empty
  directory is fine — it is populated automatically. A read-only cache root will
  fail this bootstrap; rerun the smoke command with `--json` and keep the compact error payload for issue triage.
- A **resolution-order** subtlety: a CLI flag in `.mcp.json` `args` wins over the
  environment variable of the same purpose (the server reads
  `args.<flag> or os.environ.get(<VAR>)`). Pick one mechanism per directory.

### `${HOME}` expansion and Windows

`${HOME}` in `.mcp.json` is only useful if **something expands it**. Two cases:

- **POSIX shells (macOS/Linux/WSL):** `${HOME}` is set and expands normally.
- **Native Windows:** `HOME` is typically *unset* (Windows uses `USERPROFILE`). If
  Claude Code passes the env value through without expanding it, the server can
  receive the literal string `${HOME}/.cache/...` or a wrong `/.cache/...` root,
  silently disabling caching (data and kernels re-download every run, risking
  archive rate limits).

Because Claude Code's env-expansion behavior across platforms is **not something
this repo can guarantee**, the safe, portable approach on any OS is to set an
**absolute path** you control. Examples:

```jsonc
// macOS / Linux — absolute, no expansion needed:
"XHELIO_CDAWEB_CACHE_DIR": "/Users/you/.cache/spedas/cdaweb"

// Windows — absolute, forward slashes are accepted by the Python/loader paths:
"XHELIO_CDAWEB_CACHE_DIR": "C:/Users/you/AppData/Local/spedas/cdaweb"
```

To **verify** what the server actually resolved, run the offline cache-path
diagnostic — it expands the `.mcp.json` cache vars against *your current
environment* without starting the server, downloading anything, or writing to disk,
and tells you whether `${HOME}` actually resolved on your OS:

```bash
# Works on macOS / Linux / Windows. Exits non-zero if any cache path stayed an
# unresolved literal (e.g. a bare ${HOME} on native Windows where HOME is unset).
python scripts/smoke_mcp_runtime.py --cache-diagnostics
```

It prints, per variable, the **raw** configured value, the **expanded** value, any
**unresolved** `${HOME}` / `%USERPROFILE%` tokens, and path-flavor caveats (e.g.
mixed `\`/`/` separators on a Windows drive path). If a line shows
`UNRESOLVED: ${HOME}`, switch that directory to an **absolute path** as shown above.
CI runs this same check on `ubuntu-latest`, `macos-latest`, and `windows-latest`
(see `.github/workflows/validate.yml`), and the pure cross-platform behaviour is
self-tested in `scripts/test_cache_paths.py`.

You can also run the full runtime smoke and inspect the directories it reports /
creates, or check that the cache directory fills after a real (opt-in) fetch. If
the cache stays empty across runs, expansion or writability is the likely cause
(rerun the smoke command with `--json` and check the expanded cache paths before assuming the archive is empty).

## 3. Advanced: runtime / developer / debug knobs

These are not specific to SPEDAS — they are standard `uv` and OS variables that
control where the *toolchain* caches and writes temp files. `scripts/smoke_mcp_runtime.py`
manages them to stay hermetic; document/set them yourself for HPC or air-gapped
runs. They are read by `uv`/the OS, not by `spedas_agent_kit` code.

| Variable | What it controls | When to set it |
|---|---|---|
| `UV_CACHE_DIR` | Where `uv`/`uvx` caches the resolved `spedas_agent_kit` environment | Redirect off `$HOME` on HPC; pre-populate for air-gapped/offline use |
| `XDG_CACHE_HOME` | XDG cache root that several tools honor | Same as above on Linux-like systems |
| `TMPDIR` | Temp directory for the subprocess | Read-only/again-quota `/tmp`; large intermediate files |

The runtime smoke only *overrides* these when the default location is not writable,
and only for its own subprocess — it never mutates your shell. For a fully offline
deployment, pre-warm `UV_CACHE_DIR` once with network access:

```bash
UV_CACHE_DIR=/shared/uv-cache \
  uvx --from "git+https://github.com/spedas/spedas_agent_kit.git@8fcfc7dd0e6f01800f301590ed8213eb33683582" spedas-agent-kit --help
```

then point `.mcp.json`'s process at the same `UV_CACHE_DIR`.

## Naming: why you see `XHELIO_*` and `PDSMCP_*`

The plugin's public mental model is a **unified SPEDAS data layer** (`cdaweb` /
`pds` / `spice`), and the docs say the lower-level `xhelio-*` packages are an
implementation detail. The environment-variable names are the one place that
abstraction leaks, because **the names are defined and read by the upstream
backends, not by this plugin**:

- `XHELIO_CDAWEB_CACHE_DIR`, `XHELIO_SPICE_KERNEL_DIR` — read by `xhelio-cdaweb` /
  `xhelio-spice`.
- `PDSMCP_CACHE_DIR` — read by `xhelio-pds` (its module is `pdsmcp`).

This plugin **cannot alias them** to neutral names without the server changing
first: if you rename the variable, the server simply won't read it and silently
falls back to the default cache. So treat these names as fixed upstream identifiers.
If `spedas_agent_kit` later exposes neutral aliases, this document should be updated to
prefer them. Until then, the SPEDAS-facing wording is "cache/kernel directory";
the `XHELIO_*` / `PDSMCP_*` strings are just the keys the server happens to read.

## Where caches are *not* configured

`manage_data_cache(... cache_dir=...)` does **not** override the backend cache root
per call — cache roots are fixed by the server/environment at startup (the unified
tool returns a note saying so). Configure caches via the variables above, not via
per-call arguments.

## See also

- [`../.mcp.json`](../.mcp.json) — the packaged defaults.
- [`dependencies.md`](dependencies.md) — pinning the `spedas_agent_kit` source for reproducibility.
- [`safety.md`](safety.md) — the fetch/kernel safety boundary (what fills these caches and when).
- [`../skills/spedas-skills-index/SKILL.md`](../skills/spedas-skills-index/SKILL.md) — choosing the right shared SPEDAS skill.
- [`../skills/spedas-workflow/SKILL.md`](../skills/spedas-workflow/SKILL.md) — default artifact-first workflow guardrails.
