import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.governance import evaluate_tool_intent  # noqa: E402


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
