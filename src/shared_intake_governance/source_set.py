"""Validation and inspection for source-set.v1 files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shared_intake_governance.projector.profile import load_profile
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

    seen_source_ids: set[str] = set()
    seen_source_config_paths: set[str] = set()
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
        if source_ref["source_config_path"] in seen_source_config_paths:
            raise ValueError(
                "sources must not contain duplicate source_config_path: "
                + source_ref["source_config_path"]
            )
        seen_source_config_paths.add(source_ref["source_config_path"])
        if source_ref["source_id"] in seen_source_ids:
            raise ValueError(
                "sources must not contain duplicate source_id: "
                + source_ref["source_id"]
            )
        seen_source_ids.add(source_ref["source_id"])
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
    seen_source_set_ids: set[str] = set()
    for source_set_path in sorted(source_set_root.glob("*.json")):
        source_set_ref = source_set_path.relative_to(root).as_posix()
        source_set = inspect_source_set(source_set_path, repo_root=root)
        if source_set["source_set_id"] in seen_source_set_ids:
            raise ValueError(
                "source set catalog has duplicate source_set_id: "
                + source_set["source_set_id"]
            )
        seen_source_set_ids.add(source_set["source_set_id"])
        source_set["source_set_ref"] = source_set_ref
        source_sets.append(source_set)
    return {
        "repo_root": str(root),
        "source_set_count": len(source_sets),
        "source_sets": source_sets,
    }


def check_source_set_profiles(
    source_set_path: str | Path,
    profile_paths: list[str] | list[Path],
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Validate source-set/profile compatibility without running sources."""
    if not profile_paths:
        raise ValueError("at least one profile path is required")

    root = Path(repo_root).resolve()
    source_set = inspect_source_set(source_set_path, repo_root=root)
    profiles = []
    profiles_without_matches = []
    total_matches = 0
    total_rejections = 0

    for profile_path in profile_paths:
        path = Path(profile_path).resolve()
        profile = load_profile(path)
        accepted_sources = set(profile["accepted_sources"])
        matched_sources = []
        rejected_sources = []

        for source in source_set["sources"]:
            source_entry = dict(source)
            if source["source_type"] in accepted_sources:
                matched_sources.append(source_entry)
                continue

            source_entry["reason"] = (
                "source_type "
                + source["source_type"]
                + " is not accepted by "
                + profile["profile_id"]
            )
            rejected_sources.append(source_entry)

        compatible = bool(matched_sources)
        if not compatible:
            profiles_without_matches.append(profile["profile_id"])
        total_matches += len(matched_sources)
        total_rejections += len(rejected_sources)
        profiles.append(
            {
                "profile_path": str(path),
                "profile_ref": _path_ref(path, root),
                "profile_id": profile["profile_id"],
                "accepted_sources": profile["accepted_sources"],
                "compatible": compatible,
                "matched_source_count": len(matched_sources),
                "rejected_source_count": len(rejected_sources),
                "matched_sources": matched_sources,
                "rejected_sources": rejected_sources,
            }
        )

    return {
        "repo_root": str(root),
        "source_set_path": source_set["source_set_path"],
        "source_set_id": source_set["source_set_id"],
        "source_count": source_set["source_count"],
        "profile_count": len(profiles),
        "compatible": not profiles_without_matches,
        "profiles_without_matches": profiles_without_matches,
        "total_matches": total_matches,
        "total_rejections": total_rejections,
        "profiles": profiles,
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


def _path_ref(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source set must be a JSON object")
    return payload
