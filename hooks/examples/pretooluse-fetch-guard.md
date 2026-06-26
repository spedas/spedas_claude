# Opt-in example: PreToolUse fetch/kernel guard

> **Disabled by default. This is NOT active.** Nothing here runs unless *you* copy
> it into `hooks/hooks.json`. The shipped `hooks/hooks.json` is an intentional empty
> placeholder (see [`../../docs/safety.md`](../../docs/safety.md)). This example
> exists so users who *want* a runtime warning before real fetches can enable one
> deliberately.

## What it does

A `PreToolUse` hook that fires before the network-download tools and prints a
**warning to context** (it does not block, does not mutate any state, does not
download anything). It nudges the model/user to confirm scope, cache, and rate
limits before a real fetch — turning the prose "plan-before-fetch" discipline into
a visible runtime reminder.

It matches these tools (the right-hand "opt-in" column in `docs/safety.md`):

- `mcp__spedas__fetch_data_product`
- `mcp__spedas__fetch_data`
- `mcp__spedas__fetch_pds_data`
- `mcp__spedas__manage_spice_kernels`

## Why it is not on by default

A hook changes the user's runtime behavior on every matching tool call. This plugin
should not alter that behavior without an explicit choice. The warning is harmless
(stderr text only), but enabling it is still your decision. It never blocks a call
or writes to disk — it only emits a reminder.

## How to enable it

1. Copy the JSON below into `hooks/hooks.json` (replace the empty `{"hooks": []}`).
2. Re-run `python3 scripts/validate_plugin.py` to confirm the hooks file is still valid.
3. Reload the plugin in Claude Code.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__spedas__fetch_data_product|mcp__spedas__fetch_data|mcp__spedas__fetch_pds_data|mcp__spedas__manage_spice_kernels",
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

The matcher is a regex over the tool name. `manage_spice_kernels` is matched for
*all* actions; the script itself notes that `action=status` is safe and only the
download/load paths actually hit the network, so the reminder is informational
there.

## The guard script

The companion script is [`fetch_guard.py`](fetch_guard.py). It reads the standard
Claude Code hook JSON on stdin, emits a single-line reminder to stderr, and exits
`0` (non-blocking). It performs **no** network access and writes **no** files. If
you want a *blocking* gate instead, change its exit code per the Claude Code hook
docs — but prefer keeping safety advisory unless you have a specific need.
