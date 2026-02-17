#!/usr/bin/env python3
"""
Eval runner for the proto-event-contracts agent.

Reads cases.json, runs the agent against each fixture via opencode,
and grades the output using deterministic keyword matching.

Usage:
    python agents/proto-event-contracts/evals/run_evals.py
    python agents/proto-event-contracts/evals/run_evals.py --verbose
    python agents/proto-event-contracts/evals/run_evals.py --model sonnet

Prerequisites:
    - opencode CLI installed and on PATH
    - .opencode/agents/proto-event-contracts.md in the current project
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def load_cases(cases_path: Path) -> list[dict]:
    """Load test cases from cases.json."""
    with open(cases_path) as f:
        return json.load(f)


def run_agent(fixture_path: str, model: str | None = None) -> tuple[int, str]:
    """
    Run the proto-event-contracts agent against a fixture file.

    Returns (return_code, stdout_text).
    """
    cmd = [
        "opencode", "run",
        "--agent", "proto-event-contracts",
        "-f", fixture_path,
        "Review this proto file against the event contract standard. "
        "List any must-fix or should-fix findings. "
        "If the file is clean, say so explicitly.",
    ]
    if model:
        cmd.extend(["--model", model])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout + result.stderr


def grade_clean(output: str) -> tuple[bool, str]:
    """
    Grade a case that should produce no findings.

    Fails if the output contains 'must-fix' or 'must fix' (case-insensitive).
    """
    lower = output.lower()
    must_fix_pattern = re.compile(r"must[- ]fix", re.IGNORECASE)
    if must_fix_pattern.search(output):
        return False, "Expected clean output but found 'must-fix' / 'must fix'"
    return True, "Clean — no must-fix findings detected"


def grade_finding(output: str, severity: str, keywords: list[str]) -> tuple[bool, str]:
    """
    Grade a case that should produce findings.

    Checks:
    1. Each keyword appears in the output (case-insensitive).
    2. The expected severity level is mentioned.
    """
    lower = output.lower()
    missing_keywords = []
    for kw in keywords:
        if kw.lower() not in lower:
            missing_keywords.append(kw)

    severity_pattern = re.compile(re.escape(severity), re.IGNORECASE)
    severity_found = bool(severity_pattern.search(output))

    errors = []
    if missing_keywords:
        errors.append(f"Missing keywords: {missing_keywords}")
    if not severity_found:
        errors.append(f"Severity '{severity}' not found in output")

    if errors:
        return False, "; ".join(errors)
    return True, f"Found all keywords {keywords} with severity '{severity}'"


def main():
    parser = argparse.ArgumentParser(
        description="Run evals for the proto-event-contracts agent."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full agent output for each case.",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Override the model used by the agent.",
    )
    args = parser.parse_args()

    # Resolve paths relative to this script's location
    script_dir = Path(__file__).resolve().parent
    agent_dir = script_dir.parent
    cases_path = script_dir / "cases.json"

    if not cases_path.exists():
        print(f"ERROR: {cases_path} not found", file=sys.stderr)
        sys.exit(1)

    cases = load_cases(cases_path)
    print(f"Loaded {len(cases)} eval cases from {cases_path}\n")

    results = []

    for i, case in enumerate(cases, 1):
        fixture = case["fixture"]
        fixture_path = str(agent_dir / fixture)
        expect_clean = case["expect_clean"]
        severity = case.get("severity")
        keywords = case.get("keywords", [])

        fixture_name = Path(fixture).name
        print(f"[{i}/{len(cases)}] {fixture_name} ... ", end="", flush=True)

        if not Path(fixture_path).exists():
            print("SKIP (fixture not found)")
            results.append({"case": fixture, "status": "skip", "detail": "fixture not found"})
            continue

        try:
            returncode, output = run_agent(fixture_path, model=args.model)
        except subprocess.TimeoutExpired:
            print("FAIL (timeout)")
            results.append({"case": fixture, "status": "fail", "detail": "agent timed out"})
            continue
        except FileNotFoundError:
            print("FAIL (opencode not found)")
            print(
                "\nERROR: 'opencode' command not found. "
                "Install opencode and ensure it is on your PATH.",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.verbose:
            print()
            print("-" * 60)
            print(output)
            print("-" * 60)

        # Grade
        if expect_clean:
            passed, detail = grade_clean(output)
        else:
            passed, detail = grade_finding(output, severity, keywords)

        status = "pass" if passed else "fail"
        print(f"{'PASS' if passed else 'FAIL'} — {detail}")

        results.append({"case": fixture, "status": status, "detail": detail})

        if not passed and args.verbose:
            print(f"  Agent output length: {len(output)} chars")

    # Summary
    print()
    print("=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")

    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f", {failed} failed", end="")
    if skipped:
        print(f", {skipped} skipped", end="")
    print()

    if failed:
        print("\nFailed cases:")
        for r in results:
            if r["status"] == "fail":
                print(f"  - {r['case']}: {r['detail']}")

    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
