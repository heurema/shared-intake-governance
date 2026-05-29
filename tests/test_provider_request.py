import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.adapters import prepare_provider_request  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class ProviderRequestTests(unittest.TestCase):
    def test_ready_mediation_becomes_provider_request_without_arguments(self):
        request = prepare_provider_request(
            run_id=RUN_ID,
            request_id="provider-request-1",
            provider="claude",
            mediation_record=_mediation_record(mediation_decision="ready"),
            mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
            context_refs=["profiles/code-intel-kernel/reports/report.json"],
            prepared_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(request["schema_version"], "provider-request.v1")
        self.assertEqual(request["provider"], "claude")
        self.assertEqual(request["mediation_decision"], "ready")
        self.assertEqual(request["capabilities"], ["edit_local"])
        self.assertEqual(
            request["context_refs"],
            ["profiles/code-intel-kernel/reports/report.json"],
        )
        self.assertNotIn("arguments", request)
        self.assertNotIn("credentials", request)

    def test_blocked_mediation_cannot_prepare_provider_request(self):
        with self.assertRaises(ValueError):
            prepare_provider_request(
                run_id=RUN_ID,
                request_id="provider-request-1",
                provider="claude",
                mediation_record=_mediation_record(mediation_decision="blocked"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                context_refs=[],
                prepared_at="2026-05-29T12:30:45Z",
            )

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            prepare_provider_request(
                run_id=RUN_ID,
                request_id="provider-request-1",
                provider="unknown",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                context_refs=[],
                prepared_at="2026-05-29T12:30:45Z",
            )

    def test_malformed_mediation_record_is_rejected_before_request_preparation(self):
        mediation_record = _mediation_record(mediation_decision="ready")
        mediation_record["arguments"] = {"report_id": RUN_ID}

        with self.assertRaisesRegex(ValueError, "unknown fields"):
            prepare_provider_request(
                run_id=RUN_ID,
                request_id="provider-request-1",
                provider="claude",
                mediation_record=mediation_record,
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                context_refs=[],
                prepared_at="2026-05-29T12:30:45Z",
            )


def _mediation_record(*, mediation_decision):
    return {
        "schema_version": "execution-mediation.v1",
        "run_id": RUN_ID,
        "mediation_id": "mediation-1",
        "mediated_at": "2026-05-29T12:30:45Z",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "publish-report",
        "policy_decision": "gated",
        "mediation_decision": mediation_decision,
        "reason": "test mediation",
        "dry_run_result_path": "dry-runs/dry-run-1.json",
        "approval_record_path": "approvals/approval-1.json",
        "tool_intent_path": "intent.json",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }
