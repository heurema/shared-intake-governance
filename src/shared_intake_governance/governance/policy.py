"""Default policy evaluator for tool-intent.v1 artifacts."""

from __future__ import annotations

from typing import Any


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


def evaluate_tool_intent(intent: dict[str, Any]) -> dict[str, Any]:
    """Return a governance decision without executing the requested tool."""
    action_class = str(intent["action_class"])
    if action_class not in _POLICY:
        raise ValueError(f"unsupported action_class: {action_class}")

    decision, reason = _POLICY[action_class]
    return {
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
