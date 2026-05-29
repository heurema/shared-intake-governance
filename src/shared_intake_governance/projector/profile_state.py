"""Profile-local runtime state updates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared_intake_governance.projector.profile import validate_profile_projection
from shared_intake_governance.runtime import RuntimePaths


_PROFILE_STATE_REQUIRED = {
    "schema_version",
    "profile_id",
    "state_id",
    "state_kind",
    "updated_at",
    "record_ids",
}
_PROFILE_STATE_KINDS = {"seen_records", "cursor", "custom"}


@dataclass(frozen=True)
class ProfileStateWrite:
    state: dict[str, Any]
    path: Path


def update_seen_records_state(
    *,
    paths: RuntimePaths,
    profile_id: str,
    profile_report: dict[str, Any],
    state_id: str,
    updated_at: str,
) -> ProfileStateWrite:
    """Merge one profile report into a profile-local seen-records state."""
    validate_profile_projection(profile_report)
    if profile_report["profile_id"] != profile_id:
        raise ValueError("profile report does not match profile_id")

    path = paths.profile_state_path(profile_id, state_id)
    existing_record_ids: list[str] = []
    if path.exists():
        existing = _read_json(path)
        validate_profile_state(existing)
        if existing["profile_id"] != profile_id:
            raise ValueError("existing profile state does not match profile_id")
        if existing["state_id"] != state_id:
            raise ValueError("existing profile state does not match state_id")
        if existing["state_kind"] != "seen_records":
            raise ValueError("existing profile state must be seen_records")
        existing_record_ids = _record_ids(existing)

    report_record_ids = [
        str(item["record_id"]) for item in profile_report.get("items", [])
    ]
    state = {
        "schema_version": "profile-state.v1",
        "profile_id": profile_id,
        "state_id": state_id,
        "state_kind": "seen_records",
        "updated_at": updated_at,
        "record_ids": sorted(set(existing_record_ids) | set(report_record_ids)),
    }
    validate_profile_state(state)
    _write_json(path, state)
    return ProfileStateWrite(state=state, path=path)


def validate_profile_state(state: dict[str, Any]) -> None:
    missing = sorted(_PROFILE_STATE_REQUIRED - set(state))
    if missing:
        raise ValueError(f"profile state missing required fields: {', '.join(missing)}")
    extra = sorted(set(state) - _PROFILE_STATE_REQUIRED)
    if extra:
        raise ValueError(f"profile state has unknown fields: {', '.join(extra)}")

    if state["schema_version"] != "profile-state.v1":
        raise ValueError("profile state must use profile-state.v1")
    for field in ["profile_id", "state_id", "updated_at"]:
        _require_text(state, field)
    if state["state_kind"] not in _PROFILE_STATE_KINDS:
        raise ValueError("profile state has unsupported state_kind")
    _record_ids(state)


def _record_ids(state: dict[str, Any]) -> list[str]:
    record_ids = state["record_ids"]
    if not isinstance(record_ids, list) or not all(
        isinstance(record_id, str) and record_id for record_id in record_ids
    ):
        raise ValueError("profile state record_ids must be non-empty strings")
    return record_ids


def _require_text(payload: dict[str, Any], field: str) -> None:
    if not isinstance(payload[field], str) or not payload[field]:
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
