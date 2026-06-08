"""Project clean records into one explicit profile output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared_intake_governance.runtime import RuntimePaths
from shared_intake_governance.sanitizer import validate_clean_record
from shared_intake_governance.validation import require_absolute_uri, require_date_time


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_OUTPUT_MODES = {"research_digest", "benchmark_brief", "news_brief", "custom"}
_SOURCE_TYPES = {
    "github_repo",
    "github_releases",
    "github_search",
    "arxiv_query",
    "rss",
    "news",
    "custom",
}
_SOURCE_TRUST = {"official", "maintainer", "platform", "secondary", "social", "unknown"}
_PROVIDERS = {"claude", "gemini", "agy", "vibe"}
_PROFILE_REQUIRED = {
    "profile_id",
    "description",
    "accepted_sources",
    "keywords",
    "output_mode",
}
_PROFILE_OPTIONAL = {"required_risk_flags_absent", "provider_preferences"}
_PROFILE_ALLOWED = _PROFILE_REQUIRED | _PROFILE_OPTIONAL
_PROJECTION_REQUIRED = {
    "schema_version",
    "profile_id",
    "output_mode",
    "generated_at",
    "counts",
    "items",
}
_PROJECTION_ALLOWED = _PROJECTION_REQUIRED
_PROJECTION_COUNT_REQUIRED = {
    "clean_records_seen",
    "items_written",
    "excluded_by_source",
    "excluded_by_keyword",
    "excluded_by_risk",
    "excluded_quarantined",
    "excluded_seen",
}
_PROJECTION_ITEM_REQUIRED = {
    "record_id",
    "source_id",
    "source_type",
    "canonical_url",
    "title",
    "sanitized_summary",
    "source_trust",
    "risk_flags",
    "raw_hash",
}


@dataclass(frozen=True)
class ProfileProjectionWrite:
    report: dict[str, Any]
    path: Path


class ProfileProjector:
    """Filter clean records through one explicit profile."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def project(
        self,
        profile_path: str | Path,
        *,
        output_id: str,
        generated_at: datetime | None = None,
        exclude_record_ids: set[str] | None = None,
    ) -> ProfileProjectionWrite:
        profile = load_profile(profile_path)
        generated_at_text = _format_utc(generated_at or datetime.now(timezone.utc))
        output_segment = _safe_segment(output_id, "output_id")
        seen_record_ids = _normalize_record_ids(exclude_record_ids or set())

        counts = {
            "clean_records_seen": 0,
            "items_written": 0,
            "excluded_by_source": 0,
            "excluded_by_keyword": 0,
            "excluded_by_risk": 0,
            "excluded_quarantined": 0,
            "excluded_seen": 0,
        }
        items = []

        for record_path in sorted(self.paths.clean_root.glob("*.json")):
            record = _read_json(record_path)
            validate_clean_record(record)
            counts["clean_records_seen"] += 1

            if record["source_type"] not in profile["accepted_sources"]:
                counts["excluded_by_source"] += 1
                continue
            if not _matches_keywords(record, profile["keywords"]):
                counts["excluded_by_keyword"] += 1
                continue
            if set(record["risk_flags"]) & set(profile["required_risk_flags_absent"]):
                counts["excluded_by_risk"] += 1
                continue
            if record["quarantined"]:
                counts["excluded_quarantined"] += 1
                continue
            if record["record_id"] in seen_record_ids:
                counts["excluded_seen"] += 1
                continue

            items.append(_project_item(record))

        items.sort(key=lambda item: item["record_id"])
        counts["items_written"] = len(items)
        report = {
            "schema_version": "profile-projection.v1",
            "profile_id": profile["profile_id"],
            "output_mode": profile["output_mode"],
            "generated_at": generated_at_text,
            "counts": counts,
            "items": items,
        }
        validate_profile_projection(report)
        path = (
            self.paths.profile_reports_dir(profile["profile_id"])
            / f"{output_segment}.json"
        )
        _write_json(path, report)
        return ProfileProjectionWrite(report=report, path=path)


