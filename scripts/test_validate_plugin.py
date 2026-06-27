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

        # 2b) Issue #3: an UNPINNED spedas_mcp git URL (no @ref) must fail — a
        #     floating default-branch HEAD is not reproducible.
        p = copy_plugin(base / "c2b")
        mcp = p / ".mcp.json"
        data = json.loads(mcp.read_text())
        data["mcpServers"]["spedas"]["args"] = [
            "--with", "mcp>=1.26.0,<2",
            "--from", "git+https://github.com/spedas/spedas_mcp.git",
            "spedas-mcp",
        ]
        mcp.write_text(json.dumps(data))
        expect_fail(p, "unpinned spedas_mcp source", "PINNED")

        # 2c) Issue #3: an MCP requirement with no upper bound must fail — a future
        #     breaking 2.x could be pulled silently.
        p = copy_plugin(base / "c2c")
        mcp = p / ".mcp.json"
        data = json.loads(mcp.read_text())
        data["mcpServers"]["spedas"]["args"] = [
            "--with", "mcp>=1.26.0",
            "--from", "git+https://github.com/spedas/spedas_mcp.git@4afdae39bda2ee11e27606809491b4d642e8ecc9",
            "spedas-mcp",
        ]
        mcp.write_text(json.dumps(data))
        expect_fail(p, "mcp requirement missing upper bound", "upper bound")

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

        # 6) Batch C: a cross-referenced repo doc must exist (#5/#17 config doc).
        p = copy_plugin(base / "c6")
        (p / "docs" / "configuration.md").unlink()
        expect_fail(p, "missing docs/configuration.md", "docs/configuration.md")

        # 7) Batch C: the safety doc (#6) must exist.
        p = copy_plugin(base / "c7")
        (p / "docs" / "safety.md").unlink()
        expect_fail(p, "missing docs/safety.md", "docs/safety.md")

        # 8) Batch C: the troubleshooting runbook (#13) must exist.
        p = copy_plugin(base / "c8")
        (p / "skills" / "spedas-workflow" / "reference" / "troubleshooting.md").unlink()
        expect_fail(p, "missing troubleshooting runbook", "troubleshooting.md")

        # 9) Batch C: a provenance template (#14) must exist.
        p = copy_plugin(base / "c9")
        (p / "templates" / "provenance" / "request.json").unlink()
        expect_fail(p, "missing provenance template", "templates/provenance/request.json")

        # 10) Batch C: the opt-in hook example (#6) must exist so the
        #     "enable it yourself" path documented in docs/safety.md is real.
        p = copy_plugin(base / "c10")
        (p / "hooks" / "examples" / "fetch_guard.py").unlink()
        expect_fail(p, "missing opt-in hook example", "hooks/examples/fetch_guard.py")

        # 11) Batch C: a malformed provenance JSON template must fail (a copy-paste
        #     run must start from valid JSON).
        p = copy_plugin(base / "c11")
        (p / "templates" / "provenance" / "request.json").write_text("{ not valid json ")
        expect_fail(p, "malformed provenance JSON template", "request.json")

        # 12) Batch F (#32): the pinning/reproducibility doc must exist — it is
        #     cross-linked from README/SKILL/troubleshooting/artifact-provenance.
        p = copy_plugin(base / "c12")
        (p / "docs" / "dependencies.md").unlink()
        expect_fail(p, "missing docs/dependencies.md", "docs/dependencies.md")

        # 12b) Issue #3: the root COMPATIBILITY.md anchor must exist.
        p = copy_plugin(base / "c12b")
        (p / "COMPATIBILITY.md").unlink()
        expect_fail(p, "missing COMPATIBILITY.md", "COMPATIBILITY.md")

        # 13) Batch F (#32): the documented first-run example must exist
        #     (advertised in README and CHANGELOG).
        p = copy_plugin(base / "c13")
        (p / "examples" / "run_overview.py").unlink()
        expect_fail(p, "missing examples/run_overview.py", "examples/run_overview.py")

        # 14) Batch F (#32): the advertised example must byte-compile, or the
        #     onboarding path is broken.
        p = copy_plugin(base / "c14")
        (p / "examples" / "run_overview.py").write_text("def main(:\n    pass\n")
        expect_fail(p, "example does not byte-compile", "byte-compile")

        # 15) Issue #11: a command file without YAML frontmatter must fail
        #     (the description never surfaces in Claude Code).
        p = copy_plugin(base / "c15")
        cmd = p / "commands" / "overview.md"
        text = cmd.read_text()
        body = text.split("---", 2)[2] if text.lstrip().startswith("---") else text
        cmd.write_text(body.lstrip())
        expect_fail(p, "command missing frontmatter", "YAML frontmatter")

        # 16) Issue #11: frontmatter present but no description: field must fail.
        p = copy_plugin(base / "c16")
        cmd = p / "commands" / "workflow.md"
        cmd.write_text(cmd.read_text().replace("description:", "summary:", 1))
        expect_fail(p, "command frontmatter missing description", "description:")

        # 17) Issue #11: a command that never references $ARGUMENTS must fail,
        #     because user-supplied parameters would silently be dropped.
        p = copy_plugin(base / "c17")
        cmd = p / "commands" / "data.md"
        cmd.write_text(cmd.read_text().replace("$ARGUMENTS", "the request"))
        expect_fail(p, "command missing $ARGUMENTS", "$ARGUMENTS")

        # 18) Issue #3: SSH userinfo (git@host) is not a ref pin.
        p = copy_plugin(base / "c18")
        mcp_json = json.loads((p / ".mcp.json").read_text())
        args = mcp_json["mcpServers"]["spedas"]["args"]
        args[args.index("--from") + 1] = "git+ssh://git@github.com/spedas/spedas_mcp.git"
        (p / ".mcp.json").write_text(json.dumps(mcp_json, indent=2))
        expect_fail(p, "ssh userinfo is not a pin", "PINNED")

        # 19) Issue #3: compatible-release syntax is an upper-bounded MCP requirement.
        p = copy_plugin(base / "c19")
        mcp_json = json.loads((p / ".mcp.json").read_text())
        args = mcp_json["mcpServers"]["spedas"]["args"]
        args[args.index("--with") + 1] = "mcp~=1.26.0"
        (p / ".mcp.json").write_text(json.dumps(mcp_json, indent=2))
        expect_pass(p, "mcp compatible-release requirement passes")

        # --- Batch U (#6): the empty-hooks intentional-deferred posture contract. ---

        # 20) The healthy tree carries the sidecar posture contract; an empty
        #     hooks/hooks.json WITH the contract passes (the intended steady state).
        p = copy_plugin(base / "c20")
        assert (p / "hooks" / "default_posture.json").exists(), "fixture missing posture sidecar"
        assert json.loads((p / "hooks" / "hooks.json").read_text())["hooks"] == []
        expect_pass(p, "empty hooks with deferred-posture contract passes")

        # 21) Empty hooks/hooks.json WITHOUT the posture contract must fail — an
        #     unexplained empty array is ambiguous (deferred vs. regression).
        p = copy_plugin(base / "c21")
        (p / "hooks" / "default_posture.json").unlink()
        expect_fail(p, "empty hooks without posture contract", "default_posture.json")

        # 22) A posture contract that no longer declares the deferred intent must
        #     fail (a gutted/half-edited contract is as bad as a missing one).
        p = copy_plugin(base / "c22")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd["spedas_default_hook_posture"] = "enabled"
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "posture contract not declaring deferred", "deferred")

        # 23) A posture contract that drops the issue #6 reference must fail — the
        #     deferred posture must stay traceable to the issue.
        p = copy_plugin(base / "c23")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd.pop("issue", None)
        sd = json.loads(json.dumps(sd).replace("#6", "#0").replace("/issues/6", "/issues/0"))
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "posture contract missing issue #6 reference", "issue #6")

        # 24) The opt-in example the contract advertises must really exist; deleting
        #     it (so the "enable it yourself" path is dead) must fail.
        p = copy_plugin(base / "c24")
        (p / "hooks" / "examples" / "pretooluse-fetch-guard.md").unlink()
        expect_fail(p, "posture contract opt-in example removed", "opt_in_example")

        # 25) A doc the contract claims explains the posture must exist; removing it
        #     must fail (docs/safety.md is referenced by the contract).
        p = copy_plugin(base / "c25")
        (p / "docs" / "safety.md").unlink()
        expect_fail(p, "posture contract doc removed", "safety.md")

        # 26) A contract without expected_hooks_json must fail: without the expected
        #     shape, the validator cannot prove the sidecar matches the shipped hooks.
        p = copy_plugin(base / "c26")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd.pop("expected_hooks_json", None)
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "posture contract missing expected_hooks_json", "expected_hooks_json")

        # 27) A stale contract whose expected_hooks_json no longer matches the
        #     shipped hooks/hooks.json must fail (drift between contract and reality).
        p = copy_plugin(base / "c27")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd["expected_hooks_json"] = {"hooks": "not-empty-and-not-matching"}
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "stale posture contract expected_hooks_json", "default_posture.json")


    print("\nAll validator tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
