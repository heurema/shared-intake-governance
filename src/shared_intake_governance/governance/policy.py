"""Default policy evaluator for tool-intent.v1 artifacts."""

from __future__ import annotations

from typing import Any

from shared_intake_governance.validation import require_date_time


_POLICY: dict[str, tuple[str, str]] = {
    "read_only": ("allowed", "read_only actions are allowed by default policy"),
    "edit_local": ("gated", "edit_local actions require explicit approval"),
    "destructive_local": (
        "denied",
        "destructive_local actions are denied by default policy",
    ),
    "external_side_effect": (
        "denied",
        "external_side_effect actions are denied by default policy",
    ),
    "credentialed_remote": (
        "denied",
        "credentialed_remote actions are denied by default policy",
    ),
}
_ACTION_CLASSES = set(_POLICY)
_GOVERNANCE_DECISIONS = {"allowed", "gated", "denied"}
_TOOL_INTENT_REQUIRED = {
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "arguments",
    "dry_run_supported",
    "justification",
    "evidence_refs",
}
_GOVERNANCE_DECISION_REQUIRED = {
    "schema_version",
    "intent_id",
    "profile_id",
    "action_class",
    "tool_name",
    "decision",
    "reason",
    "dry_run_supported",
    "evidence_refs",
}
_GOVERNANCE_DECISION_OPTIONAL = {
    "tool_intent_path",
    "audit_log_path",
    "audit_event",
}
_GOVERNANCE_DECISION_ALLOWED = (
    _GOVERNANCE_DECISION_REQUIRED | _GOVERNANCE_DECISION_OPTIONAL
)
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


def evaluate_tool_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return a governance decision without executing the requested tool."""
    validate_tool_intent(intent)
    action_class = intent["action_class"]
    if action_class not in _POLICY:
        raise ValueError(f"unsupported action_class: {action_class}")

    decision, reason = _POLICY[action_class]
    result = {
        "schema_version": "governance-decision.v1",
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": action_class,
        "tool_name": intent["tool_name"],
        "decision": decision,
        "reason": reason,
        "dry_run_supported": intent["dry_run_supported"],
        "evidence_refs": intent["evidence_refs"],
    }
    validate_governance_decision(result)
    return result


def validate_tool_intent(intent: dict[str, Any]) -> None:
    """Validate a tool-intent.v1 payload against the Phase 1 contract."""
    missing = sorted(_TOOL_INTENT_REQUIRED - set(intent))
    if missing:
        raise ValueError("tool intent missing required fields: " + ", ".join(missing))
    extra = sorted(set(intent) - _TOOL_INTENT_REQUIRED)
    if extra:
        raise ValueError("tool intent has unknown fields: " + ", ".join(extra))

    for field in ["intent_id", "profile_id", "tool_name", "justification"]:
        _require_text(intent, field)
    if intent["action_class"] not in _ACTION_CLASSES:
        raise ValueError("tool intent has unsupported action_class")
    if not isinstance(intent["arguments"], dict):
        raise ValueError("tool intent arguments must be an object")
    if not isinstance(intent["dry_run_supported"], bool):
        raise ValueError("tool intent dry_run_supported must be boolean")
    _require_string_array(intent, "evidence_refs", "tool intent evidence_refs")


def validate_governance_decision(decision: dict[str, Any]) -> None:
    """Validate a governance-decision.v1 payload."""
    missing = sorted(_GOVERNANCE_DECISION_REQUIRED - set(decision))
    if missing:
        raise ValueError(
            "governance decision missing required fields: " + ", ".join(missing)
        )
    extra = sorted(set(decision) - _GOVERNANCE_DECISION_ALLOWED)
    if extra:
        raise ValueError("governance decision has unknown fields: " + ", ".join(extra))

    if decision["schema_version"] != "governance-decision.v1":
        raise ValueError("governance decision must use governance-decision.v1")
    for field in ["intent_id", "profile_id", "tool_name", "reason"]:
        _require_text(decision, field)
    if decision["action_class"] not in _ACTION_CLASSES:
        raise ValueError("governance decision has unsupported action_class")
    if decision["decision"] not in _GOVERNANCE_DECISIONS:
        raise ValueError("governance decision has unsupported decision")
    if not isinstance(decision["dry_run_supported"], bool):
        raise ValueError("governance decision dry_run_supported must be boolean")
    _require_string_array(
        decision,
        "evidence_refs",
        "governance decision evidence_refs",
    )
    for field in ["tool_intent_path", "audit_log_path"]:
        if field in decision:
            _require_text(decision, field)
    if "audit_event" in decision:
        _validate_governance_audit_event(decision["audit_event"])


def _validate_governance_audit_event(event: Any) -> None:
    if not isinstance(event, dict):
        raise ValueError("governance decision audit_event must be an object")
    missing = sorted(_GOVERNANCE_AUDIT_REQUIRED - set(event))
    if missing:
        raise ValueError(
            "governance decision audit_event missing required fields: "
            + ", ".join(missing)
        )
    extra = sorted(set(event) - _GOVERNANCE_AUDIT_REQUIRED)
    if extra:
        raise ValueError(
            "governance decision audit_event has unknown fields: "
            + ", ".join(extra)
        )

    if event["schema_version"] != "governance-audit-event.v1":
        raise ValueError("governance decision audit_event has unsupported schema")
    if event["event_type"] != "tool_intent_evaluated":
        raise ValueError("governance decision audit_event has unsupported event_type")
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
    require_date_time(event["recorded_at"], "recorded_at")
    if event["action_class"] not in _ACTION_CLASSES:
        raise ValueError("governance decision audit_event has unsupported action_class")
    if event["decision"] not in _GOVERNANCE_DECISIONS:
        raise ValueError("governance decision audit_event has unsupported decision")
    if not isinstance(event["dry_run_supported"], bool):
        raise ValueError(
            "governance decision audit_event dry_run_supported must be boolean"
        )
    _require_string_array(
        event,
        "evidence_refs",
        "governance decision audit_event evidence_refs",
    )


def _require_text(payload: dict[str, Any], field: str) -> None:
    if not isinstance(payload[field], str) or not payload[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _require_string_array(payload: dict[str, Any], field: str, label: str) -> None:
    if not isinstance(payload[field], list) or not all(
        isinstance(item, str) for item in payload[field]
    ):
        raise ValueError(f"{label} must be strings")
