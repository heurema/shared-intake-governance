"""Deterministic file paths for the local runtime cache."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUNTIME_ROOT = Path.home() / ".local" / "share" / "shared-intake-governance"
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")


def generate_run_id(now: datetime | None = None, *, token: str | None = None) -> str:
    """Return a timestamped run id with injectable entropy for tests."""
    timestamp = _coerce_datetime(now or datetime.now(timezone.utc))
    suffix = _safe_segment(token or secrets.token_hex(4), "run token")
    return f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{suffix}"


class RuntimePaths:
    """Path builder for runtime artifacts kept outside the repository."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else DEFAULT_RUNTIME_ROOT

    @property
    def raw_root(self) -> Path:
        return self.root / "raw"

    @property
    def clean_root(self) -> Path:
        return self.root / "clean"

    @property
    def runs_root(self) -> Path:
        return self.root / "runs"

    @property
    def source_health_root(self) -> Path:
        return self.root / "source-health"

    @property
    def audit_root(self) -> Path:
        return self.root / "audit"

    @property
    def approvals_root(self) -> Path:
        return self.root / "approvals"

    @property
    def dry_runs_root(self) -> Path:
        return self.root / "dry-runs"

    @property
    def mediation_root(self) -> Path:
        return self.root / "mediation"

    @property
    def provider_requests_root(self) -> Path:
        return self.root / "provider-requests"

    @property
    def provider_results_root(self) -> Path:
        return self.root / "provider-results"

    @property
    def profiles_root(self) -> Path:
        return self.root / "profiles"

    def raw_body_path(
        self, source_id: str, fetched_at: str | datetime, body_hash: str
    ) -> Path:
        return self._raw_day_dir(source_id, fetched_at) / f"{_sha256(body_hash)}.body"

    def raw_metadata_path(
        self, source_id: str, fetched_at: str | datetime, body_hash: str
    ) -> Path:
        return self._raw_day_dir(source_id, fetched_at) / f"{_sha256(body_hash)}.meta.json"

    def raw_failure_metadata_path(
        self, source_id: str, fetched_at: str | datetime, failure_id: str
    ) -> Path:
        failure_segment = _safe_segment(failure_id, "failure_id")
        return self._raw_day_dir(source_id, fetched_at) / f"failed-{failure_segment}.meta.json"

    def clean_record_path(self, record_id: str) -> Path:
        return self.clean_root / f"{_safe_segment(record_id, 'record_id')}.json"

    def run_manifest_path(self, run_id: str) -> Path:
        return self.runs_root / f"{_safe_segment(run_id, 'run_id')}.manifest.json"

    def audit_log_path(self, run_id: str) -> Path:
        return self.audit_root / f"{_safe_segment(run_id, 'run_id')}.jsonl"

    def approval_record_path(self, run_id: str, approval_id: str) -> Path:
        return (
            self.approvals_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(approval_id, 'approval_id')}.json"
        )

    def dry_run_result_path(self, run_id: str, dry_run_id: str) -> Path:
        return (
            self.dry_runs_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(dry_run_id, 'dry_run_id')}.json"
        )

    def mediation_record_path(self, run_id: str, mediation_id: str) -> Path:
        return (
            self.mediation_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(mediation_id, 'mediation_id')}.json"
        )

    def provider_request_path(self, run_id: str, request_id: str) -> Path:
        return (
            self.provider_requests_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(request_id, 'request_id')}.json"
        )

    def provider_result_path(self, run_id: str, result_id: str) -> Path:
        return (
            self.provider_results_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(result_id, 'result_id')}.json"
        )

    def provider_result_artifact_path(
        self, run_id: str, result_id: str, artifact_id: str
    ) -> Path:
        return (
            self.provider_results_root
            / _safe_segment(run_id, "run_id")
            / (
                f"{_safe_segment(result_id, 'result_id')}."
                f"{_safe_segment(artifact_id, 'artifact_id')}"
            )
        )

    def source_health_path(self, run_id: str, source_id: str) -> Path:
        return (
            self.source_health_root
            / _safe_segment(run_id, "run_id")
            / f"{_safe_segment(source_id, 'source_id')}.json"
        )

    def profile_state_dir(self, profile_id: str) -> Path:
        return self.profiles_root / _safe_segment(profile_id, "profile_id") / "state"

    def profile_state_path(self, profile_id: str, state_id: str) -> Path:
        return (
            self.profile_state_dir(profile_id)
            / f"{_safe_segment(state_id, 'state_id')}.json"
        )

    def profile_reports_dir(self, profile_id: str) -> Path:
        return self.profiles_root / _safe_segment(profile_id, "profile_id") / "reports"

    def profile_report_path(self, profile_id: str, output_id: str) -> Path:
        return (
            self.profile_reports_dir(profile_id)
            / f"{_safe_segment(output_id, 'output_id')}.json"
        )

    def _raw_day_dir(self, source_id: str, fetched_at: str | datetime) -> Path:
        date_part = _coerce_datetime(fetched_at).date().isoformat()
        return self.raw_root / _safe_segment(source_id, "source_id") / date_part


def _coerce_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value


def _sha256(value: str) -> str:
    if not _SHA256_HEX.fullmatch(value):
        raise ValueError("body_hash must be a lowercase sha256 hex digest")
    return value
