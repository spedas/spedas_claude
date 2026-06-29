#!/usr/bin/env python3
"""Self-tests for the default SPEDAS PreToolUse fetch/kernel guard.

Plain Python, no pytest, so it can run in the same lightweight CI matrix as the
packaging validator. The tests exercise the hook as Claude Code runs it: JSON on
stdin, JSON permission output on stdout, no network and no file writes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "hooks" / "fetch_guard.py"


def run_guard(event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
    )


def output_payload(proc: subprocess.CompletedProcess) -> dict:
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "expected hook JSON on stdout"
    return json.loads(proc.stdout)


def assert_asks(proc: subprocess.CompletedProcess, *needles: str) -> None:
    payload = output_payload(proc)
    specific = payload.get("hookSpecificOutput", {})
    assert specific.get("hookEventName") == "PreToolUse", payload
    assert specific.get("permissionDecision") == "ask", payload
    reason = specific.get("permissionDecisionReason", "")
    for needle in needles:
        assert needle in reason, f"missing {needle!r} in reason: {reason!r}"


def assert_quiet(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "", proc.stdout
    assert proc.stderr == "", proc.stderr


def main() -> int:
    # Metadata/planning tools remain frictionless.
    assert_quiet(run_guard({"tool_name": "mcp__spedas__find_datasets", "tool_input": {"query": "mms"}}))

    # Real archive fetches ask for permission and include dataset/cache/provenance hints.
    assert_asks(
        run_guard(
            {
                "tool_name": "mcp__spedas__fetch_data_product",
                "tool_input": {
                    "dataset_id": "MMS1_FGM_BRST_L2",
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-01T01:00:00Z",
                },
            }
        ),
        "real archive/network download",
        "MMS1_FGM_BRST_L2",
        "cache/output",
        "provenance",
    )

    # Wide ranges get an extra narrowing/planning warning.
    assert_asks(
        run_guard(
            {
                "tool_name": "mcp__spedas__fetch_hapi_data",
                "tool_input": {
                    "dataset_id": "OMNI_HRO_1MIN",
                    "trange": ["2023-01-01", "2023-02-15"],
                },
            }
        ),
        "Wide time range detected",
        "Prefer the unified fetch_data_product",
    )

    # Geometry calls that do not opt into kernel downloads stay quiet.
    assert_quiet(
        run_guard(
            {
                "tool_name": "mcp__spedas__get_ephemeris",
                "tool_input": {"target": "MMS1", "allow_kernel_download": False},
            }
        )
    )

    # Kernel-download-capable geometry calls ask for permission.
    assert_asks(
        run_guard(
            {
                "tool_name": "mcp__spedas__get_ephemeris",
                "tool_input": {
                    "target": "MMS1",
                    "allow_kernel_download": "true",
                    "start_time": "2020-01-01",
                    "end_time": "2020-01-10",
                },
            }
        ),
        "SPICE kernels can be 100 MB-1+ GB",
        "MMS1",
        "Wide time range detected",
    )

    # Legacy SPICE management names remain guarded, except read-only status/list actions.
    assert_asks(
        run_guard(
            {
                "tool_name": "mcp__spedas__manage_spice_kernels",
                "tool_input": {"action": "download", "target": "psp"},
            }
        ),
        "mutate SPICE kernel cache state",
        "psp",
    )
    assert_quiet(
        run_guard(
            {
                "tool_name": "mcp__spedas__manage_spice_kernels",
                "tool_input": {"action": "status", "target": "psp"},
            }
        )
    )

    print("\nAll fetch guard tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
