# Opt-in example: PreToolUse fetch/kernel guard

> **Disabled by default. This is NOT active.** Nothing here runs unless *you* copy
> it into `hooks/hooks.json`. The shipped `hooks/hooks.json` is an intentional empty
> placeholder (see [`../../docs/safety.md`](../../docs/safety.md)).

## What it does

A `PreToolUse` hook that fires before current network-download tools and before
geometry tools when `allow_kernel_download=True`. It prints a **warning to
context**; it does not block, mutate state, or download anything.

It matches:

- `mcp__spedas__fetch_data_product`
- `mcp__spedas__fetch_hapi_data`
- `mcp__spedas__fetch_fdsn_data`
- `mcp__spedas__get_ephemeris`
- `mcp__spedas__compute_distance`
- `mcp__spedas__transform_coordinates`

For geometry tools, the script warns only when the input includes
`allow_kernel_download: true`; metadata/cache-gated calls remain quiet.

## How to enable it

1. Copy the JSON below into `hooks/hooks.json` (replace the empty `{"hooks": []}`).
2. Re-run `python3 scripts/validate_plugin.py` to confirm the hooks file is still valid.
3. Reload the plugin in Claude Code.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__spedas__fetch_data_product|mcp__spedas__fetch_hapi_data|mcp__spedas__fetch_fdsn_data|mcp__spedas__get_ephemeris|mcp__spedas__compute_distance|mcp__spedas__transform_coordinates",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/examples/fetch_guard.py"
          }
        ]
      }
    ]
  }
}
```

The companion script is [`fetch_guard.py`](fetch_guard.py). It reads the standard
Claude Code hook JSON on stdin, emits a single-line reminder to stderr, and exits
`0` (non-blocking).
