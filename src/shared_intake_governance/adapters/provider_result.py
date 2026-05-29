"""Provider result recording without provider invocation."""

from __future__ import annotations

from typing import Any

from shared_intake_governance.runtime import (
    validate_provider_request,
    validate_provider_result,
)


_RESULT_STATUSES = {"succeeded", "failed", "blocked"}


def record_provider_result(
    *,
    run_id: str,
    result_id: str,
    provider_request: dict[str, Any],
    provider_request_path: str,
    result_status: str,
    recorded_by: str,
    summary: str,
    response_refs: list[str],
    usage_metadata: dict[str, str],
    error: dict[str, str] | None,
    recorded_at: str,
) -> dict[str, Any]:
    """Return a provider result record without storing provider payloads."""
    validate_provider_request(provider_request)
    if result_status not in _RESULT_STATUSES:
        raise ValueError(f"unsupported result_status: {result_status}")
    if result_status == "succeeded" and error is not None:
        raise ValueError("succeeded provider results must not include an error")
    if result_status in {"failed", "blocked"} and error is None:
        raise ValueError("failed or blocked provider results require an error")

    result = {
        "schema_version": "provider-result.v1",
        "run_id": run_id,
        "result_id": result_id,
        "request_id": provider_request["request_id"],
        "provider": provider_request["provider"],
        "recorded_by": recorded_by,
        "recorded_at": recorded_at,
        "result_status": result_status,
        "summary": summary,
        "provider_request_path": provider_request_path,
        "mediation_id": provider_request["mediation_id"],
        "intent_id": provider_request["intent_id"],
        "profile_id": provider_request["profile_id"],
        "action_class": provider_request["action_class"],
        "tool_name": provider_request["tool_name"],
        "response_refs": response_refs,
        "usage_metadata": usage_metadata,
        "error": error,
        "evidence_refs": provider_request["evidence_refs"],
    }
    validate_provider_result(result)
    return result