def load_profile(profile_path: str | Path) -> dict[str, Any]:
    profile = _read_json(Path(profile_path))
    missing = sorted(_PROFILE_REQUIRED - set(profile))
    if missing:
        raise ValueError(f"profile missing required fields: {', '.join(missing)}")
    extra = sorted(set(profile) - _PROFILE_ALLOWED)
    if extra:
        raise ValueError(f"profile has unknown fields: {', '.join(extra)}")

    _require_text(profile, "profile_id")
    _safe_segment(profile["profile_id"], "profile_id")
    _require_text(profile, "description")
    _require_string_list(profile, "accepted_sources")
    if not profile["accepted_sources"]:
        raise ValueError("accepted_sources must be a non-empty list")
    unsupported_sources = sorted(
        source
        for source in profile["accepted_sources"]
        if source not in _SOURCE_TYPES
    )
    if unsupported_sources:
        raise ValueError(
            "profile has unsupported accepted source: "
            + ", ".join(unsupported_sources)
        )
    _require_string_list(profile, "keywords")
    if profile["output_mode"] not in _OUTPUT_MODES:
        raise ValueError("profile has unsupported output_mode")

    profile = dict(profile)
    profile.setdefault("required_risk_flags_absent", [])
    _require_string_list(profile, "required_risk_flags_absent")
    if "provider_preferences" in profile:
        _require_string_list(profile, "provider_preferences")
        if any(provider not in _PROVIDERS for provider in profile["provider_preferences"]):
            raise ValueError("profile has unsupported provider preference")
    return profile


def inspect_profile(profile_path: str | Path) -> dict[str, Any]:
    """Validate one profile config and return its normalized read-only summary."""
    path = Path(profile_path).resolve()
    profile = load_profile(path)
    result = _profile_summary(profile, path)
    result["keywords"] = profile["keywords"]
    return result


def list_profiles(repo_root: str | Path = ".") -> dict[str, Any]:
    """Validate tracked profile configs and return a deterministic inventory."""
    root = Path(repo_root).resolve()
    profile_root = root / "profiles" / "examples"
    profiles = []
    seen_profile_ids: set[str] = set()
    for profile_path in sorted(profile_root.glob("*.json")):
        profile = load_profile(profile_path)
        if profile["profile_id"] in seen_profile_ids:
            raise ValueError(
                "profile catalog has duplicate profile_id: "
                + profile["profile_id"]
            )
        seen_profile_ids.add(profile["profile_id"])
        profiles.append(_profile_summary(profile, profile_path.resolve()))
    profiles.sort(
        key=lambda profile: (profile["profile_id"], profile["profile_ref"])
    )
    return {
        "repo_root": str(root),
        "profile_count": len(profiles),
        "profiles": profiles,
    }


def validate_profile_projection(report: dict[str, Any]) -> None:
    missing = sorted(_PROJECTION_REQUIRED - set(report))
    if missing:
        raise ValueError(
            f"profile projection missing required fields: {', '.join(missing)}"
        )
    extra = sorted(set(report) - _PROJECTION_ALLOWED)
    if extra:
        raise ValueError(
            f"profile projection has unknown fields: {', '.join(extra)}"
        )

    if report["schema_version"] != "profile-projection.v1":
        raise ValueError("profile projection must use profile-projection.v1")
    _require_text(report, "profile_id")
    _safe_segment(report["profile_id"], "profile_id")
    if report["output_mode"] not in _OUTPUT_MODES:
        raise ValueError("profile projection has unsupported output_mode")
    _require_text(report, "generated_at")
    require_date_time(report["generated_at"], "generated_at")

    counts = report["counts"]
    if not isinstance(counts, dict):
        raise ValueError("profile projection counts must be an object")
    count_missing = sorted(_PROJECTION_COUNT_REQUIRED - set(counts))
    if count_missing:
        raise ValueError(
            "profile projection counts missing required fields: "
            + ", ".join(count_missing)
        )
    count_extra = sorted(set(counts) - _PROJECTION_COUNT_REQUIRED)
    if count_extra:
        raise ValueError(
            "profile projection counts has unknown fields: "
            + ", ".join(count_extra)
        )
    for field in sorted(_PROJECTION_COUNT_REQUIRED):
        if not isinstance(counts[field], int) or counts[field] < 0:
            raise ValueError(f"profile projection count {field} must be non-negative")

    items = report["items"]
    if not isinstance(items, list):
        raise ValueError("profile projection items must be a list")
    for item in items:
        _validate_projection_item(item)

    if counts["items_written"] != len(items):
        raise ValueError("profile projection items_written must match item count")
    counted_records = (
        counts["items_written"]
        + counts["excluded_by_source"]
        + counts["excluded_by_keyword"]
        + counts["excluded_by_risk"]
        + counts["excluded_quarantined"]
        + counts["excluded_seen"]
    )
    if counts["clean_records_seen"] != counted_records:
        raise ValueError(
            "profile projection clean_records_seen must equal items_written plus exclusions"
        )


