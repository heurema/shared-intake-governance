"""Writers for immutable raw evidence and operational artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import RuntimePaths


_BODY_HASH = re.compile(r"^[a-f0-9]{64}$")
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
_RAW_FETCH_STATUS = {"success", "degraded", "failed"}
_RAW_METADATA_REQUIRED = {
    "schema_version",
    "run_id",
    "source_id",
    "source_type",
    "fetch_status",
    "fetched_at",
    "request_url",
    "canonical_url",
    "http_status",
    "etag",
    "last_modified",
    "content_type",
    "body_hash",
    "storage_path",
    "collector_version",
    "error",
}
_RAW_METADATA_OPTIONAL = {"source_trust"}
_RAW_METADATA_ALLOWED = _RAW_METADATA_REQUIRED | _RAW_METADATA_OPTIONAL
_RUN_MANIFEST_MODE = {"backfill", "daily_collection", "shadow", "governance"}
_RUN_MANIFEST_STATUS = {
    "started",
    "completed",
    "completed_with_degradation",
    "failed",
}
_RUN_MANIFEST_REQUIRED = {
    "schema_version",
    "run_id",
    "mode",
    "status",
    "started_at",
    "finished_at",
    "runtime_root",
    "raw_root",
    "clean_root",
    "profiles_root",
    "sources",
    "counts",
    "source_health",
}
_RUN_MANIFEST_COUNT_REQUIRED = {
    "raw_payloads_written",
    "raw_metadata_written",
    "clean_records_written",
    "projected_profiles",
    "quarantined_records",
    "failed_sources",
}
_SOURCE_HEALTH_STATUS = {"healthy", "degraded", "failed", "skipped"}
_ACTION_CLASSES = {
    "read_only",
    "edit_local",
    "destructive_local",
    "external_side_effect",
    "credentialed_remote",
}
_GOVERNANCE_DECISIONS = {"allowed", "gated", "denied"}
_GOVERNANCE_AUDIT_REQUIRED = {
    "schema_version",
    "run_id",
    "event_type",
    "recorded_at",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "decision",
    "reason",
    "dry_run_supported",
    "evidence_refs",
    "tool_intent_path",
}
_APPROVAL_DECISIONS = {"approved", "rejected"}
_APPROVAL_RECORD_REQUIRED = {
    "schema_version",
    "run_id",
    "approval_id",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "approval_decision",
    "approved_by",
    "approved_at",
    "justification",
    "dry_run_ref",
    "evidence_refs",
    "tool_intent_path",
}
_DRY_RUN_KINDS = {
    "disposable_worktree",
    "sandboxed_container",
    "read_only_simulation",
    "test_only_execution",
    "custom",
}
_DRY_RUN_RESULT_STATUS = {"passed", "failed", "blocked"}
_DRY_RUN_RESULT_REQUIRED = {
    "schema_version",
    "run_id",
    "dry_run_id",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "dry_run_kind",
    "result_status",
    "recorded_by",
    "recorded_at",
    "summary",
    "artifact_refs",
    "evidence_refs",
    "tool_intent_path",
}
_MEDIATION_DECISIONS = {"ready", "blocked"}
_EXECUTION_MEDIATION_REQUIRED = {
    "schema_version",
    "run_id",
    "mediation_id",
    "mediated_at",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "policy_decision",
    "mediation_decision",
    "reason",
    "dry_run_result_path",
    "approval_record_path",
    "tool_intent_path",
    "evidence_refs",
}
_TOOL_EXECUTION_STATUS = {"succeeded", "failed", "blocked"}
_TOOL_EXECUTION_RESULT_REQUIRED = {
    "schema_version",
    "run_id",
    "execution_id",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "executed_by",
    "executed_at",
    "execution_status",
    "summary",
    "tool_intent_path",
    "mediation_record_path",
    "output_refs",
    "execution_metadata",
    "error",
    "evidence_refs",
}
_PROVIDERS = {"claude", "gemini", "vibe"}
_PROVIDER_REQUEST_REQUIRED = {
    "schema_version",
    "run_id",
    "request_id",
    "prepared_at",
    "provider",
    "mediation_record_path",
    "mediation_id",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "policy_decision",
    "mediation_decision",
    "capabilities",
    "context_refs",
    "evidence_refs",
}
_SOURCE_HEALTH_REQUIRED = {
    "schema_version",
    "run_id",
    "source_id",
    "source_type",
    "status",
    "checked_at",
    "attempted_fetches",
    "successful_fetches",
    "failed_fetches",
    "raw_records_written",
    "degraded_reasons",
    "last_error",
    "next_retry_after",
}


@dataclass(frozen=True)
class RawBodyWrite:
    body_hash: str
    path: Path


class RawWriter:
    """Write raw payload bodies and metadata before source collectors exist."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_body(
        self,
        source_id: str,
        fetched_at: str | datetime,
        body: bytes | bytearray | memoryview,
    ) -> RawBodyWrite:
        payload = bytes(body)
        body_hash = hashlib.sha256(payload).hexdigest()
        path = self.paths.raw_body_path(source_id, fetched_at, body_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return RawBodyWrite(body_hash=body_hash, path=path)

    def write_metadata(
        self, metadata: dict[str, Any], *, failure_id: str | None = None
    ) -> Path:
        validate_raw_metadata(metadata)
        source_id = str(metadata["source_id"])
        fetched_at = str(metadata["fetched_at"])
        body_hash = metadata.get("body_hash")

        if body_hash is None:
            if failure_id is None:
                failure_id = str(metadata["run_id"])
            path = self.paths.raw_failure_metadata_path(source_id, fetched_at, failure_id)
        else:
            path = self.paths.raw_metadata_path(source_id, fetched_at, str(body_hash))

        return _write_json(path, metadata)


class RunWriter:
    """Write run manifests as stable JSON artifacts."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_manifest(self, manifest: dict[str, Any]) -> Path:
        validate_run_manifest(manifest)
        path = self.paths.run_manifest_path(str(manifest["run_id"]))
        return _write_json(path, manifest)


class SourceHealthWriter:
    """Write one source-health artifact for a run/source pair."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_source_health(self, source_health: dict[str, Any]) -> Path:
        validate_source_health(source_health)
        path = self.paths.source_health_path(
            str(source_health["run_id"]), str(source_health["source_id"])
        )
        return _write_json(path, source_health)


class AuditWriter:
    """Append governance audit events as JSONL."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_event(self, event: dict[str, Any]) -> Path:
        validate_governance_audit_event(event)
        path = self.paths.audit_log_path(str(event["run_id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n"
            )
        return path


class ApprovalWriter:
    """Write one explicit local approval record."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_record(self, record: dict[str, Any]) -> Path:
        validate_approval_record(record)
        path = self.paths.approval_record_path(
            str(record["run_id"]), str(record["approval_id"])
        )
        return _write_json(path, record)


class DryRunWriter:
    """Write one recorded dry-run result."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_result(self, result: dict[str, Any]) -> Path:
        validate_dry_run_result(result)
        path = self.paths.dry_run_result_path(
            str(result["run_id"]), str(result["dry_run_id"])
        )
        return _write_json(path, result)


class MediationWriter:
    """Write one pre-execution mediation record."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_record(self, record: dict[str, Any]) -> Path:
        validate_execution_mediation(record)
        path = self.paths.mediation_record_path(
            str(record["run_id"]), str(record["mediation_id"])
        )
        return _write_json(path, record)


class ToolExecutionWriter:
    """Write one governed tool execution result."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_result(self, result: dict[str, Any]) -> Path:
        validate_tool_execution_result(result)
        path = self.paths.tool_execution_result_path(
            str(result["run_id"]), str(result["execution_id"])
        )
        return _write_json(path, result)


class ProviderRequestWriter:
    """Write one provider-neutral adapter request."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_request(self, request: dict[str, Any]) -> Path:
        validate_provider_request(request)
        path = self.paths.provider_request_path(
            str(request["run_id"]), str(request["request_id"])
        )
        return _write_json(path, request)


class ProviderResultWriter:
    """Write one provider result record."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_result(self, result: dict[str, Any]) -> Path:
        path = self.paths.provider_result_path(
            str(result["run_id"]), str(result["result_id"])
        )
        return _write_json(path, result)


def validate_governance_audit_event(event: dict[str, Any]) -> None:
    missing = sorted(_GOVERNANCE_AUDIT_REQUIRED - set(event))
    if missing:
        raise ValueError(
            "governance audit event missing required fields: "
            + ", ".join(missing)
        )
    extra = sorted(set(event) - _GOVERNANCE_AUDIT_REQUIRED)
    if extra:
        raise ValueError(
            "governance audit event has unknown fields: " + ", ".join(extra)
        )

    if event["schema_version"] != "governance-audit-event.v1":
        raise ValueError("governance audit event must use governance-audit-event.v1")
    if event["event_type"] != "tool_intent_evaluated":
        raise ValueError("governance audit event has unsupported event_type")
    for field in [
        "run_id",
        "recorded_at",
        "intent_id",
        "profile_id",
        "tool_name",
        "reason",
        "tool_intent_path",
    ]:
        _require_text(event, field)
    if event["action_class"] not in _ACTION_CLASSES:
        raise ValueError("governance audit event has unsupported action_class")
    if event["decision"] not in _GOVERNANCE_DECISIONS:
        raise ValueError("governance audit event has unsupported decision")
    if not isinstance(event["dry_run_supported"], bool):
        raise ValueError("governance audit event dry_run_supported must be boolean")
    _require_string_array(
        event,
        "evidence_refs",
        "governance audit event evidence_refs",
    )


def validate_approval_record(record: dict[str, Any]) -> None:
    missing = sorted(_APPROVAL_RECORD_REQUIRED - set(record))
    if missing:
        raise ValueError(
            "approval record missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(record) - _APPROVAL_RECORD_REQUIRED)
    if extra:
        raise ValueError("approval record has unknown fields: " + ", ".join(extra))

    if record["schema_version"] != "approval-record.v1":
        raise ValueError("approval record must use approval-record.v1")
    for field in [
        "run_id",
        "approval_id",
        "intent_id",
        "profile_id",
        "tool_name",
        "approved_by",
        "approved_at",
        "justification",
        "tool_intent_path",
    ]:
        _require_text(record, field)
    if record["action_class"] not in _ACTION_CLASSES:
        raise ValueError("approval record has unsupported action_class")
    if record["approval_decision"] not in _APPROVAL_DECISIONS:
        raise ValueError("approval record has unsupported approval_decision")
    _require_optional_string(record, "dry_run_ref", "approval record dry_run_ref")
    _require_string_array(
        record,
        "evidence_refs",
        "approval record evidence_refs",
    )


def validate_dry_run_result(result: dict[str, Any]) -> None:
    missing = sorted(_DRY_RUN_RESULT_REQUIRED - set(result))
    if missing:
        raise ValueError(
            "dry-run result missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(result) - _DRY_RUN_RESULT_REQUIRED)
    if extra:
        raise ValueError("dry-run result has unknown fields: " + ", ".join(extra))

    if result["schema_version"] != "dry-run-result.v1":
        raise ValueError("dry-run result must use dry-run-result.v1")
    for field in [
        "run_id",
        "dry_run_id",
        "intent_id",
        "profile_id",
        "tool_name",
        "recorded_by",
        "recorded_at",
        "summary",
        "tool_intent_path",
    ]:
        _require_text(result, field)
    if result["action_class"] not in _ACTION_CLASSES:
        raise ValueError("dry-run result has unsupported action_class")
    if result["dry_run_kind"] not in _DRY_RUN_KINDS:
        raise ValueError("dry-run result has unsupported dry_run_kind")
    if result["result_status"] not in _DRY_RUN_RESULT_STATUS:
        raise ValueError("dry-run result has unsupported result_status")
    _require_string_array(
        result,
        "artifact_refs",
        "dry-run result artifact_refs",
    )
    _require_string_array(
        result,
        "evidence_refs",
        "dry-run result evidence_refs",
    )


def validate_execution_mediation(record: dict[str, Any]) -> None:
    missing = sorted(_EXECUTION_MEDIATION_REQUIRED - set(record))
    if missing:
        raise ValueError(
            "execution mediation missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(record) - _EXECUTION_MEDIATION_REQUIRED)
    if extra:
        raise ValueError(
            "execution mediation has unknown fields: " + ", ".join(extra)
        )

    if record["schema_version"] != "execution-mediation.v1":
        raise ValueError("execution mediation must use execution-mediation.v1")
    for field in [
        "run_id",
        "mediation_id",
        "mediated_at",
        "intent_id",
        "profile_id",
        "tool_name",
        "reason",
        "tool_intent_path",
    ]:
        _require_text(record, field)
    if record["action_class"] not in _ACTION_CLASSES:
        raise ValueError("execution mediation has unsupported action_class")
    if record["policy_decision"] not in _GOVERNANCE_DECISIONS:
        raise ValueError("execution mediation has unsupported policy_decision")
    if record["mediation_decision"] not in _MEDIATION_DECISIONS:
        raise ValueError("execution mediation has unsupported mediation_decision")
    _require_optional_string(
        record,
        "dry_run_result_path",
        "execution mediation dry_run_result_path",
    )
    _require_optional_string(
        record,
        "approval_record_path",
        "execution mediation approval_record_path",
    )
    _require_string_array(
        record,
        "evidence_refs",
        "execution mediation evidence_refs",
    )


def validate_tool_execution_result(result: dict[str, Any]) -> None:
    missing = sorted(_TOOL_EXECUTION_RESULT_REQUIRED - set(result))
    if missing:
        raise ValueError(
            "tool execution result missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(result) - _TOOL_EXECUTION_RESULT_REQUIRED)
    if extra:
        raise ValueError(
            "tool execution result has unknown fields: " + ", ".join(extra)
        )

    if result["schema_version"] != "tool-execution-result.v1":
        raise ValueError("tool execution result must use tool-execution-result.v1")
    for field in [
        "run_id",
        "execution_id",
        "intent_id",
        "profile_id",
        "tool_name",
        "executed_by",
        "executed_at",
        "summary",
        "tool_intent_path",
        "mediation_record_path",
    ]:
        _require_text(result, field)
    if result["action_class"] not in _ACTION_CLASSES:
        raise ValueError("tool execution result has unsupported action_class")
    if result["execution_status"] not in _TOOL_EXECUTION_STATUS:
        raise ValueError("tool execution result has unsupported execution_status")
    _require_string_array(
        result,
        "output_refs",
        "tool execution result output_refs",
    )
    _require_string_object(
        result,
        "execution_metadata",
        "tool execution result execution_metadata",
    )
    if result["error"] is not None:
        _validate_error_object(
            result["error"],
            "tool execution result error",
            allow_retryable=False,
        )
    _require_string_array(
        result,
        "evidence_refs",
        "tool execution result evidence_refs",
    )


def validate_provider_request(request: dict[str, Any]) -> None:
    missing = sorted(_PROVIDER_REQUEST_REQUIRED - set(request))
    if missing:
        raise ValueError(
            "provider request missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(request) - _PROVIDER_REQUEST_REQUIRED)
    if extra:
        raise ValueError("provider request has unknown fields: " + ", ".join(extra))

    if request["schema_version"] != "provider-request.v1":
        raise ValueError("provider request must use provider-request.v1")
    for field in [
        "run_id",
        "request_id",
        "prepared_at",
        "mediation_record_path",
        "mediation_id",
        "intent_id",
        "profile_id",
        "tool_name",
    ]:
        _require_text(request, field)
    if request["provider"] not in _PROVIDERS:
        raise ValueError("provider request has unsupported provider")
    if request["action_class"] not in _ACTION_CLASSES:
        raise ValueError("provider request has unsupported action_class")
    if request["policy_decision"] not in _GOVERNANCE_DECISIONS:
        raise ValueError("provider request has unsupported policy_decision")
    if request["mediation_decision"] != "ready":
        raise ValueError("provider request must use ready mediation")
    _require_enum_array(
        request,
        "capabilities",
        _ACTION_CLASSES,
        "provider request capabilities",
    )
    _require_string_array(
        request,
        "context_refs",
        "provider request context_refs",
    )
    _require_string_array(
        request,
        "evidence_refs",
        "provider request evidence_refs",
    )


def validate_raw_metadata(metadata: dict[str, Any]) -> None:
    missing = sorted(_RAW_METADATA_REQUIRED - set(metadata))
    if missing:
        raise ValueError(f"raw metadata missing required fields: {', '.join(missing)}")
    extra = sorted(set(metadata) - _RAW_METADATA_ALLOWED)
    if extra:
        raise ValueError(f"raw metadata has unknown fields: {', '.join(extra)}")

    if metadata["schema_version"] != "raw-metadata.v1":
        raise ValueError("raw metadata must use raw-metadata.v1")
    for field in [
        "run_id",
        "source_id",
        "fetched_at",
        "request_url",
        "collector_version",
    ]:
        _require_text(metadata, field)
    if metadata["source_type"] not in _SOURCE_TYPES:
        raise ValueError("raw metadata has unsupported source_type")
    if metadata["fetch_status"] not in _RAW_FETCH_STATUS:
        raise ValueError("raw metadata has unsupported fetch_status")
    if metadata["canonical_url"] is not None:
        _require_text(metadata, "canonical_url")
    if metadata["http_status"] is not None:
        if not isinstance(metadata["http_status"], int) or not (
            100 <= metadata["http_status"] <= 599
        ):
            raise ValueError("raw metadata http_status must be an HTTP status")
    for field in ["etag", "last_modified", "content_type", "storage_path"]:
        if metadata[field] is not None:
            _require_text(metadata, field)
    if metadata["body_hash"] is not None:
        if not isinstance(metadata["body_hash"], str) or not _BODY_HASH.fullmatch(
            metadata["body_hash"]
        ):
            raise ValueError("raw metadata body_hash must be a sha256 hex digest")
    if "source_trust" in metadata and metadata["source_trust"] not in _SOURCE_TRUST:
        raise ValueError("raw metadata has unsupported source_trust")
    if metadata["error"] is not None:
        _validate_error_object(metadata["error"], "raw metadata error")


def validate_run_manifest(manifest: dict[str, Any]) -> None:
    missing = sorted(_RUN_MANIFEST_REQUIRED - set(manifest))
    if missing:
        raise ValueError(f"run manifest missing required fields: {', '.join(missing)}")
    extra = sorted(set(manifest) - _RUN_MANIFEST_REQUIRED)
    if extra:
        raise ValueError(f"run manifest has unknown fields: {', '.join(extra)}")

    if manifest["schema_version"] != "run-manifest.v1":
        raise ValueError("run manifest must use run-manifest.v1")
    for field in [
        "run_id",
        "started_at",
        "runtime_root",
        "raw_root",
        "clean_root",
        "profiles_root",
    ]:
        _require_text(manifest, field)
    if manifest["mode"] not in _RUN_MANIFEST_MODE:
        raise ValueError("run manifest has unsupported mode")
    if manifest["status"] not in _RUN_MANIFEST_STATUS:
        raise ValueError("run manifest has unsupported status")
    if manifest["finished_at"] is not None:
        _require_text(manifest, "finished_at")
    _require_string_list(manifest, "sources", "run manifest sources")
    _require_string_list(
        manifest,
        "source_health",
        "run manifest source_health",
    )

    counts = manifest["counts"]
    if not isinstance(counts, dict):
        raise ValueError("run manifest counts must be an object")
    count_missing = sorted(_RUN_MANIFEST_COUNT_REQUIRED - set(counts))
    if count_missing:
        raise ValueError(
            "run manifest counts missing required fields: "
            + ", ".join(count_missing)
        )
    count_extra = sorted(set(counts) - _RUN_MANIFEST_COUNT_REQUIRED)
    if count_extra:
        raise ValueError(
            "run manifest counts has unknown fields: " + ", ".join(count_extra)
        )
    for field in sorted(_RUN_MANIFEST_COUNT_REQUIRED):
        if not isinstance(counts[field], int) or counts[field] < 0:
            raise ValueError(f"run manifest count {field} must be non-negative")


def validate_source_health(source_health: dict[str, Any]) -> None:
    missing = sorted(_SOURCE_HEALTH_REQUIRED - set(source_health))
    if missing:
        raise ValueError(f"source health missing required fields: {', '.join(missing)}")
    extra = sorted(set(source_health) - _SOURCE_HEALTH_REQUIRED)
    if extra:
        raise ValueError(f"source health has unknown fields: {', '.join(extra)}")

    if source_health["schema_version"] != "source-health.v1":
        raise ValueError("source health must use source-health.v1")
    _require_text(source_health, "run_id")
    _require_text(source_health, "source_id")
    _require_text(source_health, "checked_at")
    if source_health["source_type"] not in _SOURCE_TYPES:
        raise ValueError("source health has unsupported source_type")
    if source_health["status"] not in _SOURCE_HEALTH_STATUS:
        raise ValueError("source health has unsupported status")

    for field in [
        "attempted_fetches",
        "successful_fetches",
        "failed_fetches",
        "raw_records_written",
    ]:
        if not isinstance(source_health[field], int) or source_health[field] < 0:
            raise ValueError(f"source health {field} must be non-negative")

    degraded_reasons = source_health["degraded_reasons"]
    if not isinstance(degraded_reasons, list) or not all(
        isinstance(reason, str) and reason for reason in degraded_reasons
    ):
        raise ValueError("source health degraded_reasons must be strings")

    last_error = source_health["last_error"]
    if last_error is not None:
        _validate_error_object(last_error, "source health last_error")
    if source_health["next_retry_after"] is not None:
        _require_text(source_health, "next_retry_after")


def _validate_error_object(
    error: Any,
    label: str,
    *,
    allow_retryable: bool = True,
) -> None:
    if not isinstance(error, dict):
        raise ValueError(f"{label} must be an object")
    required = {"kind", "message"}
    allowed = required | ({"retryable"} if allow_retryable else set())
    missing = sorted(required - set(error))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")
    extra = sorted(set(error) - allowed)
    if extra:
        raise ValueError(f"{label} has unknown fields: {', '.join(extra)}")
    _require_text(error, "kind")
    _require_text(error, "message")
    if "retryable" in error and not isinstance(error["retryable"], bool):
        raise ValueError(f"{label} retryable must be boolean")


def _require_text(payload: dict[str, Any], field: str) -> None:
    if not isinstance(payload[field], str) or not payload[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _require_string_list(payload: dict[str, Any], field: str, label: str) -> None:
    if not isinstance(payload[field], list) or not all(
        isinstance(item, str) and item for item in payload[field]
    ):
        raise ValueError(f"{label} must be strings")


def _require_string_array(payload: dict[str, Any], field: str, label: str) -> None:
    if not isinstance(payload[field], list) or not all(
        isinstance(item, str) for item in payload[field]
    ):
        raise ValueError(f"{label} must be strings")


def _require_enum_array(
    payload: dict[str, Any],
    field: str,
    allowed_values: set[str],
    label: str,
) -> None:
    if not isinstance(payload[field], list) or not all(
        isinstance(item, str) and item in allowed_values for item in payload[field]
    ):
        raise ValueError(f"{label} must contain supported values")


def _require_string_object(payload: dict[str, Any], field: str, label: str) -> None:
    if not isinstance(payload[field], dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in payload[field].items()
    ):
        raise ValueError(f"{label} must be an object with string values")


def _require_optional_string(payload: dict[str, Any], field: str, label: str) -> None:
    if payload[field] is not None and not isinstance(payload[field], str):
        raise ValueError(f"{label} must be a string or null")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
