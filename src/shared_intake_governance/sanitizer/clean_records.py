"""Emit safe clean records from raw evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared_intake_governance.runtime import RuntimePaths


SANITIZER_VERSION = "clean-record.v1"
SUMMARY_MAX_LENGTH = 500
_SOURCE_TYPES = {
    "github_repo",
    "github_search",
    "arxiv_query",
    "arxiv_rss_keywords",
    "rss",
    "news",
    "custom",
}
_SOURCE_TRUST = {"official", "maintainer", "platform", "secondary", "social", "unknown"}
_REQUIRED_CLEAN_FIELDS = {
    "record_id",
    "source_id",
    "source_type",
    "canonical_url",
    "title",
    "sanitized_summary",
    "source_trust",
    "risk_flags",
    "quarantined",
    "raw_hash",
    "sanitizer_version",
}
_OPTIONAL_CLEAN_FIELDS = {"published_at", "license_or_terms_note"}
_ALLOWED_CLEAN_FIELDS = _REQUIRED_CLEAN_FIELDS | _OPTIONAL_CLEAN_FIELDS
_RISK_PATTERNS = {
    "instruction_like_content": [
        "ignore previous instructions",
        "ignore all previous instructions",
        "system prompt",
        "developer message",
    ],
    "tool_escalation_language": [
        "use tool",
        "tool access",
        "run shell",
        "run command",
        "execute command",
    ],
    "credential_bait": [
        "api key",
        "password",
        "secret token",
    ],
}
_QUARANTINE_FLAGS = {
    "instruction_like_content",
    "tool_escalation_language",
    "credential_bait",
}


@dataclass(frozen=True)
class CleanRecordWrite:
    record: dict[str, Any]
    path: Path


class CleanRecordEmitter:
    """Convert raw source evidence into one provider-neutral clean record."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def emit_from_raw_metadata(self, metadata_path: str | Path) -> CleanRecordWrite:
        metadata = _read_json(Path(metadata_path))
        if metadata.get("fetch_status") != "success":
            raise ValueError("only successful raw metadata can emit clean records")
        if metadata.get("body_hash") is None or metadata.get("storage_path") is None:
            raise ValueError("successful raw metadata must include body storage")

        body_path = Path(str(metadata["storage_path"]))
        body = body_path.read_bytes()
        body_hash = hashlib.sha256(body).hexdigest()
        if body_hash != metadata["body_hash"]:
            raise ValueError("raw body hash does not match metadata")

        if metadata["source_type"] == "github_repo":
            record = _github_repo_clean_record(metadata, body)
        else:
            raise ValueError(f"unsupported source_type: {metadata['source_type']}")

        validate_clean_record(record)
        path = self.paths.clean_record_path(record["record_id"])
        _write_json(path, record)
        return CleanRecordWrite(record=record, path=path)


def validate_clean_record(record: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_CLEAN_FIELDS - set(record))
    if missing:
        raise ValueError(f"clean record missing required fields: {', '.join(missing)}")

    extra = sorted(set(record) - _ALLOWED_CLEAN_FIELDS)
    if extra:
        raise ValueError(f"clean record has unknown fields: {', '.join(extra)}")

    _require_text(record, "record_id")
    _require_text(record, "source_id")
    _require_text(record, "canonical_url")
    _require_text(record, "title")
    _require_text(record, "raw_hash")
    _require_text(record, "sanitizer_version")

    if record["source_type"] not in _SOURCE_TYPES:
        raise ValueError("clean record has unsupported source_type")
    if record["source_trust"] not in _SOURCE_TRUST:
        raise ValueError("clean record has unsupported source_trust")
    if not isinstance(record["sanitized_summary"], str):
        raise ValueError("sanitized_summary must be a string")
    if not isinstance(record["risk_flags"], list) or not all(
        isinstance(flag, str) for flag in record["risk_flags"]
    ):
        raise ValueError("risk_flags must be a list of strings")
    if not isinstance(record["quarantined"], bool):
        raise ValueError("quarantined must be a boolean")
    if "published_at" in record and record["published_at"] is not None:
        _require_text(record, "published_at")
    if "license_or_terms_note" in record and record["license_or_terms_note"] is not None:
        _require_text(record, "license_or_terms_note")


def _github_repo_clean_record(metadata: dict[str, Any], body: bytes) -> dict[str, Any]:
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("github_repo raw body must be a JSON object")

    canonical_url = _clean_text(metadata.get("canonical_url") or payload.get("html_url"))
    title = _clean_text(payload.get("full_name") or payload.get("name") or canonical_url)
    description = _clean_text(payload.get("description") or "")
    topics = payload.get("topics") if isinstance(payload.get("topics"), list) else []
    topic_text = ", ".join(str(topic) for topic in topics if str(topic))
    summary = _cap_length(
        _clean_text(
            " ".join(
                part
                for part in [
                    description,
                    f"Topics: {topic_text}" if topic_text else "",
                ]
                if part
            )
        )
    )
    risk_flags = _risk_flags(" ".join([description, topic_text]))

    return {
        "record_id": _record_id("github_repo", canonical_url),
        "source_id": metadata["source_id"],
        "source_type": "github_repo",
        "canonical_url": canonical_url,
        "title": title,
        "sanitized_summary": summary,
        "published_at": _optional_text(payload.get("created_at")),
        "license_or_terms_note": _license_note(payload.get("license")),
        "source_trust": "platform",
        "risk_flags": risk_flags,
        "quarantined": bool(set(risk_flags) & _QUARANTINE_FLAGS),
        "raw_hash": metadata["body_hash"],
        "sanitizer_version": SANITIZER_VERSION,
    }


def _risk_flags(text: str) -> list[str]:
    lowered = text.lower()
    flags = [
        flag
        for flag, patterns in _RISK_PATTERNS.items()
        if any(pattern in lowered for pattern in patterns)
    ]
    return sorted(flags)


def _record_id(source_type: str, canonical_url: str) -> str:
    digest = hashlib.sha256(f"{source_type}:{canonical_url}".encode("utf-8")).hexdigest()
    return f"{source_type}-{digest[:16]}"


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _cap_length(value: str) -> str:
    if len(value) <= SUMMARY_MAX_LENGTH:
        return value
    return value[: SUMMARY_MAX_LENGTH - 3].rstrip() + "..."


def _license_note(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    spdx_id = value.get("spdx_id")
    if not spdx_id or spdx_id == "NOASSERTION":
        return None
    return f"license: {_clean_text(spdx_id)}"


def _optional_text(value: Any) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _require_text(record: dict[str, Any], field: str) -> None:
    if not isinstance(record[field], str) or not record[field]:
        raise ValueError(f"{field} must be a non-empty string")


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
