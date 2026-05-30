"""Validation and loading for source-config.v1 files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shared_intake_governance.validation import require_https_url


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SOURCE_TRUST = {"official", "maintainer", "platform", "secondary", "social", "unknown"}
_SOURCE_TYPES = {
    "github_repo",
    "github_search",
    "arxiv_query",
    "news",
    "rss",
}


def load_source_config(path: str | Path) -> dict[str, Any]:
    """Load and validate one source-config.v1 file."""
    config = _read_json(Path(path))
    return validate_source_config(config)


def validate_source_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one supported source-config.v1 payload."""
    if config.get("schema_version") != "source-config.v1":
        raise ValueError("source config must use schema_version source-config.v1")
    _require_text(config, "source_type")
    _require_text(config, "source_id")
    _safe_segment(config["source_id"], "source_id")

    source_type = config["source_type"]
    if source_type not in _SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {source_type}")
    if source_type == "github_repo":
        return _validate_github_repo_config(config)
    if source_type == "github_search":
        return _validate_query_config(
            config,
            required_field="query",
            default_api_base_url="https://api.github.com",
        )
    if source_type == "arxiv_query":
        return _validate_query_config(
            config,
            required_field="query",
            default_api_base_url="https://export.arxiv.org/api/query",
        )
    return _validate_feed_config(config)


def _validate_github_repo_config(config: dict[str, Any]) -> dict[str, Any]:
    _require_fields(config, {"owner", "repo"})
    _reject_unknown(
        config,
        {
            "schema_version",
            "source_type",
            "source_id",
            "owner",
            "repo",
            "api_base_url",
        },
    )
    _require_text(config, "owner")
    _require_text(config, "repo")
    result = dict(config)
    result.setdefault("api_base_url", "https://api.github.com")
    _require_https_url(result, "api_base_url")
    return result


def _validate_query_config(
    config: dict[str, Any],
    *,
    required_field: str,
    default_api_base_url: str,
) -> dict[str, Any]:
    _require_fields(config, {required_field, "max_results"})
    _reject_unknown(
        config,
        {
            "schema_version",
            "source_type",
            "source_id",
            required_field,
            "max_results",
            "api_base_url",
        },
    )
    _require_text(config, required_field)
    _require_max_results(config)
    result = dict(config)
    result.setdefault("api_base_url", default_api_base_url)
    _require_https_url(result, "api_base_url")
    return result


def _validate_feed_config(config: dict[str, Any]) -> dict[str, Any]:
    _require_fields(config, {"feed_url"})
    _reject_unknown(
        config,
        {
            "schema_version",
            "source_type",
            "source_id",
            "feed_url",
            "source_trust",
        },
    )
    result = dict(config)
    result.setdefault("source_trust", "secondary")
    _require_https_url(result, "feed_url")
    if result["source_trust"] not in _SOURCE_TRUST:
        raise ValueError("source config has unsupported source_trust")
    return result


def _require_max_results(config: dict[str, Any]) -> None:
    value = config.get("max_results")
    if type(value) is not int:
        raise ValueError("max_results must be an integer")
    if not 1 <= value <= 100:
        raise ValueError("max_results must be between 1 and 100")


def _require_fields(config: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(
            "source config missing required fields: " + ", ".join(missing)
        )


def _reject_unknown(config: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(config) - allowed)
    if unknown:
        raise ValueError(f"source config has unknown fields: {', '.join(unknown)}")


def _require_text(config: dict[str, Any], field: str) -> None:
    if not isinstance(config.get(field), str) or not config[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value


def _require_https_url(config: dict[str, Any], field: str) -> None:
    require_https_url(config.get(field), field)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("source config must be a JSON object")
    return payload
