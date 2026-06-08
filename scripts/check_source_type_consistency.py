#!/usr/bin/env python3
"""Check source-type lists across code, schemas, and source-of-truth docs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CUSTOM_SOURCE_TYPE = "custom"
SCHEMA_SOURCE_TYPE_ENUMS = {
    "schemas/clean-record.schema.json": ("properties", "source_type", "enum"),
    "schemas/raw-metadata.schema.json": ("properties", "source_type", "enum"),
    "schemas/source-health.schema.json": ("properties", "source_type", "enum"),
    "schemas/profile.schema.json": (
        "properties",
        "accepted_sources",
        "items",
        "enum",
    ),
}


def main() -> int:
    errors = check_source_type_consistency(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("source type consistency OK")
    return 0


def check_source_type_consistency(repo_root: Path) -> list[str]:
    implemented_source_types = _source_config_schema_types(repo_root)
    contract_source_types = implemented_source_types + [CUSTOM_SOURCE_TYPE]
    errors = []

    _check_equal(
        errors,
        "source_config._SOURCE_TYPES",
        _code_source_types(repo_root, "shared_intake_governance.source_config"),
        implemented_source_types,
        compare_order=False,
    )
    _check_equal(
        errors,
        "runtime.writers._SOURCE_TYPES",
        _code_source_types(repo_root, "shared_intake_governance.runtime.writers"),
        contract_source_types,
        compare_order=False,
    )
    _check_equal(
        errors,
        "sanitizer.clean_records._SOURCE_TYPES",
        _code_source_types(
            repo_root,
            "shared_intake_governance.sanitizer.clean_records",
        ),
        contract_source_types,
        compare_order=False,
    )

    for schema_ref, path_parts in SCHEMA_SOURCE_TYPE_ENUMS.items():
        _check_equal(
            errors,
            schema_ref,
            _schema_enum(repo_root / schema_ref, path_parts),
            contract_source_types,
        )

    _check_equal(
        errors,
        "docs/12-current-surface-audit.md implemented source families",
        _audit_implemented_source_types(
            repo_root / "docs" / "12-current-surface-audit.md"
        ),
        implemented_source_types,
    )
    _check_custom_boundary(
        errors,
        repo_root / "docs" / "12-current-surface-audit.md",
    )
    return errors


def _source_config_schema_types(repo_root: Path) -> list[str]:
    schema = _read_json(repo_root / "schemas" / "source-config.schema.json")
    return [
        variant["properties"]["source_type"]["const"]
        for variant in schema["oneOf"]
    ]


def _code_source_types(repo_root: Path, module_name: str) -> list[str]:
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    module = __import__(module_name, fromlist=["_SOURCE_TYPES"])
    return sorted(module._SOURCE_TYPES)


def _schema_enum(path: Path, path_parts: tuple[str, ...]) -> list[str]:
    value: Any = _read_json(path)
    for part in path_parts:
        value = value[part]
    return list(value)


def _audit_implemented_source_types(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    in_list = False
    source_types = []
    for line in lines:
        if line == "## Implemented source families":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        if line.endswith("manifest output for:"):
            in_list = True
            continue
        if in_list and not line and not source_types:
            continue
        if in_list and not line:
            break
        if in_list:
            match = re.fullmatch(r"- `([A-Za-z0-9_]+)`", line)
            if match:
                source_types.append(match.group(1))
    return source_types


def _check_custom_boundary(errors: list[str], path: Path) -> None:
    audit_text = path.read_text(encoding="utf-8")
    expected = (
        "`custom` remains a contract-level source type for consumer-owned or "
        "future\nruntime paths. It does not currently have a shared collector "
        "or source-config\ndispatch path."
    )
    if expected not in audit_text:
        errors.append(
            "docs/12-current-surface-audit.md must state the custom "
            "contract-only source boundary"
        )


def _check_equal(
    errors: list[str],
    label: str,
    actual: list[str],
    expected: list[str],
    *,
    compare_order: bool = True,
) -> None:
    if compare_order:
        drifted = actual != expected
    else:
        drifted = set(actual) != set(expected)
    if drifted:
        errors.append(
            f"{label} source types drifted.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
