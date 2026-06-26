#!/usr/bin/env python3
"""Self-contained tests for scripts/validate_plugin.py.

Runs without pytest (plain ``python scripts/test_validate_plugin.py``) so CI does
not need extra deps. Each negative case copies the real plugin tree into a temp
dir, mutates one thing, and asserts the validator now fails. The positive case
asserts the unmodified tree passes.

The point of these tests is issue #15: prove the validator actually catches the
packaging mistakes it claims to (missing geometry.md, wrong MCP source, an
unresolvable declared resource path, broken skill frontmatter), not just that it
prints OK on a healthy repo.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_plugin.py"


def run_validator(plugin_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(plugin_root / "scripts" / "validate_plugin.py")],
        capture_output=True,
        text=True,
    )


def copy_plugin(dst: Path) -> Path:
    target = dst / "plugin"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    return target


def expect_pass(plugin_root: Path, label: str) -> None:
    proc = run_validator(plugin_root)
    assert proc.returncode == 0, f"[{label}] expected pass, got {proc.returncode}\n{proc.stderr}"
    assert "OK" in proc.stdout, f"[{label}] expected OK in stdout\n{proc.stdout}"
    print(f"PASS: {label}")


def expect_fail(plugin_root: Path, label: str, needle: str) -> None:
    proc = run_validator(plugin_root)
    assert proc.returncode != 0, f"[{label}] expected failure, got 0\n{proc.stdout}"
    assert needle in proc.stderr, f"[{label}] expected {needle!r} in stderr\n{proc.stderr}"
    print(f"PASS: {label} (correctly failed: {needle!r})")


def main() -> int:
    # Positive: the real tree must validate.
    expect_pass(ROOT, "healthy repo validates")

    with tempfile.TemporaryDirectory(prefix="spedas-validate-test-") as d:
        base = Path(d)

        # 1) Missing required command file commands/geometry.md.
        p = copy_plugin(base / "c1")
        (p / "commands" / "geometry.md").unlink()
        expect_fail(p, "missing geometry.md", "commands/geometry.md")

        # 2) Wrong MCP source repo.
        p = copy_plugin(base / "c2")
        mcp = p / ".mcp.json"
        data = json.loads(mcp.read_text())
        data["mcpServers"]["spedas"]["args"] = ["--from", "git+https://github.com/evil/x.git", "spedas-mcp"]
        mcp.write_text(json.dumps(data))
        expect_fail(p, "wrong MCP source", "github.com/spedas/spedas_mcp")

        # 3) Declared resource path that does not resolve relative to plugin root
        #    (this is exactly the issue #4 ambiguity made into a hard error).
        p = copy_plugin(base / "c3")
        manifest = p / ".claude-plugin" / "plugin.json"
        data = json.loads(manifest.read_text())
        data["skills"] = "./.claude-plugin/skills"
        manifest.write_text(json.dumps(data, indent=2))
        expect_fail(p, "unresolvable declared skills path", "skills")

        # 4) Broken skill frontmatter (no name field).
        p = copy_plugin(base / "c4")
        skill = p / "skills" / "spedas-workflow" / "SKILL.md"
        skill.write_text(skill.read_text().replace("name: spedas-workflow", ""))
        expect_fail(p, "skill missing name field", "name:")

        # 5) Empty hooks file is fine (placeholder), but malformed hooks fails.
        p = copy_plugin(base / "c5")
        (p / "hooks" / "hooks.json").write_text(json.dumps({"hooks": "not-an-object"}))
        expect_fail(p, "malformed hooks", "hooks")

    print("\nAll validator tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
