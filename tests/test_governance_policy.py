import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.governance import (  # noqa: E402
    evaluate_tool_intent,
    validate_governance_decision,
    validate_tool_intent,
)


class GovernancePolicyTests(unittest.TestCase):
    def test_read_only_intent_is_allowed(self):
        decision = evaluate_tool_intent(
            _tool_intent(action_class="read_only", dry_run_supported=False)
        )

        self.assertEqual(decision["schema_version"], "governance-decision.v1")
        self.assertEqual(decision["intent_id"], "intent-1")
        self.assertEqual(decision["profile_id"], "code-intel-kernel")
        self.assertEqual(decision["action_class"], "read_only")
        self.assertEqual(decision["tool_name"], "inspect-record")
        self.assertEqual(decision["decision"], "allowed")
        self.assertEqual(
            decision["reason"], "read_only actions are allowed by default policy"
        )
        self.assertEqual(decision["evidence_refs"], ["clean/github_repo-good.json"])

    def test_edit_local_intent_is_gated(self):
        decision = evaluate_tool_intent(
            _tool_intent(action_class="edit_local", dry_run_supported=True)
        )

        self.assertEqual(decision["decision"], "gated")
        self.assertEqual(
            decision["reason"], "edit_local actions require explicit approval"
        )
        self.assertTrue(decision["dry_run_supported"])

    def test_side_effect_intents_are_denied_by_default(self):
        for action_class in [
            "destructive_local",
            "external_side_effect",
            "credentialed_remote",
        ]:
            with self.subTest(action_class=action_class):
                decision = evaluate_tool_intent(
                    _tool_intent(action_class=action_class, dry_run_supported=True)
                )

                self.assertEqual(decision["decision"], "denied")
                self.assertEqual(
                    decision["reason"],
                    f"{action_class} actions are denied by default policy",
                )

    def test_unknown_action_class_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tool_intent(
                _tool_intent(action_class="unknown", dry_run_supported=False)
            )

    def test_tool_intent_validation_rejects_contract_drift(self):
        valid = _tool_intent(action_class="read_only", dry_run_supported=False)
        validate_tool_intent(valid)

        missing_required = dict(valid)
        del missing_required["intent_id"]
        with self.assertRaises(ValueError):
            validate_tool_intent(missing_required)

        unknown_field = dict(valid)
        unknown_field["schema_version"] = "tool-intent.v1"
        with self.assertRaises(ValueError):
            validate_tool_intent(unknown_field)

        bad_dry_run = dict(valid)
        bad_dry_run["dry_run_supported"] = "false"
        with self.assertRaises(ValueError):
            validate_tool_intent(bad_dry_run)

        bad_arguments = dict(valid)
        bad_arguments["arguments"] = []
        with self.assertRaises(ValueError):
            validate_tool_intent(bad_arguments)

        bad_evidence_refs = dict(valid)
        bad_evidence_refs["evidence_refs"] = [123]
        with self.assertRaises(ValueError):
            validate_tool_intent(bad_evidence_refs)

    def test_evaluate_tool_intent_validates_input_before_policy(self):
        invalid = _tool_intent(action_class="read_only", dry_run_supported=False)
        del invalid["dry_run_supported"]

        with self.assertRaisesRegex(ValueError, "missing required field"):
            evaluate_tool_intent(invalid)

    def test_governance_decision_validation_rejects_contract_drift(self):
        decision = evaluate_tool_intent(
            _tool_intent(action_class="read_only", dry_run_supported=False)
        )
        validate_governance_decision(decision)

        missing_required = dict(decision)
        del missing_required["reason"]
        with self.assertRaises(ValueError):
            validate_governance_decision(missing_required)

        unknown_field = dict(decision)
        unknown_field["arguments"] = {}
        with self.assertRaises(ValueError):
            validate_governance_decision(unknown_field)

        bad_schema = dict(decision)
        bad_schema["schema_version"] = "governance-decision.v0"
        with self.assertRaises(ValueError):
            validate_governance_decision(bad_schema)

        bad_decision = dict(decision)
        bad_decision["decision"] = "approved"
        with self.assertRaises(ValueError):
            validate_governance_decision(bad_decision)

        bad_audit_event = dict(decision)
        bad_audit_event["audit_event"] = {
            "schema_version": "governance-audit-event.v1",
            "run_id": "20260529T123045Z-deadbeef",
            "event_type": "tool_intent_evaluated",
            "recorded_at": "not-a-date-time",
            "intent_id": decision["intent_id"],
            "profile_id": decision["profile_id"],
            "action_class": decision["action_class"],
            "tool_name": decision["tool_name"],
            "decision": decision["decision"],
            "reason": decision["reason"],
            "dry_run_supported": decision["dry_run_supported"],
            "evidence_refs": decision["evidence_refs"],
            "tool_intent_path": "intents/intent-1.json",
        }
        with self.assertRaisesRegex(
            ValueError, "recorded_at must be a date-time string"
        ):
            validate_governance_decision(bad_audit_event)

        unsafe_audit_run_id = dict(decision)
        unsafe_audit_run_id["audit_event"] = dict(bad_audit_event["audit_event"])
        unsafe_audit_run_id["audit_event"]["recorded_at"] = "2026-05-29T12:30:45Z"
        unsafe_audit_run_id["audit_event"]["run_id"] = "../20260529T123045Z-deadbeef"
        with self.assertRaisesRegex(ValueError, "run_id must be a safe path segment"):
            validate_governance_decision(unsafe_audit_run_id)


def _tool_intent(*, action_class, dry_run_supported):
    return {
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": action_class,
        "tool_name": "inspect-record",
        "arguments": {"record_id": "github_repo-good"},
        "dry_run_supported": dry_run_supported,
        "justification": "Inspect one clean record.",
        "evidence_refs": ["clean/github_repo-good.json"],
    }
