#!/usr/bin/env python3
"""Check that documented CLI surface matches the actual argparse surface."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_COMMAND_PATTERN = re.compile(
    r"^- `python -m shared_intake_governance\.cli ([A-Za-z0-9-]+)`$"
)


def main() -> int:
    errors = check_surface_consistency(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("surface consistency OK")
    return 0


def check_surface_consistency(repo_root: Path) -> list[str]:
    actual_commands = _actual_cli_commands(repo_root)
    documented_commands = _documented_cli_commands(
        repo_root / "docs" / "10-implementation-guide.md"
    )

    errors = []
    if actual_commands != documented_commands:
        errors.append(_format_command_drift(actual_commands, documented_commands))
    return errors


def _actual_cli_commands(repo_root: Path) -> list[str]:
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from shared_intake_governance.cli import pipeline

    parser = pipeline._parser()
    subparsers = _subparsers_action(parser)
    return list(subparsers.choices)


def _documented_cli_commands(path: Path) -> list[str]:
    commands = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CLI_COMMAND_PATTERN.fullmatch(line)
        if match:
            commands.append(match.group(1))
    return commands


def _subparsers_action(
    parser: argparse.ArgumentParser,
) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("CLI parser has no subcommands")


def _format_command_drift(
    actual_commands: list[str],
    documented_commands: list[str],
) -> str:
    missing_from_docs = [
        command for command in actual_commands if command not in documented_commands
    ]
    stale_in_docs = [
        command for command in documented_commands if command not in actual_commands
    ]
    order_mismatch = []
    for index, command in enumerate(actual_commands):
        documented = (
            documented_commands[index]
            if index < len(documented_commands)
            else "<missing>"
        )
        if command != documented:
            order_mismatch.append(
                f"index {index}: actual={command} documented={documented}"
            )

    parts = ["CLI surface drift in docs/10-implementation-guide.md."]
    if missing_from_docs:
        parts.append("Missing from docs: " + ", ".join(missing_from_docs))
    if stale_in_docs:
        parts.append("Stale in docs: " + ", ".join(stale_in_docs))
    if order_mismatch:
        parts.append("Order mismatch: " + "; ".join(order_mismatch[:5]))
    return "\n".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
