"""Emit safe clean records from raw evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ElementTree
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
_ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class CleanRecordWrite:
    record: dict[str, Any]
    path: Path


class CleanRecordEmitter:
    """Convert raw source evidence into one provider-neutral clean record."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def emit_from_raw_metadata(self, metadata_path: str | Path) -> CleanRecordWrite:
        records = self._records_from_raw_metadata(metadata_path)
        if len(records) != 1:
            raise ValueError(
                "raw metadata emits multiple clean records; use "
                "emit_all_from_raw_metadata"
            )
        return self._write_clean_record(records[0])

    def emit_all_from_raw_metadata(
        self, metadata_path: str | Path
    ) -> list[CleanRecordWrite]:
        records = self._records_from_raw_metadata(metadata_path)
        return [self._write_clean_record(record) for record in records]

    def _records_from_raw_metadata(self, metadata_path: str | Path) -> list[dict[str, Any]]:
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
            return [_github_repo_clean_record(metadata, body)]
        if metadata["source_type"] == "arxiv_rss_keywords":
            return _arxiv_rss_keywords_clean_records(metadata, body)
        if metadata["source_type"] == "rss":
            return _rss_clean_records(metadata, body)

        raise ValueError(f"unsupported source_type: {metadata['source_type']}")

    def _write_clean_record(self, record: dict[str, Any]) -> CleanRecordWrite:
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


def _arxiv_rss_keywords_clean_records(
    metadata: dict[str, Any], body: bytes
) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise ValueError("arxiv_rss_keywords raw body must be valid Atom XML") from exc

    entries = _atom_entries(root)
    if not entries:
        raise ValueError("arxiv_rss_keywords raw body must include at least one entry")

    return [_arxiv_entry_clean_record(metadata, entry) for entry in entries]


def _arxiv_entry_clean_record(
    metadata: dict[str, Any], entry: ElementTree.Element
) -> dict[str, Any]:
    canonical_url = _clean_text(_atom_text(entry, "id"))
    if not canonical_url:
        raise ValueError("arxiv_rss_keywords entry must include an id")

    title = _clean_text(_atom_text(entry, "title") or canonical_url)
    summary = _cap_length(_clean_text(_atom_text(entry, "summary")))
    published_at = _optional_text(
        _atom_text(entry, "published") or _atom_text(entry, "updated")
    )
    risk_flags = _risk_flags(" ".join([title, summary]))

    return {
        "record_id": _record_id("arxiv_rss_keywords", canonical_url),
        "source_id": metadata["source_id"],
        "source_type": "arxiv_rss_keywords",
        "canonical_url": canonical_url,
        "title": title,
        "sanitized_summary": summary,
        "published_at": published_at,
        "license_or_terms_note": None,
        "source_trust": "official",
        "risk_flags": risk_flags,
        "quarantined": bool(set(risk_flags) & _QUARANTINE_FLAGS),
        "raw_hash": metadata["body_hash"],
        "sanitizer_version": SANITIZER_VERSION,
    }


def _rss_clean_records(metadata: dict[str, Any], body: bytes) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise ValueError("rss raw body must be valid XML") from exc

    items = _rss_items(root)
    if not items:
        raise ValueError("rss raw body must include at least one item")

    return [_rss_item_clean_record(metadata, item) for item in items]


def _rss_item_clean_record(
    metadata: dict[str, Any], item: ElementTree.Element
) -> dict[str, Any]:
    canonical_url = _clean_text(_rss_text(item, "link") or _rss_text(item, "guid"))
    if not canonical_url:
        raise ValueError("rss item must include link or guid")

    title = _clean_text(_rss_text(item, "title") or canonical_url)
    summary = _cap_length(
        _clean_text(_rss_text(item, "description") or _rss_text(item, "summary"))
    )
    published_at = _optional_text(_rss_text(item, "pubDate"))
    risk_flags = _risk_flags(" ".join([title, summary]))

    return {
        "record_id": _record_id("rss", canonical_url),
        "source_id": metadata["source_id"],
        "source_type": "rss",
        "canonical_url": canonical_url,
        "title": title,
        "sanitized_summary": summary,
        "published_at": published_at,
        "license_or_terms_note": None,
        "source_trust": metadata.get("source_trust") or "secondary",
        "risk_flags": risk_flags,
        "quarantined": bool(set(risk_flags) & _QUARANTINE_FLAGS),
        "raw_hash": metadata["body_hash"],
        "sanitizer_version": SANITIZER_VERSION,
    }


def _rss_items(root: ElementTree.Element) -> list[ElementTree.Element]:
    items = root.findall("./channel/item")
    return items or root.findall(".//item")


def _rss_text(item: ElementTree.Element, name: str) -> str:
    node = item.find(name)
    if node is None:
        return ""
    return "".join(node.itertext())


def _atom_entries(root: ElementTree.Element) -> list[ElementTree.Element]:
    entries = root.findall("atom:entry", _ATOM_NAMESPACE)
    return entries or root.findall("entry")


def _atom_text(entry: ElementTree.Element, name: str) -> str:
    node = entry.find(f"atom:{name}", _ATOM_NAMESPACE)
    if node is None:
        node = entry.find(name)
    if node is None:
        return ""
    return "".join(node.itertext())


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
