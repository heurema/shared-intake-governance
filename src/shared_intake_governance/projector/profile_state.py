"""Profile-local runtime state updates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared_intake_governance.projector.profile import validate_profile_projection
from shared_intake_governance.runtime import RuntimePaths


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
    _write_json(path, state)
    return ProfileStateWrite(state=state, path=path)


def _record_ids(state: dict[str, Any]) -> list[str]:
    record_ids = state["record_ids"]
    if not isinstance(record_ids, list) or not all(
        isinstance(record_id, str) and record_id for record_id in record_ids
    ):
        raise ValueError("profile state record_ids must be non-empty strings")
    return record_ids


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
