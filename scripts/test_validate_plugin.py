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
        data["mcpServers"]["spedas"]["args"] = ["--from", "git+https://github.com/evil/x.git", "spedas-agent-kit"]
        mcp.write_text(json.dumps(data))
        expect_fail(p, "wrong MCP source", "github.com/spedas/spedas_agent_kit")

        # 2b) Issue #3: an UNPINNED spedas_agent_kit git URL (no @ref) must fail — a
        #     floating default-branch HEAD is not reproducible.
        p = copy_plugin(base / "c2b")
        mcp = p / ".mcp.json"
        data = json.loads(mcp.read_text())
        data["mcpServers"]["spedas"]["args"] = [
            "--with", "mcp>=1.26.0,<2",
            "--from", "git+https://github.com/spedas/spedas_agent_kit.git",
            "spedas-agent-kit",
        ]
        mcp.write_text(json.dumps(data))
        expect_fail(p, "unpinned spedas_agent_kit source", "PINNED")

        # 2c) Issue #3: an MCP requirement with no upper bound must fail — a future
        #     breaking 2.x could be pulled silently.
        p = copy_plugin(base / "c2c")
        mcp = p / ".mcp.json"
        data = json.loads(mcp.read_text())
        data["mcpServers"]["spedas"]["args"] = [
            "--with", "mcp>=1.26.0",
            "--from", "git+https://github.com/spedas/spedas_agent_kit.git@8fcfc7dd0e6f01800f301590ed8213eb33683582",
            "spedas-agent-kit",
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

        # 5) Malformed hooks still fail the structural hook validator.
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

        # 8) The shared skill router must exist; the wrapper should carry the
        #    full exported Agent Kit shared skill set, not just one workflow skill.
        p = copy_plugin(base / "c8")
        (p / "skills" / "spedas-skills-index" / "SKILL.md").unlink()
        expect_fail(p, "missing shared skill router", "spedas-skills-index")

        # 9) Batch C: a provenance template (#14) must exist.
        p = copy_plugin(base / "c9")
        (p / "templates" / "provenance" / "request.json").unlink()
        expect_fail(p, "missing provenance template", "templates/provenance/request.json")

        # 10) Batch C: the compatibility hook example (#6) must exist so older
        #     copied configs/documentation do not point to a dead path.
        p = copy_plugin(base / "c10")
        (p / "hooks" / "examples" / "fetch_guard.py").unlink()
        expect_fail(p, "missing compatibility hook example", "hooks/examples/fetch_guard.py")

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
        args[args.index("--from") + 1] = "git+ssh://git@github.com/spedas/spedas_agent_kit.git"
        (p / ".mcp.json").write_text(json.dumps(mcp_json, indent=2))
        expect_fail(p, "ssh userinfo is not a pin", "PINNED")

        # 19) Issue #3: compatible-release syntax is an upper-bounded MCP requirement.
        p = copy_plugin(base / "c19")
        mcp_json = json.loads((p / ".mcp.json").read_text())
        args = mcp_json["mcpServers"]["spedas"]["args"]
        args[args.index("--with") + 1] = "mcp~=1.26.0"
        (p / ".mcp.json").write_text(json.dumps(mcp_json, indent=2))
        expect_pass(p, "mcp compatible-release requirement passes")

        # --- Batch U (#6): enabled default PreToolUse fetch/kernel guard. ---

        # 20) The healthy tree ships an active default guard, not the old empty
        #     placeholder posture.
        p = copy_plugin(base / "c20")
        assert json.loads((p / "hooks" / "hooks.json").read_text())["hooks"] != []
        expect_pass(p, "enabled default fetch/kernel guard passes")

        # 21) Regressing hooks/hooks.json to the old empty placeholder must fail.
        p = copy_plugin(base / "c21")
        (p / "hooks" / "hooks.json").write_text(json.dumps({"hooks": []}, indent=2))
        expect_fail(p, "empty hooks now fails", "enabled default PreToolUse")

        # 22) The sidecar must declare the enabled posture, not the old deferred one.
        p = copy_plugin(base / "c22")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd["spedas_default_hook_posture"] = "deferred"
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "posture contract not declaring enabled", "enabled")

        # 23) The sidecar must keep the issue #6 traceability.
        p = copy_plugin(base / "c23")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd.pop("issue", None)
        sd = json.loads(json.dumps(sd).replace("#6", "#0").replace("/issues/6", "/issues/0"))
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "posture contract missing issue #6 reference", "issue #6")

        # 24) The active guard script the hook invokes must exist.
        p = copy_plugin(base / "c24")
        (p / "hooks" / "fetch_guard.py").unlink()
        expect_fail(p, "default guard script removed", "hooks/fetch_guard.py")

        # 25) A doc the enabled-posture contract names must exist.
        p = copy_plugin(base / "c25")
        (p / "docs" / "safety.md").unlink()
        expect_fail(p, "enabled posture doc removed", "safety.md")

        # 26) Dropping one risky tool from the matcher must fail so new edits cannot
        #     silently unguard a download/kernel surface.
        p = copy_plugin(base / "c26")
        hooks_path = p / "hooks" / "hooks.json"
        hd = json.loads(hooks_path.read_text())
        hd["hooks"]["PreToolUse"][0]["matcher"] = hd["hooks"]["PreToolUse"][0]["matcher"].replace(
            "|mcp__spedas__fetch_fdsn_data", ""
        )
        hooks_path.write_text(json.dumps(hd, indent=2))
        expect_fail(p, "matcher missing fetch_fdsn_data", "mcp__spedas__fetch_fdsn_data")

        # 27) Keeping the matcher but no longer invoking the default guard script
        #     must fail.
        p = copy_plugin(base / "c27")
        hooks_path = p / "hooks" / "hooks.json"
        hd = json.loads(hooks_path.read_text())
        hd["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "echo no guard"
        hooks_path.write_text(json.dumps(hd, indent=2))
        expect_fail(p, "PreToolUse no longer invokes default guard", "hooks/fetch_guard.py")

        # 28) The command must quote the CLAUDE_PLUGIN_ROOT path so plugin dirs with
        #     spaces do not split the guard invocation at runtime.
        p = copy_plugin(base / "c28")
        hooks_path = p / "hooks" / "hooks.json"
        hd = json.loads(hooks_path.read_text())
        hd["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "python ${CLAUDE_PLUGIN_ROOT}/hooks/fetch_guard.py"
        hooks_path.write_text(json.dumps(hd, indent=2))
        expect_fail(p, "PreToolUse guard path not quoted", "must quote")

        # 29) The sidecar cannot silently shrink the canonical required guard set.
        p = copy_plugin(base / "c29")
        sidecar = p / "hooks" / "default_posture.json"
        sd = json.loads(sidecar.read_text())
        sd["matched_tools"] = [t for t in sd["matched_tools"] if t != "mcp__spedas__fetch_fdsn_data"]
        sidecar.write_text(json.dumps(sd, indent=2))
        expect_fail(p, "sidecar matched_tools missing canonical guard", "matched_tools")


    print("\nAll validator tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
