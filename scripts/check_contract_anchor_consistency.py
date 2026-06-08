#!/usr/bin/env python3
"""Check schema contract anchors across docs and schema files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ID_PREFIX = "https://shared-intake-governance.local/"


def main() -> int:
    errors = check_contract_anchor_consistency(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("contract anchor consistency OK")
    return 0


def check_contract_anchor_consistency(repo_root: Path) -> list[str]:
    schema_paths = _schema_paths(repo_root)
    index_schema_paths = _index_schema_refs(repo_root / "docs" / "INDEX.md")
    data_contract_schema_paths = _data_contract_schema_refs(
        repo_root / "docs" / "02-data-contracts.md"
    )
    implementation_schema_paths = _implementation_guide_schema_refs(
        repo_root / "docs" / "10-implementation-guide.md"
    )

    errors = []
    _check_members(
        errors,
        "docs/INDEX.md schema list",
        index_schema_paths,
        schema_paths,
    )
    _check_equal(
        errors,
        "docs/02-data-contracts.md",
        data_contract_schema_paths,
        index_schema_paths,
    )
    _check_equal(
        errors,
        "docs/10-implementation-guide.md",
        implementation_schema_paths,
        index_schema_paths,
    )
    _check_schema_ids(errors, repo_root, schema_paths)
    return errors


def _schema_paths(repo_root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "schemas").glob("*.schema.json")
    )


def _index_schema_refs(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    schema_refs = []
    for line in lines:
        if line == "## Schemas and examples":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        match = re.fullmatch(
            r"- \[\.\./(schemas/[A-Za-z0-9._-]+\.schema\.json)\]"
            r"\(\.\./\1\)",
            line,
        )
        if match:
            schema_refs.append(match.group(1))
    return schema_refs


def _data_contract_schema_refs(path: Path) -> list[str]:
    schema_refs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(
            r"See \[\.\./(schemas/[A-Za-z0-9._-]+\.schema\.json)\]"
            r"\(\.\./\1\)\.",
            line,
        )
        if match:
            schema_refs.append(match.group(1))
    return schema_refs


def _implementation_guide_schema_refs(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    schema_refs = []
    for line in lines:
        if line == "Current Phase 1 contract anchors:":
            in_section = True
            continue
        if in_section and line == "If these anchors drift, update the docs or schemas before adding runtime code.":
            break
        if not in_section:
            continue
        match = re.fullmatch(
            r"- [A-Za-z0-9 -]+: `(schemas/[A-Za-z0-9._-]+\.schema\.json)`",
            line,
        )
        if match:
            schema_refs.append(match.group(1))
    return schema_refs


def _check_schema_ids(
    errors: list[str],
    repo_root: Path,
    schema_paths: list[str],
) -> None:
    for schema_path in schema_paths:
        payload = _read_json(repo_root / schema_path)
        expected = SCHEMA_ID_PREFIX + schema_path
        actual = payload.get("$id")
        if actual != expected:
            errors.append(
                f"{schema_path} $id drifted.\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )


def _check_members(
    errors: list[str],
    label: str,
    actual: list[str],
    expected: list[str],
) -> None:
    missing = [item for item in expected if item not in actual]
    stale = [item for item in actual if item not in expected]
    if missing or stale:
        parts = [f"{label} contract anchors drifted."]
        if missing:
            parts.append("Missing: " + ", ".join(missing))
        if stale:
            parts.append("Stale: " + ", ".join(stale))
        errors.append("\n".join(parts))


def _check_equal(
    errors: list[str],
    label: str,
    actual: list[str],
    expected: list[str],
) -> None:
    if actual != expected:
        missing = [item for item in expected if item not in actual]
        stale = [item for item in actual if item not in expected]
        order_mismatch = []
        for index, expected_item in enumerate(expected):
            actual_item = actual[index] if index < len(actual) else "<missing>"
            if actual_item != expected_item:
                order_mismatch.append(
                    f"index {index}: expected={expected_item} actual={actual_item}"
                )

        parts = [f"{label} contract anchors drifted."]
        if missing:
            parts.append("Missing: " + ", ".join(missing))
        if stale:
            parts.append("Stale: " + ", ".join(stale))
        if order_mismatch:
            parts.append("Order mismatch: " + "; ".join(order_mismatch[:5]))
        errors.append("\n".join(parts))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