def _validate_projection_item(item: Any) -> None:
    if not isinstance(item, dict):
        raise ValueError("profile projection item must be an object")
    missing = sorted(_PROJECTION_ITEM_REQUIRED - set(item))
    if missing:
        raise ValueError(
            f"profile projection item missing required fields: {', '.join(missing)}"
        )
    extra = sorted(set(item) - _PROJECTION_ITEM_REQUIRED)
    if extra:
        raise ValueError(
            f"profile projection item has unknown fields: {', '.join(extra)}"
        )

    _require_text(item, "record_id")
    _require_text(item, "source_id")
    _safe_segment(item["record_id"], "record_id")
    _safe_segment(item["source_id"], "source_id")
    _require_text(item, "canonical_url")
    require_absolute_uri(item["canonical_url"], "canonical_url")
    _require_text(item, "title")
    _require_text(item, "raw_hash")
    if item["source_type"] not in _SOURCE_TYPES:
        raise ValueError("profile projection item has unsupported source_type")
    if item["source_trust"] not in _SOURCE_TRUST:
        raise ValueError("profile projection item has unsupported source_trust")
    if not isinstance(item["sanitized_summary"], str):
        raise ValueError("profile projection item summary must be a string")
    if not isinstance(item["risk_flags"], list) or not all(
        isinstance(flag, str) for flag in item["risk_flags"]
    ):
        raise ValueError("profile projection item risk_flags must be strings")


def _matches_keywords(record: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = f"{record['title']} {record['sanitized_summary']}".lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _normalize_record_ids(record_ids: set[str]) -> set[str]:
    normalized = set()
    for record_id in record_ids:
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("record_id must be a non-empty string")
        normalized.add(_safe_segment(record_id, "record_id"))
    return normalized


def _project_item(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record["record_id"],
        "source_id": record["source_id"],
        "source_type": record["source_type"],
        "canonical_url": record["canonical_url"],
        "title": record["title"],
        "sanitized_summary": record["sanitized_summary"],
        "source_trust": record["source_trust"],
        "risk_flags": record["risk_flags"],
        "raw_hash": record["raw_hash"],
    }


def _profile_summary(profile: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "profile_path": str(path),
        "profile_ref": _profile_ref(path),
        "profile_id": profile["profile_id"],
        "description": profile["description"],
        "accepted_sources": profile["accepted_sources"],
        "keyword_count": len(profile["keywords"]),
        "required_risk_flags_absent": profile["required_risk_flags_absent"],
        "output_mode": profile["output_mode"],
        "provider_preferences": profile.get("provider_preferences", []),
    }


def _profile_ref(path: Path) -> str:
    if path.parent.name == "examples" and path.parent.parent.name == "profiles":
        return f"profiles/examples/{path.name}"
    return str(path)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value


def _require_text(profile: dict[str, Any], field: str) -> None:
    if not isinstance(profile[field], str) or not profile[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _require_string_list(profile: dict[str, Any], field: str) -> None:
    if not isinstance(profile[field], list) or not all(
        isinstance(item, str) for item in profile[field]
    ):
        raise ValueError(f"{field} must be a list of strings")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
