import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.adapters import invoke_provider_request  # noqa: E402
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class ProviderInvocationTests(unittest.TestCase):
    def test_invocation_runs_explicit_command_and_records_stdout_ref(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            result = invoke_provider_request(
                paths=paths,
                run_id=RUN_ID,
                result_id="provider-result-1",
                provider_request=_provider_request(),
                provider_request_path="provider-requests/provider-request-1.json",
                command=[
                    sys.executable,
                    "-c",
                    (
                        "import json, sys; "
                        "request = json.load(sys.stdin); "
                        "print('handled ' + request['provider'])"
                    ),
                ],
                recorded_by="local-operator",
                timeout_seconds=5.0,
                usage_metadata={"test_run": "true"},
                recorded_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )

            self.assertEqual(result["schema_version"], "provider-result.v1")
            self.assertEqual(result["result_status"], "succeeded")
            self.assertEqual(result["response_refs"], [str(stdout_path)])
            self.assertEqual(result["usage_metadata"]["exit_code"], "0")
            self.assertEqual(result["usage_metadata"]["test_run"], "true")
            self.assertEqual(stdout_path.read_text(encoding="utf-8"), "handled claude\n")
            self.assertNotIn("provider_response", result)
            self.assertNotIn("credentials", result)

    def test_invocation_records_failed_result_for_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            result = invoke_provider_request(
                paths=paths,
                run_id=RUN_ID,
                result_id="provider-result-1",
                provider_request=_provider_request(),
                provider_request_path="provider-requests/provider-request-1.json",
                command=[
                    sys.executable,
                    "-c",
                    (
                        "import sys; "
                        "print('partial response'); "
                        "print('provider failed', file=sys.stderr); "
                        "sys.exit(7)"
                    ),
                ],
                recorded_by="local-operator",
                timeout_seconds=5.0,
                usage_metadata={},
                recorded_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )
            stderr_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stderr.txt"
            )

            self.assertEqual(result["result_status"], "failed")
            self.assertEqual(result["response_refs"], [str(stdout_path), str(stderr_path)])
            self.assertEqual(result["usage_metadata"]["exit_code"], "7")
            self.assertEqual(
                result["error"],
                {
                    "kind": "provider_command_failed",
                    "message": "provider command exited 7",
                },
            )
            self.assertEqual(stdout_path.read_text(encoding="utf-8"), "partial response\n")
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "provider failed\n")

    def test_invocation_records_failed_result_for_timeout(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            result = invoke_provider_request(
                paths=paths,
                run_id=RUN_ID,
                result_id="provider-result-1",
                provider_request=_provider_request(),
                provider_request_path="provider-requests/provider-request-1.json",
                command=[
                    sys.executable,
                    "-c",
                    (
                        "import time; "
                        "print('before timeout', flush=True); "
                        "time.sleep(2)"
                    ),
                ],
                recorded_by="local-operator",
                timeout_seconds=0.2,
                usage_metadata={},
                recorded_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )

            self.assertEqual(result["result_status"], "failed")
            self.assertEqual(result["response_refs"], [str(stdout_path)])
            self.assertEqual(result["usage_metadata"]["timeout_seconds"], "0.2")
            self.assertEqual(
                result["error"],
                {
                    "kind": "provider_command_timeout",
                    "message": "provider command timed out after 0.2 seconds",
                },
            )
            self.assertEqual(
                stdout_path.read_text(encoding="utf-8"), "before timeout\n"
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
