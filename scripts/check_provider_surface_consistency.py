#!/usr/bin/env python3
"""Check provider and provider-preset lists across code, schemas, and docs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_SCHEMA_ENUMS = {
    "schemas/profile.schema.json": (
        "properties",
        "provider_preferences",
        "items",
        "enum",
    ),
    "schemas/provider-request.schema.json": ("properties", "provider", "enum"),
    "schemas/provider-result.schema.json": ("properties", "provider", "enum"),
}


def main() -> int:
    errors = check_provider_surface_consistency(ROOT)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("provider surface consistency OK")
    return 0


def check_provider_surface_consistency(repo_root: Path) -> list[str]:
    preset_ids = _provider_preset_ids(repo_root)
    providers = _provider_names(repo_root, preset_ids)
    errors = []

    for schema_ref, path_parts in PROVIDER_SCHEMA_ENUMS.items():
        _check_equal(
            errors,
            schema_ref,
            _schema_enum(repo_root / schema_ref, path_parts),
            providers,
        )

    _check_equal(
        errors,
        "schemas/provider-request.schema.json preset_id",
        _schema_enum(
            repo_root / "schemas" / "provider-request.schema.json",
            ("properties", "preset_id", "enum"),
        ),
        preset_ids,
    )
    _check_equal(
        errors,
        "runtime.writers._PROVIDERS",
        _code_providers(repo_root, "shared_intake_governance.runtime.writers"),
        providers,
        compare_order=False,
    )
    _check_equal(
        errors,
        "projector.profile._PROVIDERS",
        _code_providers(repo_root, "shared_intake_governance.projector.profile"),
        providers,
        compare_order=False,
    )
    _check_equal(
        errors,
        "docs/01-architecture.md provider adapters",
        _architecture_provider_adapters(repo_root / "docs" / "01-architecture.md"),
        providers,
    )
    _check_equal(
        errors,
        "docs/02-data-contracts.md provider request preset ids",
        _data_contract_preset_ids(repo_root / "docs" / "02-data-contracts.md"),
        preset_ids,
    )
    _check_equal(
        errors,
        "docs/11-local-runbook.md current read-only presets",
        _runbook_preset_ids(repo_root / "docs" / "11-local-runbook.md"),
        preset_ids,
    )
    return errors


def _provider_preset_ids(repo_root: Path) -> list[str]:
    _add_src_path(repo_root)
    from shared_intake_governance.provider_presets import provider_preset_ids

    return list(provider_preset_ids())


def _provider_names(repo_root: Path, preset_ids: list[str]) -> list[str]:
    _add_src_path(repo_root)
    from shared_intake_governance.provider_presets import resolve_provider_preset

    providers = []
    for preset_id in preset_ids:
        provider = resolve_provider_preset(preset_id)["provider"]
        if provider not in providers:
            providers.append(provider)
    return providers


def _code_providers(repo_root: Path, module_name: str) -> list[str]:
    _add_src_path(repo_root)
    module = __import__(module_name, fromlist=["_PROVIDERS"])
    return sorted(module._PROVIDERS)


def _schema_enum(path: Path, path_parts: tuple[str, ...]) -> list[str]:
    value: Any = _read_json(path)
    for part in path_parts:
        value = value[part]
    return list(value)


def _architecture_provider_adapters(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_section = False
    providers = []
    for line in lines:
        if line == "### 8. Provider adapters":
            in_section = True
            continue
        if in_section and line.startswith("### "):
            break
        if not in_section:
            continue
        match = re.fullmatch(r"- `([A-Za-z0-9_]+)`", line)
        if match:
            providers.append(match.group(1))
    return providers


def _data_contract_preset_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"Current preset ids are ([^.]+)\.", text)
    if not match:
        return []
    return re.findall(r"`([A-Za-z0-9_]+)`", match.group(1))


def _runbook_preset_ids(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_list = False
    preset_ids = []
    for line in lines:
        if line == "Current read-only presets:":
            in_list = True
            continue
        if in_list and not line and preset_ids:
            break
        if not in_list:
            continue
        match = re.fullmatch(r"- `([A-Za-z0-9_]+)`", line)
        if match:
            preset_ids.append(match.group(1))
    return preset_ids


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
            f"{label} provider surface drifted.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _add_src_path(repo_root: Path) -> None:
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


if __name__ == "__main__":
    raise SystemExit(main())
