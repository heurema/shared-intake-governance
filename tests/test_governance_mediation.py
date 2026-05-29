import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.governance import mediate_tool_intent  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class GovernanceMediationTests(unittest.TestCase):
    def test_read_only_intent_is_ready_without_side_effect_evidence(self):
        record = mediate_tool_intent(
            run_id=RUN_ID,
            mediation_id="mediation-1",
            intent=_tool_intent(action_class="read_only", dry_run_supported=False),
            tool_intent_path="intent.json",
            dry_run_result=None,
            dry_run_result_path=None,
            approval_record=None,
            approval_record_path=None,
            mediated_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(record["schema_version"], "execution-mediation.v1")
        self.assertEqual(record["policy_decision"], "allowed")
        self.assertEqual(record["mediation_decision"], "ready")
        self.assertEqual(
            record["reason"], "read_only actions are allowed by default policy"
        )
        self.assertIsNone(record["dry_run_result_path"])
        self.assertIsNone(record["approval_record_path"])
        self.assertNotIn("arguments", record)

    def test_side_effect_intent_is_ready_with_passed_dry_run_and_approval(self):
        intent = _tool_intent(action_class="edit_local", dry_run_supported=True)
        record = mediate_tool_intent(
            run_id=RUN_ID,
            mediation_id="mediation-1",
            intent=intent,
            tool_intent_path="intent.json",
            dry_run_result=_dry_run_result(intent, result_status="passed"),
            dry_run_result_path="dry-runs/dry-run-1.json",
            approval_record=_approval_record(intent, approval_decision="approved"),
            approval_record_path="approvals/approval-1.json",
            mediated_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(record["policy_decision"], "gated")
        self.assertEqual(record["mediation_decision"], "ready")
        self.assertEqual(
            record["reason"],
            "side-effect action has passed dry run and approved approval record",
        )

    def test_side_effect_intent_blocks_without_passed_dry_run(self):
        intent = _tool_intent(action_class="edit_local", dry_run_supported=True)
        record = mediate_tool_intent(
            run_id=RUN_ID,
            mediation_id="mediation-1",
            intent=intent,
            tool_intent_path="intent.json",
            dry_run_result=None,
            dry_run_result_path=None,
            approval_record=_approval_record(intent, approval_decision="approved"),
            approval_record_path="approvals/approval-1.json",
            mediated_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(record["mediation_decision"], "blocked")
        self.assertEqual(record["reason"], "side-effect actions require a passed dry run")

    def test_side_effect_intent_blocks_without_approval(self):
        intent = _tool_intent(action_class="external_side_effect", dry_run_supported=True)
        record = mediate_tool_intent(
            run_id=RUN_ID,
            mediation_id="mediation-1",
            intent=intent,
            tool_intent_path="intent.json",
            dry_run_result=_dry_run_result(intent, result_status="passed"),
            dry_run_result_path="dry-runs/dry-run-1.json",
            approval_record=None,
            approval_record_path=None,
            mediated_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(record["policy_decision"], "denied")
        self.assertEqual(record["mediation_decision"], "blocked")
        self.assertEqual(
            record["reason"],
            "side-effect actions require an approved approval record",
        )

    def test_side_effect_evidence_must_match_intent_scope(self):
        intent = _tool_intent(action_class="edit_local", dry_run_supported=True)
        mismatched = dict(intent)
        mismatched["intent_id"] = "other-intent"

        record = mediate_tool_intent(
            run_id=RUN_ID,
            mediation_id="mediation-1",
            intent=intent,
            tool_intent_path="intent.json",
            dry_run_result=_dry_run_result(mismatched, result_status="passed"),
            dry_run_result_path="dry-runs/dry-run-1.json",
            approval_record=_approval_record(intent, approval_decision="approved"),
            approval_record_path="approvals/approval-1.json",
            mediated_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(record["mediation_decision"], "blocked")
        self.assertEqual(
            record["reason"], "dry-run result does not match the tool intent scope"
        )

    def test_malformed_dry_run_result_is_rejected_before_mediation(self):
        intent = _tool_intent(action_class="edit_local", dry_run_supported=True)
        dry_run_result = _dry_run_result(intent, result_status="passed")
        dry_run_result["arguments"] = {"report_id": RUN_ID}

        with self.assertRaisesRegex(ValueError, "dry-run result has unknown fields"):
            mediate_tool_intent(
                run_id=RUN_ID,
                mediation_id="mediation-1",
                intent=intent,
                tool_intent_path="intent.json",
                dry_run_result=dry_run_result,
                dry_run_result_path="dry-runs/dry-run-1.json",
                approval_record=_approval_record(
                    intent, approval_decision="approved"
                ),
                approval_record_path="approvals/approval-1.json",
                mediated_at="2026-05-29T12:30:45Z",
            )

    def test_malformed_approval_record_is_rejected_before_mediation(self):
        intent = _tool_intent(action_class="edit_local", dry_run_supported=True)
        approval_record = _approval_record(intent, approval_decision="approved")
        approval_record["credentials"] = {"token": "do-not-load"}

        with self.assertRaisesRegex(ValueError, "approval record has unknown fields"):
            mediate_tool_intent(
                run_id=RUN_ID,
                mediation_id="mediation-1",
                intent=intent,
                tool_intent_path="intent.json",
                dry_run_result=_dry_run_result(intent, result_status="passed"),
                dry_run_result_path="dry-runs/dry-run-1.json",
                approval_record=approval_record,
                approval_record_path="approvals/approval-1.json",
                mediated_at="2026-05-29T12:30:45Z",
            )


def _tool_intent(*, action_class, dry_run_supported):
    return {
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": action_class,
        "tool_name": "publish-report",
        "arguments": {"report_id": RUN_ID},
        "dry_run_supported": dry_run_supported,
        "justification": "Publish one generated report.",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


def _dry_run_result(intent, *, result_status):
    return {
        "schema_version": "dry-run-result.v1",
        "run_id": RUN_ID,
        "dry_run_id": "dry-run-1",
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": intent["action_class"],
        "tool_name": intent["tool_name"],
        "dry_run_kind": "read_only_simulation",
        "result_status": result_status,
        "recorded_by": "local-operator",
        "recorded_at": "2026-05-29T12:30:45Z",
        "summary": "Simulated local write.",
        "artifact_refs": ["dry-runs/dry-run-1.json"],
        "evidence_refs": intent["evidence_refs"],
        "tool_intent_path": "intent.json",
    }


def _approval_record(intent, *, approval_decision):
    return {
        "schema_version": "approval-record.v1",
        "run_id": RUN_ID,
        "approval_id": "approval-1",
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": intent["action_class"],
        "tool_name": intent["tool_name"],
        "approval_decision": approval_decision,
        "approved_by": "local-operator",
        "approved_at": "2026-05-29T12:30:45Z",
        "justification": "Dry run reviewed.",
        "dry_run_ref": "dry-runs/dry-run-1.json",
        "evidence_refs": intent["evidence_refs"],
        "tool_intent_path": "intent.json",
    }
