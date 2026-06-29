#!/usr/bin/env python3
"""Validate the SPEDAS Agent Kit module index and first runtime modules."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = {"claude-code", "codex"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report all failures cleanly.
        fail(errors, f"{path.relative_to(ROOT)} is not valid JSON: {exc}")
        return {}


def require_path(errors: list[str], rel: str, *, base: Path = ROOT, kind: str = "path") -> Path:
    path = base / rel
    if not path.exists():
        fail(errors, f"missing {kind}: {path.relative_to(ROOT)}")
    return path


def main() -> int:
    errors: list[str] = []
    manifest_path = require_path(errors, "agent-kit.json", kind="Agent Kit manifest")
    manifest = load_json(manifest_path, errors) if manifest_path.exists() else {}

    if manifest.get("name") != "spedas-agent-kit":
        fail(errors, "agent-kit.json name must be spedas-agent-kit")
    modules = manifest.get("modules")
    if not isinstance(modules, list):
        fail(errors, "agent-kit.json modules must be a list")
        modules = []
    by_id = {m.get("id"): m for m in modules if isinstance(m, dict)}
    missing = REQUIRED_MODULES - set(by_id)
    if missing:
        fail(errors, f"agent-kit.json missing first runtime modules: {', '.join(sorted(missing))}")

    for module_id, module in by_id.items():
        if module_id not in REQUIRED_MODULES:
            continue
        module_path_rel = module.get("path")
        if not isinstance(module_path_rel, str) or not module_path_rel:
            fail(errors, f"module {module_id} must declare path")
            continue
        module_root = require_path(errors, module_path_rel, kind=f"module {module_id} root")
        for key in ("manifest", "mcpServers", "skills"):
            value = module.get(key)
            if isinstance(value, str) and value:
                require_path(errors, value, kind=f"module {module_id} {key}")
            else:
                fail(errors, f"module {module_id} must declare {key}")
        if module_id == "claude-code":
            if module_path_rel != ".":
                fail(errors, "Claude Code module must remain at repo root in this compatibility PR")
            for key in ("commands", "hooks", "moduleReadme"):
                value = module.get(key)
                if isinstance(value, str) and value:
                    require_path(errors, value, kind=f"Claude Code {key}")
                else:
                    fail(errors, f"Claude Code module must declare {key}")
        if module_id == "codex":
            if module_path_rel != "plugins/codex":
                fail(errors, "Codex module must live at plugins/codex in this PR")
            for key in ("instructions", "marketplace"):
                value = module.get(key)
                if isinstance(value, str) and value:
                    require_path(errors, value, kind=f"Codex {key}")
                else:
                    fail(errors, f"Codex module must declare {key}")
            codex_manifest = load_json(ROOT / module["manifest"], errors) if isinstance(module.get("manifest"), str) else {}
            if codex_manifest.get("name") != "spedas-codex":
                fail(errors, "Codex plugin manifest name must stay spedas-codex for compatibility")

    plugins_readme = require_path(errors, "plugins/README.md", kind="plugins index README")
    if plugins_readme.exists():
        text = plugins_readme.read_text(encoding="utf-8")
        for phrase in ("Claude Code", "Codex", "OpenCode"):
            if phrase not in text:
                fail(errors, f"plugins/README.md should mention {phrase}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print(f"\nAgent Kit validation FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("SPEDAS Agent Kit module validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
