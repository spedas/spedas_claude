#!/usr/bin/env python3
"""Validate the SPEDAS Claude Code plugin wrapper structure without network access.

This validator checks that every resource the plugin *advertises* actually exists
and resolves correctly. It is deliberately strict about packaging mistakes so CI
fails loudly before a user ever tries to load the plugin in Claude Code.

Plugin resource-path semantics (verified against the Claude Code plugin
convention and shipped Anthropic/superpowers plugins; see the README section
"How the plugin's resources are resolved"):

- Claude Code auto-discovers root-level ``commands/``, ``skills/``,
  ``hooks/hooks.json`` and ``.mcp.json`` by convention. The canonical
  ``.claude-plugin/plugin.json`` can be metadata-only.
- When ``.claude-plugin/plugin.json`` *does* declare path keys
  (``skills``/``commands``/``hooks``/``mcpServers``), those paths are resolved
  **relative to the plugin root** (the directory that contains
  ``.claude-plugin/``), NOT relative to the ``.claude-plugin/`` directory.

So every declared path here is joined against ``ROOT`` (the plugin root). If a
declared resource does not resolve to an existing, non-empty file/dir under the
root, that is a hard error. This makes both flavors of mistake visible: a wrong
relative base, and a missing/renamed resource.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Plugin root = directory that contains .claude-plugin/ (this file lives in scripts/).
ROOT = Path(__file__).resolve().parents[1]

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def _strip_dotslash(value: str) -> str:
    """Remove a single leading './' (the plugin.json convention) without eating
    the leading dot of dotfiles like './.mcp.json'."""
    value = value.strip()
    while value.startswith("./"):
        value = value[2:]
    return value or "."


def require(rel: str, *, kind: str = "file") -> Path | None:
    """Require a path to exist under the plugin root.

    kind: "file" (must exist and be non-empty) or "dir".
    Records an error instead of raising so we can report all problems at once.
    """
    p = ROOT / rel
    if not p.exists():
        fail(f"missing required {kind}: {rel}")
        return None
    if kind == "dir":
        if not p.is_dir():
            fail(f"expected directory but found file: {rel}")
            return None
    else:
        if not p.is_file():
            fail(f"expected file but found directory: {rel}")
            return None
        if p.stat().st_size == 0:
            fail(f"empty required file: {rel}")
            return None
    return p


def load_json(rel: str):
    p = require(rel)
    if p is None:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {rel}: {exc}")
        return None


def resolve_declared(rel_value, *, kind: str, source_key: str) -> Path | None:
    """Resolve a path declared in plugin.json relative to the plugin root.

    Rejects absolute paths and parent-escaping paths loudly; these are the
    ambiguous declarations issue #4 warned about.
    """
    if not isinstance(rel_value, str) or not rel_value.strip():
        fail(f"plugin.json key {source_key!r} must be a non-empty path string")
        return None
    if rel_value.startswith("/"):
        fail(f"plugin.json key {source_key!r} must be plugin-root-relative, got absolute path {rel_value!r}")
        return None
    candidate = _strip_dotslash(rel_value)
    if ".." in Path(candidate).parts:
        fail(f"plugin.json key {source_key!r} escapes the plugin root: {rel_value!r}")
        return None
    resolved = require(candidate, kind=kind)
    if resolved is None:
        fail(
            f"plugin.json declares {source_key!r} -> {rel_value!r} but it does not resolve "
            f"to an existing {kind} relative to the plugin root ({candidate})"
        )
    return resolved


def validate_skill_dir(skills_dir: Path) -> None:
    """Every advertised skill must have a non-empty SKILL.md with name+description frontmatter."""
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        fail(f"no SKILL.md found under {skills_dir.relative_to(ROOT).as_posix()}/*/")
        return
    for sf in skill_files:
        rel = sf.relative_to(ROOT).as_posix()
        text = sf.read_text(encoding="utf-8")
        if not text.strip():
            fail(f"empty skill file: {rel}")
            continue
        if not text.lstrip().startswith("---"):
            fail(f"skill missing YAML frontmatter (--- header): {rel}")
            continue
        parts = text.split("---", 2)
        front = parts[1] if len(parts) >= 3 else ""
        if "name:" not in front:
            fail(f"skill frontmatter missing 'name:' field: {rel}")
        if "description:" not in front:
            fail(f"skill frontmatter missing 'description:' field: {rel}")
        # reference/*.md files the skill lists in its bullet index must exist.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- `reference/") and stripped.count("`") >= 2:
                ref = stripped.split("`")[1]
                if not (sf.parent / ref).exists():
                    fail(f"{rel} references missing file: {ref}")


def validate_commands(commands_dir: Path) -> None:
    cmd_files = sorted(commands_dir.glob("*.md"))
    if not cmd_files:
        fail(f"no command .md files found under {commands_dir.relative_to(ROOT).as_posix()}/")
    # geometry.md is explicitly required (issues #7/#8/#15): the plugin advertises
    # a geometry workflow, so the file must exist and document SPICE/geometry use.
    geometry = commands_dir / "geometry.md"
    if not geometry.exists():
        fail("missing required command file: commands/geometry.md")
    elif geometry.stat().st_size == 0:
        fail("empty required file: commands/geometry.md")
    else:
        gtext = geometry.read_text(encoding="utf-8").lower()
        if "spice" not in gtext and "geometry" not in gtext:
            fail("commands/geometry.md should describe SPICE/geometry usage")
    for cf in cmd_files:
        rel = cf.relative_to(ROOT).as_posix()
        if cf.stat().st_size == 0:
            fail(f"empty command file: {rel}")
            continue
        # Issue #11: every command must carry YAML frontmatter (so it surfaces a
        # description in Claude Code) and reference $ARGUMENTS (so user-supplied
        # parameters are actually injected into the prompt). A plain-Markdown
        # command silently drops invocation arguments, defeating the slash command.
        text = cf.read_text(encoding="utf-8")
        if not text.lstrip().startswith("---"):
            fail(f"command missing YAML frontmatter (--- header): {rel}")
        else:
            parts = text.split("---", 2)
            front = parts[1] if len(parts) >= 3 else ""
            if "description:" not in front:
                fail(f"command frontmatter missing 'description:' field: {rel}")
        if "$ARGUMENTS" not in text:
            fail(f"command does not reference $ARGUMENTS for argument substitution: {rel}")


def validate_hooks(hooks_value) -> None:
    """Validate the hooks file the plugin advertises (declared key or convention)."""
    if isinstance(hooks_value, str) and hooks_value.strip():
        hooks_path = resolve_declared(hooks_value, kind="file", source_key="hooks")
    else:
        # Convention: hooks/hooks.json at the root. Optional if not advertised.
        p = ROOT / "hooks/hooks.json"
        hooks_path = require("hooks/hooks.json") if p.exists() else None
    if hooks_path is None:
        return
    rel = hooks_path.relative_to(ROOT).as_posix()
    try:
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {rel}: {exc}")
        return
    if "hooks" not in data:
        fail(f"{rel} must contain a top-level 'hooks' key")
        return
    hooks = data["hooks"]
    # Claude Code accepts an object keyed by event name; an empty list/object is a
    # valid placeholder. Anything else is a malformed hooks file.
    if not isinstance(hooks, (dict, list)):
        fail(f"{rel} 'hooks' must be an object (event->matchers) or an empty placeholder")


_MCP_REQ_RE = re.compile(r"^mcp(?=[<>=!~])")


def _split_git_url_ref(from_value: str) -> tuple[str, str | None]:
    """Split a pip/uv git URL into (url_without_ref, ref).

    A real pin is the final ``@<ref>`` after the repository path. Userinfo/SSH
    forms such as ``git+ssh://git@github.com/spedas/spedas_mcp.git`` also contain
    ``@`` before the final slash; those must NOT be treated as pinned refs.
    """
    if not from_value.startswith("git+"):
        return from_value, None
    base, sep, fragment = from_value.partition("#")
    at = base.rfind("@")
    last_slash = base.rfind("/")
    if at > last_slash:
        ref = base[at + 1 :] or None
        url = base[:at]
        if sep:
            url = f"{url}#{fragment}"
        return url, ref
    return from_value, None


def _is_mcp_requirement(compact: str) -> bool:
    return compact == "mcp" or bool(_MCP_REQ_RE.match(compact))


def _mcp_has_upper_bound(compact: str) -> bool:
    return "==" in compact or "<" in compact or "~=" in compact


def _validate_mcp_pin(rel: str, args: list[str]) -> None:
    """Issue #3: enforce that the spedas_mcp source is pinned and the MCP protocol
    requirement is upper-bounded.

    - The ``--from git+...spedas_mcp.git`` URL must carry a real final ``@<ref>``
      pin (commit or tag) after the repository path. A bare URL resolves the
      default branch HEAD on every run; an SSH userinfo ``git@host`` alone is not a
      ref pin.
    - The ``mcp`` requirement passed via ``--with`` must have an upper bound
      (a ``<`` constraint, an exact ``==``, or compatible-release ``~=``);
      open-ended ``mcp>=1.26.0`` allows a future breaking ``2.x`` to reach every
      user silently.
    """
    def _value_after(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return None

    from_value = _value_after("--from") or ""
    if "spedas_mcp" in from_value:
        # Require a ref pin appended after the repo path; do not accept user@host.
        _, ref = _split_git_url_ref(from_value)
        if not ref:
            fail(
                f"{rel}: spedas_mcp source must be PINNED to a commit or tag "
                f"(git+https://github.com/spedas/spedas_mcp.git@<sha-or-tag>); "
                f"a floating default-branch HEAD is not reproducible (issue #3)"
            )

    # Find the mcp requirement among --with values (e.g. "mcp>=1.26.0,<2").
    mcp_req = None
    for a in args:
        compact = a.replace(" ", "")
        if _is_mcp_requirement(compact):
            mcp_req = compact
            break
    if mcp_req is not None and not _mcp_has_upper_bound(mcp_req):
        fail(
            f"{rel}: the MCP protocol requirement must have an upper bound "
            f"(e.g. 'mcp>=1.26.0,<2' or 'mcp~=1.26.0'); an open-ended '{mcp_req}' "
            f"allows a breaking major version to be pulled silently (issue #3)"
        )


def validate_mcp(mcp_value) -> None:
    if isinstance(mcp_value, str) and mcp_value.strip():
        if resolve_declared(mcp_value, kind="file", source_key="mcpServers") is None:
            return
        rel = _strip_dotslash(mcp_value)
    else:
        if require(".mcp.json") is None:
            return
        rel = ".mcp.json"
    data = load_json(rel)
    if data is None:
        return
    servers = data.get("mcpServers") or data.get("mcp_servers")
    if not isinstance(servers, dict) or "spedas" not in servers:
        fail(f"{rel} must define a 'spedas' MCP server")
        return
    server = servers["spedas"]
    if not isinstance(server, dict):
        fail(f"{rel} 'spedas' server config must be an object")
        return
    if server.get("command") != "uvx":
        fail(f"{rel}: expected MCP command 'uvx' for a portable, no-clone install")
    args = [a for a in (server.get("args") or []) if isinstance(a, str)]
    joined = " ".join(args)
    # Issue #3: the resolved spedas_mcp source must be the official repo and the
    # console entrypoint must be invoked. A wrong repo/entrypoint must fail CI.
    if "github.com/spedas/spedas_mcp" not in joined:
        fail(f"{rel}: spedas server must install from git+https://github.com/spedas/spedas_mcp.git")
    if "spedas-mcp" not in joined:
        fail(f"{rel}: spedas server must run the 'spedas-mcp' console script")
    if not any(_is_mcp_requirement(a.replace(" ", "")) for a in args):
        fail(f"{rel}: expected an explicit 'mcp>=...' / 'mcp~=...' / 'mcp==...' requirement for the MCP protocol dependency")

    # Issue #3 reproducibility/auditability: the default spedas_mcp source must be
    # PINNED (a git @<ref> on the --from URL), and the MCP protocol requirement
    # must be UPPER-BOUNDED so a future breaking major (mcp 2.x) cannot be pulled
    # silently. A regression to a floating HEAD or an open-ended floor fails CI.
    _validate_mcp_pin(rel, args)

    env = server.get("env")
    if env is not None and not isinstance(env, dict):
        fail(f"{rel}: 'spedas' server env must be an object when present")


def validate_batch_c_docs() -> None:
    """Batch C (issues #5/#6/#9/#13/#14/#17): the cross-referenced docs, the
    troubleshooting runbook, the provenance templates, and the opt-in hook example
    must all exist. README/SKILL/safety link to these; a missing target is a broken
    contract, so fail loudly the same way the skill reference-link check does.
    """
    # Repo docs cross-linked from README/SKILL/commands.
    require("docs/configuration.md")          # #5 / #17 env + cache config
    require("docs/safety.md")                 # #6 fetch/kernel boundary
    require("skills/spedas-workflow/reference/troubleshooting.md")  # #13 runbook

    # #6: opt-in hook example referenced by docs/safety.md and hooks/README.md.
    # These must be present so the "enable it yourself" path is real, and the
    # shipped hooks.json must remain the intentional empty placeholder (not an
    # accidentally-active hook).
    require("hooks/examples/pretooluse-fetch-guard.md")
    require("hooks/examples/fetch_guard.py")

    # #14: provenance template bundle (the five files + helper + README).
    provenance = ROOT / "templates" / "provenance"
    if not provenance.is_dir():
        fail("missing required dir: templates/provenance (issue #14 provenance scaffolding)")
        return
    for name in (
        "README.md",
        "request.json",
        "tool_calls.jsonl",
        "capture_environment.sh",
        "artifacts_manifest.json",
        "provenance.md",
    ):
        require(f"templates/provenance/{name}")
    # The two JSON templates must be well-formed JSON so a copy-paste run starts valid.
    for jname in ("request.json", "artifacts_manifest.json"):
        load_json(f"templates/provenance/{jname}")


def validate_reproducibility_and_example() -> None:
    """#32: the pinning/reproducibility doc and the documented first-run example are
    ship-critical and heavily cross-linked, so their absence must fail CI — not ship
    silently. ``docs/dependencies.md`` is linked from README/SKILL/troubleshooting/
    artifact-provenance; ``examples/run_overview.py`` is the README/CHANGELOG-advertised
    onboarding path.
    """
    require("docs/dependencies.md")        # pinning/reproducibility, cross-linked widely
    # #3: the root compatibility/reproducibility anchor (pinned triple, verification
    # command, bump procedure, supply-chain trust model). README/CHANGELOG/docs link
    # to it; a missing target is a broken contract, so fail loudly.
    require("COMPATIBILITY.md")
    example = require("examples/run_overview.py")  # documented first-run example (README/CHANGELOG)
    # The advertised example must byte-compile, or the onboarding path is broken.
    if example is not None:
        import py_compile

        try:
            py_compile.compile(str(example), doraise=True)
        except py_compile.PyCompileError as exc:
            fail(f"examples/run_overview.py does not byte-compile: {exc.msg}")


def validate_hooks_placeholder_intentional() -> None:
    """#6: assert hooks/hooks.json is a *deliberate* empty placeholder OR a valid
    hooks object — never a malformed/half-edited file. The structural check lives in
    validate_hooks(); this records that an empty array is an accepted, documented
    state (hooks/README.md explains why) rather than a regression.
    """
    p = ROOT / "hooks" / "hooks.json"
    if not p.exists():
        return  # absence handled by validate_hooks() / convention.
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return  # validate_hooks() already reports malformed JSON.
    hooks = data.get("hooks")
    # Empty list/dict = intentional placeholder (documented in hooks/README.md).
    # Non-empty = an enabled hook config, which validate_hooks() structurally checks.
    if hooks in ([], {}) and not (ROOT / "hooks" / "README.md").exists():
        fail("hooks/hooks.json is an empty placeholder but hooks/README.md is missing; "
             "document the intent (issue #6) so the empty array is not read as a regression")


def validate_metadata(data: dict) -> None:
    if data.get("name") != "spedas-claude":
        fail("plugin.json: Claude plugin 'name' must be 'spedas-claude'")
    if not data.get("version"):
        fail("plugin.json: missing 'version'")
    if not data.get("description"):
        fail("plugin.json: missing 'description'")


def main() -> int:
    require("README.md")
    require("LICENSE")

    manifest_rel = ".claude-plugin/plugin.json"
    data = load_json(manifest_rel)
    if data is None:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"\nplugin validation FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1

    validate_metadata(data)

    # Resolve declared resources relative to the plugin root. If a key is absent,
    # fall back to the Claude Code auto-discovery convention directory/file.
    if "skills" in data:
        skills_dir = resolve_declared(data["skills"], kind="dir", source_key="skills")
    else:
        skills_dir = require("skills", kind="dir")
    if skills_dir is not None:
        validate_skill_dir(skills_dir)

    if "commands" in data:
        commands_dir = resolve_declared(data["commands"], kind="dir", source_key="commands")
    else:
        commands_dir = require("commands", kind="dir")
    if commands_dir is not None:
        validate_commands(commands_dir)

    validate_hooks(data.get("hooks"))
    validate_mcp(data.get("mcpServers"))

    # Onboarding (#12) depends on the workflow skill existing.
    require("skills/spedas-workflow/SKILL.md")

    # Batch C (#5/#6/#9/#13/#14/#17): cross-referenced docs, runbook, templates,
    # and the opt-in hook example must resolve; hooks placeholder must be intentional.
    validate_batch_c_docs()
    # Batch F (#32): pinning/reproducibility doc + documented first-run example.
    validate_reproducibility_and_example()
    validate_hooks_placeholder_intentional()

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        print(f"\nplugin validation FAILED with {len(errors)} error(s)", file=sys.stderr)
        return 1

    print("SPEDAS Claude plugin wrapper validation OK")
    print(f"  manifest: {manifest_rel}")
    if skills_dir is not None:
        print(f"  skills:   {skills_dir.relative_to(ROOT).as_posix()}")
    if commands_dir is not None:
        print(f"  commands: {commands_dir.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
