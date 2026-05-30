"""Provider-neutral request preparation without provider invocation."""

from __future__ import annotations

from typing import Any

from shared_intake_governance.provider_presets import resolve_provider_preset
from shared_intake_governance.runtime import (
    validate_execution_mediation,
    validate_provider_request,
)


_PROVIDER_ACTION_CLASS = "read_only"


def prepare_provider_request(
    *,
    run_id: str,
    request_id: str,
    preset_id: str,
    mediation_record: dict[str, Any],
    mediation_record_path: str,
    context_refs: list[str],
    prepared_at: str,
) -> dict[str, Any]:
    """Return a provider request record without invoking the provider."""
    validate_execution_mediation(mediation_record)
    preset = resolve_provider_preset(preset_id)
    if mediation_record["mediation_decision"] != "ready":
        raise ValueError("provider request requires ready mediation")
    if mediation_record["action_class"] != _PROVIDER_ACTION_CLASS:
        raise ValueError("provider request requires read_only mediation")

    action_class = str(mediation_record["action_class"])
    request = {
        "schema_version": "provider-request.v1",
        "run_id": run_id,
        "request_id": request_id,
        "prepared_at": prepared_at,
        "provider": preset["provider"],
        "preset_id": preset["preset_id"],
        "mediation_record_path": mediation_record_path,
        "mediation_id": mediation_record["mediation_id"],
        "intent_id": mediation_record["intent_id"],
        "profile_id": mediation_record["profile_id"],
        "action_class": action_class,
        "tool_name": mediation_record["tool_name"],
        "policy_decision": mediation_record["policy_decision"],
        "mediation_decision": mediation_record["mediation_decision"],
        "capabilities": [action_class],
        "resolved_command": preset["resolved_command"],
        "command_hash": preset["command_hash"],
        "context_refs": context_refs,
        "evidence_refs": mediation_record["evidence_refs"],
    }
    validate_provider_request(request)
    return request
