import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.adapters import record_provider_result  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class ProviderResultTests(unittest.TestCase):
    def test_provider_result_captures_refs_and_usage_without_payloads(self):
        result = record_provider_result(
            run_id=RUN_ID,
            result_id="provider-result-1",
            provider_request=_provider_request(),
            provider_request_path="provider-requests/20260529T123045Z-deadbeef/provider-request-1.json",
            result_status="succeeded",
            recorded_by="local-operator",
            summary="Provider completed the request.",
            response_refs=["provider-results/provider-result-1.summary.json"],
            usage_metadata={"input_tokens": "120", "output_tokens": "30"},
            error=None,
            recorded_at="2026-05-29T12:30:45Z",
        )

        self.assertEqual(result["schema_version"], "provider-result.v1")
        self.assertEqual(result["provider"], "claude")
        self.assertEqual(result["request_id"], "provider-request-1")
        self.assertEqual(result["result_status"], "succeeded")
        self.assertEqual(result["usage_metadata"]["input_tokens"], "120")
        self.assertEqual(result["response_refs"], ["provider-results/provider-result-1.summary.json"])
        self.assertNotIn("arguments", result)
        self.assertNotIn("credentials", result)
        self.assertNotIn("provider_response", result)

    def test_failed_result_requires_error(self):
        with self.assertRaises(ValueError):
            record_provider_result(
                run_id=RUN_ID,
                result_id="provider-result-1",
                provider_request=_provider_request(),
                provider_request_path="provider-requests/20260529T123045Z-deadbeef/provider-request-1.json",
                result_status="failed",
                recorded_by="local-operator",
                summary="Provider failed.",
                response_refs=[],
                usage_metadata={},
                error=None,
                recorded_at="2026-05-29T12:30:45Z",
            )

    def test_success_result_rejects_error_payload(self):
        with self.assertRaises(ValueError):
            record_provider_result(
                run_id=RUN_ID,
                result_id="provider-result-1",
                provider_request=_provider_request(),
                provider_request_path="provider-requests/20260529T123045Z-deadbeef/provider-request-1.json",
                result_status="succeeded",
                recorded_by="local-operator",
                summary="Provider completed the request.",
                response_refs=[],
                usage_metadata={},
                error={"kind": "provider_error", "message": "unexpected"},
                recorded_at="2026-05-29T12:30:45Z",
            )


def _provider_request():
    return {
        "schema_version": "provider-request.v1",
        "run_id": RUN_ID,
        "request_id": "provider-request-1",
        "prepared_at": "2026-05-29T12:30:45Z",
        "provider": "claude",
        "mediation_record_path": "mediation/20260529T123045Z-deadbeef/mediation-1.json",
        "mediation_id": "mediation-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "publish-report",
        "policy_decision": "gated",
        "mediation_decision": "ready",
        "capabilities": ["edit_local"],
        "context_refs": ["profiles/code-intel-kernel/reports/report.json"],
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }
