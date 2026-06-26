#!/usr/bin/env bash
# capture_environment.sh — write reproducibility-critical environment facts to stdout.
#
# Usage:
#   ./capture_environment.sh > environment.txt          # MCP-only run
#   ./capture_environment.sh --pyspedas > environment.txt  # also record local Python deps
#
# What it records:
#   - timestamp, OS/kernel/arch
#   - uv / uvx version (the toolchain that runs the MCP server)
#   - the resolved spedas_mcp upstream commit (lightweight `git ls-remote`, metadata
#     only — no clone, no fetch, no kernel download). Skipped gracefully if offline
#     or if SPEDAS_PROVENANCE_NO_NETWORK=1 is set.
#   - cache/kernel directories in effect (the XHELIO_*/PDSMCP_* env vars)
#   - with --pyspedas: local python version + pyspedas/pytplot/numpy versions
#
# It performs NO data fetch and NO SPICE kernel download. The only network call is
# the optional `git ls-remote` to resolve the spedas_mcp commit; disable it with
# SPEDAS_PROVENANCE_NO_NETWORK=1 for fully offline/air-gapped runs.
set -u

PYSPEDAS=0
[ "${1:-}" = "--pyspedas" ] && PYSPEDAS=1

SPEDAS_MCP_REPO="${SPEDAS_MCP_REPO:-https://github.com/spedas/spedas_mcp.git}"

echo "# SPEDAS provenance environment capture"
echo "captured_at: $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
echo "layer: $([ "$PYSPEDAS" -eq 1 ] && echo 'mcp + pyspedas' || echo 'mcp-only')"
echo

echo "## OS"
echo "uname: $(uname -a 2>/dev/null || echo unknown)"
echo

echo "## Toolchain (uv/uvx)"
if command -v uv >/dev/null 2>&1; then
  echo "uv: $(uv --version 2>/dev/null)"
else
  echo "uv: NOT FOUND on PATH"
fi
if command -v uvx >/dev/null 2>&1; then
  echo "uvx: present ($(command -v uvx))"
else
  echo "uvx: NOT FOUND on PATH"
fi
echo

echo "## Resolved spedas_mcp upstream commit"
echo "repo: ${SPEDAS_MCP_REPO}"
if [ "${SPEDAS_PROVENANCE_NO_NETWORK:-0}" = "1" ]; then
  echo "spedas_mcp_head: SKIPPED (SPEDAS_PROVENANCE_NO_NETWORK=1)"
elif command -v git >/dev/null 2>&1; then
  HEAD_LINE="$(git ls-remote "${SPEDAS_MCP_REPO}" HEAD 2>/dev/null | head -n1)"
  if [ -n "${HEAD_LINE}" ]; then
    echo "spedas_mcp_head: ${HEAD_LINE%%	*}"
  else
    echo "spedas_mcp_head: UNRESOLVED (offline or repo unreachable) — record manually"
  fi
else
  echo "spedas_mcp_head: git not available — record manually"
fi
echo "# NOTE: if .mcp.json pins '@<ref>', record that pinned ref here instead."
echo

echo "## Cache / kernel directories in effect"
echo "XHELIO_CDAWEB_CACHE_DIR: ${XHELIO_CDAWEB_CACHE_DIR:-<unset; server default ~/.cdawebmcp/>}"
echo "PDSMCP_CACHE_DIR: ${PDSMCP_CACHE_DIR:-<unset; server default ~/.pdsmcp/>}"
echo "XHELIO_SPICE_KERNEL_DIR: ${XHELIO_SPICE_KERNEL_DIR:-<unset; server default ~/.xhelio_spice/kernels/>}"
echo "UV_CACHE_DIR: ${UV_CACHE_DIR:-<unset; uv default>}"
echo

if [ "$PYSPEDAS" -eq 1 ]; then
  echo "## Local Python (PySPEDAS layer)"
  if command -v python3 >/dev/null 2>&1; then
    echo "python: $(python3 --version 2>&1)"
    python3 - <<'PY' 2>/dev/null || echo "pyspedas/pytplot: not importable in this python"
import importlib
for pkg in ("pyspedas", "pytplot", "numpy"):
    try:
        m = importlib.import_module(pkg)
        print(f"{pkg}: {getattr(m, '__version__', 'unknown')}")
    except Exception:
        print(f"{pkg}: NOT INSTALLED")
PY
  else
    echo "python3: NOT FOUND on PATH"
  fi
  echo
fi

echo "# End of capture. Review and fill any UNRESOLVED/manual fields above."
