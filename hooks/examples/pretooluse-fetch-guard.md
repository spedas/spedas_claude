# Default PreToolUse fetch/kernel guard reference

This repository now ships the SPEDAS fetch/kernel guard **enabled by default** in
[`../hooks.json`](../hooks.json). This file is a reference copy for humans who want to
restore the default config after local edits, or for older plugin copies that still
pointed at the former example path.

## What it does

A `PreToolUse` hook fires before current network-download tools and before geometry
tools when `allow_kernel_download=True`. The companion script emits a Claude Code hook
JSON response with `permissionDecision: "ask"`, so the call pauses for explicit
permission instead of silently downloading data or kernels.

It matches:

- `mcp__spedas__fetch_data_product`
- `mcp__spedas__fetch_hapi_data`
- `mcp__spedas__fetch_fdsn_data`
- legacy `mcp__spedas__fetch_data`
- legacy `mcp__spedas__fetch_pds_data`
- legacy `mcp__spedas__manage_spice_kernels`
- `mcp__spedas__get_ephemeris`
- `mcp__spedas__compute_distance`
- `mcp__spedas__transform_coordinates`

For geometry tools, the script stays quiet unless the input includes
`allow_kernel_download: true`; metadata/cache status calls remain quiet.

## Default JSON

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__spedas__fetch_data_product|mcp__spedas__fetch_hapi_data|mcp__spedas__fetch_fdsn_data|mcp__spedas__fetch_data|mcp__spedas__fetch_pds_data|mcp__spedas__manage_spice_kernels|mcp__spedas__get_ephemeris|mcp__spedas__compute_distance|mcp__spedas__transform_coordinates",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/fetch_guard.py\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

The active companion script is [`../fetch_guard.py`](../fetch_guard.py). The local
[`fetch_guard.py`](fetch_guard.py) file in this directory is only a compatibility
wrapper that delegates to it.
