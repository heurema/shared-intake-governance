"""Validation and inspection for source-set.v1 files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shared_intake_governance.source_config import load_source_config


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SOURCE_CONFIG_REF = re.compile(
    r"^sources/examples/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
)


def load_source_set(path: str | Path) -> dict[str, Any]:
    """Load and validate one source-set.v1 file."""
    source_set = _read_json(Path(path))
    return validate_source_set(source_set)


def validate_source_set(source_set: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one source-set.v1 payload."""
    if source_set.get("schema_version") != "source-set.v1":
        raise ValueError("source set must use schema_version source-set.v1")
    _require_text(source_set, "source_set_id")
    _safe_segment(source_set["source_set_id"], "source_set_id")
    _reject_unknown(
        source_set,
        {
            "schema_version",
            "source_set_id",
            "description",
            "sources",
        },
    )
    if "description" in source_set:
        _require_text(source_set, "description")

    sources = source_set.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty array")

    seen_refs: set[tuple[str, str]] = set()
    normalized_sources = []
    for index, source_ref in enumerate(sources):
        if not isinstance(source_ref, dict):
            raise ValueError(f"sources[{index}] must be an object")
        _reject_unknown(source_ref, {"source_id", "source_config_path"})
        _require_text(source_ref, "source_id")
        _require_text(source_ref, "source_config_path")
        _safe_segment(source_ref["source_id"], f"sources[{index}].source_id")
        _source_config_ref(
            source_ref["source_config_path"],
            f"sources[{index}].source_config_path",
        )
        ref_key = (source_ref["source_id"], source_ref["source_config_path"])
        if ref_key in seen_refs:
            raise ValueError("sources must not contain duplicate refs")
        seen_refs.add(ref_key)
        normalized_sources.append(dict(source_ref))

    result = dict(source_set)
    result["sources"] = normalized_sources
    return result


def inspect_source_set(
    source_set_path: str | Path,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Validate a source set and its referenced source configs without writes."""
    source_set_file = Path(source_set_path).resolve()
    root = Path(repo_root).resolve()
    source_set = load_source_set(source_set_file)
    inspected_sources = []

    for source_ref in source_set["sources"]:
        config_path = root / source_ref["source_config_path"]
        if not config_path.is_file():
            raise ValueError(
                "source config not found: " + source_ref["source_config_path"]
            )
        source_config = load_source_config(config_path)
        if source_ref["source_id"] != source_config["source_id"]:
            raise ValueError(
                "source_id mismatch for "
                + source_ref["source_config_path"]
                + ": source set has "
                + source_ref["source_id"]
                + ", source config has "
                + source_config["source_id"]
            )
        inspected_sources.append(
            {
                "source_id": source_ref["source_id"],
                "source_type": source_config["source_type"],
                "source_config_ref": source_ref["source_config_path"],
                "source_config_path": str(config_path),
            }
        )

    return {
        "source_set_path": str(source_set_file),
        "repo_root": str(root),
        "schema_version": source_set["schema_version"],
        "source_set_id": source_set["source_set_id"],
        "source_count": len(inspected_sources),
        "sources": inspected_sources,
    }


def list_source_sets(repo_root: str | Path = ".") -> dict[str, Any]:
    """Validate tracked source-set.v1 files and return a deterministic inventory."""
    root = Path(repo_root).resolve()
    source_set_root = root / "sources" / "sets"
    source_sets = []
    for source_set_path in sorted(source_set_root.glob("*.json")):
        source_set = inspect_source_set(source_set_path, repo_root=root)
        source_set["source_set_ref"] = source_set_path.relative_to(root).as_posix()
        source_sets.append(source_set)
    return {
        "repo_root": str(root),
        "source_set_count": len(source_sets),
        "source_sets": source_sets,
    }


def _reject_unknown(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError("source set has unknown fields: " + ", ".join(unknown))


def _require_text(payload: dict[str, Any], field: str) -> None:
    if not isinstance(payload.get(field), str) or not payload[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value


def _source_config_ref(value: str, label: str) -> str:
    if not _SOURCE_CONFIG_REF.fullmatch(value):
        raise ValueError(f"{label} must reference sources/examples/*.json")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source set must be a JSON object")
    return payload
