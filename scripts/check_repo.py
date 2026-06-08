#!/usr/bin/env python3
"""Run the canonical local repository verification checklist."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOTS = ("src", "tests", "scripts")


@dataclass(frozen=True)
class Step:
    display: str
    command: tuple[str, ...]
    pythonpath_src: bool = False


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    steps = _verification_steps(ROOT)
    if args.list_steps:
        for step in steps:
            print(step.display)
        print("remove generated __pycache__ directories")
        return 0

    exit_code = 0
    for step in steps:
        print(f"==> {step.display}", flush=True)
        result = _run_step(step)
        if result != 0:
            exit_code = result
            break

    cleanup_result = _remove_pycache(ROOT)
    if cleanup_result != 0 and exit_code == 0:
        exit_code = cleanup_result
    if exit_code == 0:
        print("check_repo OK")
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local tests, consistency guards, and static checks.",
    )
    parser.add_argument(
        "--list",
        dest="list_steps",
        action="store_true",
        help="Print the verification checklist without running it.",
    )
    return parser


def _verification_steps(repo_root: Path) -> list[Step]:
    return [
        Step(
            "PYTHONPATH=src python3 -m unittest discover -s tests",
            (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
            pythonpath_src=True,
        ),
        _python_script_step("scripts/check_surface_consistency.py"),
        _python_script_step("scripts/check_source_type_consistency.py"),
        _python_script_step("scripts/check_provider_surface_consistency.py"),
        _python_script_step("scripts/check_contract_anchor_consistency.py"),
        Step(
            (
                "jq empty schemas/*.json profiles/examples/*.json "
                "sources/examples/*.json sources/sets/*.json"
            ),
            ("jq", "empty", *_json_files(repo_root)),
        ),
        Step("git diff --check", ("git", "diff", "--check")),
        Step(
            "PYTHONPATH=src python3 -m compileall -q src tests scripts",
            (
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "src",
                "tests",
                "scripts",
            ),
            pythonpath_src=True,
        ),
        Step(
            "PYTHONPATH=src python3 -m shared_intake_governance.cli --help",
            (
                sys.executable,
                "-m",
                "shared_intake_governance.cli",
                "--help",
            ),
            pythonpath_src=True,
        ),
    ]


def _python_script_step(path: str) -> Step:
    return Step(f"python3 {path}", (sys.executable, path))


def _json_files(repo_root: Path) -> tuple[str, ...]:
    files = []
    for pattern in (
        "schemas/*.json",
        "profiles/examples/*.json",
        "sources/examples/*.json",
        "sources/sets/*.json",
    ):
        files.extend(
            sorted(
                str(path.relative_to(repo_root))
                for path in repo_root.glob(pattern)
            )
        )
    return tuple(files)


def _run_step(step: Step) -> int:
    env = os.environ.copy()
    if step.pythonpath_src:
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = "src" if not existing else f"src{os.pathsep}{existing}"
    try:
        completed = subprocess.run(
            step.command,
            cwd=ROOT,
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        print(f"missing command: {step.command[0]} ({exc})", file=sys.stderr)
        return 127
    return completed.returncode


def _remove_pycache(repo_root: Path) -> int:
    print("==> remove generated __pycache__ directories", flush=True)
    try:
        for root in CACHE_ROOTS:
            for cache_path in (repo_root / root).rglob("__pycache__"):
                shutil.rmtree(cache_path)
    except OSError as exc:
        print(f"failed to remove __pycache__: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
