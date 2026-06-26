---
description: Summarize the SPEDAS MCP layers and recommend the next tools for a science question.
argument-hint: [free-text science question]
---

# SPEDAS overview

Use `spedas_overview` first. Summarize the MCP layers, then recommend the next
one or two tools for the user's science question. Prefer the unified data layer
and science workflow tools over compatibility low-level tools.

## Invocation arguments

User-supplied arguments (may be empty): `$ARGUMENTS`

Treat `$ARGUMENTS` as the free-text science question to orient the overview. If
it is empty, give the general overview and ask what the user wants to do next.
