"""Pre-execution mediation for governed tool intents."""

from __future__ import annotations

from typing import Any

from shared_intake_governance.runtime import (
    validate_approval_record,
    validate_dry_run_result,
)

from .policy import evaluate_tool_intent


_SIDE_EFFECT_ACTIONS = {
    "edit_local",
    "destructive_local",
    "external_side_effect",
    "credentialed_remote",
}


def mediate_tool_intent(
    *,
    run_id: str,
    mediation_id: str,
    intent: dict[str, Any],
    tool_intent_path: str,
    dry_run_result: dict[str, Any] | None,
    dry_run_result_path: str | None,
    approval_record: dict[str, Any] | None,
    approval_record_path: str | None,
    mediated_at: str,
) -> dict[str, Any]:
    """Return a mediation record without executing the requested tool."""
    decision = evaluate_tool_intent(intent)
    if dry_run_result is not None:
        validate_dry_run_result(dry_run_result)
    if approval_record is not None:
        validate_approval_record(approval_record)
    action_class = decision["action_class"]

    mediation_decision, reason = _mediation_decision(
        intent=intent,
        policy_decision=decision["decision"],
        policy_reason=decision["reason"],
        dry_run_result=dry_run_result,
        approval_record=approval_record,
    )

    return {
        "schema_version": "execution-mediation.v1",
        "run_id": run_id,
        "mediation_id": mediation_id,
        "mediated_at": mediated_at,
        "intent_id": decision["intent_id"],
        "profile_id": decision["profile_id"],
        "action_class": action_class,
        "tool_name": decision["tool_name"],
        "policy_decision": decision["decision"],
        "mediation_decision": mediation_decision,
        "reason": reason,
        "dry_run_result_path": dry_run_result_path,
        "approval_record_path": approval_record_path,
        "tool_intent_path": tool_intent_path,
        "evidence_refs": decision["evidence_refs"],
    }


def _mediation_decision(
    *,
    intent: dict[str, Any],
    policy_decision: str,
    policy_reason: str,
    dry_run_result: dict[str, Any] | None,
    approval_record: dict[str, Any] | None,
) -> tuple[str, str]:
    if policy_decision == "denied":
        return "blocked", "denied policy decisions cannot become ready"

    action_class = str(intent["action_class"])
    if action_class == "read_only":
        return "ready", policy_reason

    if action_class not in _SIDE_EFFECT_ACTIONS:
        raise ValueError(f"unsupported action_class: {action_class}")

    if not bool(intent["dry_run_supported"]):
        return "blocked", "side-effect actions require dry_run_supported=true"
    if dry_run_result is None:
        return "blocked", "side-effect actions require a passed dry run"
    if not _same_intent_scope(intent, dry_run_result):
        return "blocked", "dry-run result does not match the tool intent scope"
    if dry_run_result.get("result_status") != "passed":
        return "blocked", "side-effect actions require a passed dry run"

    if approval_record is None:
        return "blocked", "side-effect actions require an approved approval record"
    if not _same_intent_scope(intent, approval_record):
        return "blocked", "approval record does not match the tool intent scope"
    if approval_record.get("approval_decision") != "approved":
        return "blocked", "side-effect actions require an approved approval record"

    return "ready", "side-effect action has passed dry run and approved approval record"


def _same_intent_scope(intent: dict[str, Any], record: dict[str, Any]) -> bool:
    return all(
        intent[field] == record.get(field)
        for field in ("intent_id", "profile_id", "action_class", "tool_name")
    )
