import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.adapters import invoke_provider_request  # noqa: E402
from shared_intake_governance.provider_presets import (  # noqa: E402
    ProviderPreset,
    provider_command_hash,
)
import shared_intake_governance.provider_presets as provider_presets  # noqa: E402
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class ProviderInvocationTests(unittest.TestCase):
    def test_invocation_runs_explicit_command_and_records_stdout_ref(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                (
                    "import json, sys; "
                    "request = json.load(sys.stdin); "
                    "print('handled ' + request['provider'])"
                ),
            ]
            with _provider_preset(command):
                result = invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=_provider_request(command=command),
                    provider_request_path="provider-requests/provider-request-1.json",
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
            command = [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "print('partial response'); "
                    "print('provider failed', file=sys.stderr); "
                    "sys.exit(7)"
                ),
            ]
            with _provider_preset(command):
                result = invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=_provider_request(command=command),
                    provider_request_path="provider-requests/provider-request-1.json",
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
            command = [
                sys.executable,
                "-c",
                (
                    "import time; "
                    "print('before timeout', flush=True); "
                    "time.sleep(2)"
                ),
            ]
            with _provider_preset(command):
                result = invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=_provider_request(command=command),
                    provider_request_path="provider-requests/provider-request-1.json",
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

    def test_invalid_provider_request_is_rejected_before_command_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "print('should not run')",
            ]
            provider_request = _provider_request(command=command)
            provider_request["credentials"] = {"token": "do-not-forward"}
            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )

            with self.assertRaisesRegex(ValueError, "unknown fields"):
                invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=provider_request,
                    provider_request_path="provider-requests/provider-request-1.json",
                    recorded_by="local-operator",
                    timeout_seconds=5.0,
                    usage_metadata={},
                    recorded_at="2026-05-29T12:30:45Z",
                )

            self.assertFalse(stdout_path.exists())

    def test_side_effect_provider_request_is_rejected_before_command_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "print('should not run')",
            ]
            provider_request = _provider_request(command=command)
            provider_request["action_class"] = "edit_local"
            provider_request["policy_decision"] = "gated"
            provider_request["capabilities"] = ["edit_local"]
            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )

            with self.assertRaisesRegex(ValueError, "read_only provider requests"):
                invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=provider_request,
                    provider_request_path="provider-requests/provider-request-1.json",
                    recorded_by="local-operator",
                    timeout_seconds=5.0,
                    usage_metadata={},
                    recorded_at="2026-05-29T12:30:45Z",
                )

            self.assertFalse(stdout_path.exists())

    def test_tampered_provider_request_command_is_blocked_before_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            expected_command = [
                sys.executable,
                "-c",
                "print('expected command')",
            ]
            tampered_command = [
                sys.executable,
                "-c",
                "raise SystemExit(99)",
            ]
            with _provider_preset(expected_command):
                result = invoke_provider_request(
                    paths=paths,
                    run_id=RUN_ID,
                    result_id="provider-result-1",
                    provider_request=_provider_request(command=tampered_command),
                    provider_request_path="provider-requests/provider-request-1.json",
                    recorded_by="local-operator",
                    timeout_seconds=5.0,
                    usage_metadata={},
                    recorded_at="2026-05-29T12:30:45Z",
                )

            stdout_path = paths.provider_result_artifact_path(
                RUN_ID, "provider-result-1", "stdout.txt"
            )

            self.assertEqual(result["result_status"], "blocked")
            self.assertEqual(result["response_refs"], [])
            self.assertEqual(
                result["error"],
                {
                    "kind": "provider_preset_mismatch",
                    "message": "provider request does not match provider preset",
                },
            )
            self.assertFalse(stdout_path.exists())


def _provider_request(*, command):
    return {
        "schema_version": "provider-request.v1",
        "run_id": RUN_ID,
        "request_id": "provider-request-1",
        "prepared_at": "2026-05-29T12:30:45Z",
        "provider": "claude",
        "preset_id": "claude_readonly_local",
        "mediation_record_path": "mediation/20260529T123045Z-deadbeef/mediation-1.json",
        "mediation_id": "mediation-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "read_only",
        "tool_name": "publish-report",
        "policy_decision": "allowed",
        "mediation_decision": "ready",
        "capabilities": ["read_only"],
        "resolved_command": list(command),
        "command_hash": provider_command_hash(command),
        "context_refs": ["profiles/code-intel-kernel/reports/report.json"],
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


def _provider_preset(command):
    return patch.dict(
        provider_presets._PROVIDER_PRESETS,
        {
            "claude_readonly_local": ProviderPreset(
                preset_id="claude_readonly_local",
                provider="claude",
                resolved_command=tuple(command),
            )
        },
    )
