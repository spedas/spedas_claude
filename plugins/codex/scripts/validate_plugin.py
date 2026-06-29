#!/usr/bin/env python3
"""Validate the SPEDAS Agent Kit Codex runtime module without network access."""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED_REF_RE = re.compile(r"git\+https://github\.com/spedas/spedas_mcp\.git@[^\s]+$")


def fail(message: str) -> None:
    raise SystemExit(message)


def require(path: str) -> Path:
    p = ROOT / path
    if not p.exists():
        fail(f"missing required file: {path}")
    if p.is_file() and p.stat().st_size == 0:
        fail(f"empty required file: {path}")
    return p


def load_json(path: str) -> dict:
    p = require(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report cleanly.
        fail(f"invalid JSON in {path}: {exc}")
        return {}


def validate_mcp() -> None:
    data = load_json(".mcp.json")
    servers = data.get("mcp_servers") or data.get("mcpServers")
    if not isinstance(servers, dict) or "spedas" not in servers:
        fail(".mcp.json must define a spedas MCP server")
    server = servers["spedas"]
    if server.get("command") != "uvx":
        fail("expected MCP command uvx for portable install")
    args = server.get("args") or []
    joined = " ".join(str(arg) for arg in args)
    if "github.com/spedas/spedas_mcp" not in joined or "spedas-mcp" not in joined:
        fail("spedas MCP server must install/run github.com/spedas/spedas_mcp spedas-mcp")
    if not any(str(arg).startswith("mcp>=") or str(arg).startswith("mcp~=") or str(arg).startswith("mcp==") for arg in args):
        fail(".mcp.json must include an explicit MCP protocol dependency")
    if "mcp>=1.26.0,<2" not in args:
        fail(".mcp.json must bound the MCP protocol dependency, e.g. mcp>=1.26.0,<2")
    try:
        from_value = args[args.index("--from") + 1]
    except (ValueError, IndexError):
        fail(".mcp.json must pass --from spedas-mcp[analysis] @ git+...@<sha> to uvx")
    normalized = " ".join(str(from_value).split())
    if "spedas-mcp[analysis] @ " not in normalized:
        fail("Codex module must request the spedas-mcp[analysis] extra for analysis tools")
    git_url = normalized.split(" @ ", 1)[1] if " @ " in normalized else normalized
    if not PINNED_REF_RE.search(git_url):
        fail("Codex module spedas_mcp source must be pinned to a commit or tag")


def validate_skill_links() -> None:
    skill = require("skills/spedas-workflow/SKILL.md")
    text = skill.read_text(encoding="utf-8")
    for rel in re.findall(r"\((reference/[^)]+)\)", text):
        require(f"skills/spedas-workflow/{rel}")


def validate_markdown_links() -> None:
    broken: list[str] = []
    for md in ROOT.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            raw = match.group(1).split("#", 1)[0].strip()
            if not raw or "://" in raw or raw.startswith("mailto:"):
                continue
            target = (md.parent / urllib.parse.unquote(raw)).resolve()
            if not target.exists():
                broken.append(f"{md.relative_to(ROOT)} -> {match.group(1)}")
    if broken:
        fail("broken Codex module markdown links:\n" + "\n".join(broken[:20]))


def main() -> int:
    require("README.md")
    require("LICENSE")
    require("AGENTS.md")
    require("examples/prompts.md")
    manifest = load_json(".codex-plugin/plugin.json")
    if manifest.get("name") != "spedas-codex":
        fail("Codex plugin name must stay spedas-codex for compatibility")
    validate_mcp()
    validate_skill_links()
    validate_markdown_links()
    print("SPEDAS Agent Kit Codex module validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
