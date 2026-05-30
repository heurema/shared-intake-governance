import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.executor import execute_tool_intent  # noqa: E402
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class ToolExecutionTests(unittest.TestCase):
    def test_ready_mediation_runs_explicit_command_and_records_stdout_ref(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                (
                    "import json, sys; "
                    "intent = json.load(sys.stdin); "
                    "print('executed ' + intent['tool_name'])"
                ),
            ]
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(command=command),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=5.0,
                execution_metadata={"test_run": "true"},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            self.assertEqual(result["schema_version"], "tool-execution-result.v1")
            self.assertEqual(result["execution_status"], "succeeded")
            self.assertEqual(result["output_refs"], [str(stdout_path)])
            self.assertEqual(result["execution_metadata"]["exit_code"], "0")
            self.assertEqual(result["execution_metadata"]["test_run"], "true")
            self.assertEqual(
                stdout_path.read_text(encoding="utf-8"), "executed write-report\n"
            )
            self.assertNotIn("arguments", result)
            self.assertNotIn("credentials", result)

    def test_blocked_mediation_does_not_invoke_command(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "raise SystemExit(99)",
            ]
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(command=command),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="blocked"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=5.0,
                execution_metadata={},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            self.assertEqual(result["execution_status"], "blocked")
            self.assertEqual(result["output_refs"], [])
            self.assertEqual(
                result["error"],
                {
                    "kind": "mediation_not_ready",
                    "message": "execution mediation is blocked",
                },
            )
            self.assertFalse(stdout_path.exists())

    def test_ready_mediation_requires_bound_command_before_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "raise SystemExit(99)",
            ]
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(command=None),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=5.0,
                execution_metadata={},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            self.assertEqual(result["execution_status"], "blocked")
            self.assertEqual(result["output_refs"], [])
            self.assertEqual(
                result["error"],
                {
                    "kind": "tool_command_not_bound",
                    "message": (
                        "tool intent arguments.command must be a non-empty "
                        "string array"
                    ),
                },
            )
            self.assertFalse(stdout_path.exists())

    def test_ready_mediation_rejects_mismatched_command_before_invocation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "raise SystemExit(99)",
            ]
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(
                    command=[
                        sys.executable,
                        "-c",
                        "print('expected command')",
                    ]
                ),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=5.0,
                execution_metadata={},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            self.assertEqual(result["execution_status"], "blocked")
            self.assertEqual(result["output_refs"], [])
            self.assertEqual(
                result["error"],
                {
                    "kind": "tool_command_mismatch",
                    "message": (
                        "supplied command does not match tool intent "
                        "arguments.command"
                    ),
                },
            )
            self.assertFalse(stdout_path.exists())

    def test_ready_mediation_records_failed_result_for_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "print('partial execution'); "
                    "print('tool failed', file=sys.stderr); "
                    "sys.exit(7)"
                ),
            ]
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(command=command),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=5.0,
                execution_metadata={},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )
            stderr_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stderr.txt"
            )

            self.assertEqual(result["execution_status"], "failed")
            self.assertEqual(result["output_refs"], [str(stdout_path), str(stderr_path)])
            self.assertEqual(result["execution_metadata"]["exit_code"], "7")
            self.assertEqual(
                result["error"],
                {
                    "kind": "tool_command_failed",
                    "message": "tool command exited 7",
                },
            )
            self.assertEqual(
                stdout_path.read_text(encoding="utf-8"), "partial execution\n"
            )
            self.assertEqual(stderr_path.read_text(encoding="utf-8"), "tool failed\n")

    def test_ready_mediation_records_failed_result_for_timeout(self):
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
            result = execute_tool_intent(
                paths=paths,
                run_id=RUN_ID,
                execution_id="execution-1",
                intent=_tool_intent(command=command),
                tool_intent_path="intent.json",
                mediation_record=_mediation_record(mediation_decision="ready"),
                mediation_record_path="mediation/20260529T123045Z-deadbeef/mediation-1.json",
                command=command,
                executed_by="local-operator",
                timeout_seconds=0.2,
                execution_metadata={},
                executed_at="2026-05-29T12:30:45Z",
            )

            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            self.assertEqual(result["execution_status"], "failed")
            self.assertEqual(result["output_refs"], [str(stdout_path)])
            self.assertEqual(result["execution_metadata"]["timeout_seconds"], "0.2")
            self.assertEqual(
                result["error"],
                {
                    "kind": "tool_command_timeout",
                    "message": "tool command timed out after 0.2 seconds",
                },
            )
            self.assertEqual(
                stdout_path.read_text(encoding="utf-8"), "before timeout\n"
            )

    def test_invalid_tool_intent_is_rejected_before_command_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "print('should not run')",
            ]
            intent = _tool_intent(command=command)
            intent["credentials"] = {"token": "do-not-forward"}
            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            with self.assertRaisesRegex(ValueError, "unknown fields"):
                execute_tool_intent(
                    paths=paths,
                    run_id=RUN_ID,
                    execution_id="execution-1",
                    intent=intent,
                    tool_intent_path="intent.json",
                    mediation_record=_mediation_record(mediation_decision="ready"),
                    mediation_record_path=(
                        "mediation/20260529T123045Z-deadbeef/mediation-1.json"
                    ),
                    command=command,
                    executed_by="local-operator",
                    timeout_seconds=5.0,
                    execution_metadata={},
                    executed_at="2026-05-29T12:30:45Z",
                )

            self.assertFalse(stdout_path.exists())

    def test_invalid_mediation_record_is_rejected_before_command_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            command = [
                sys.executable,
                "-c",
                "print('should not run')",
            ]
            mediation_record = _mediation_record(mediation_decision="ready")
            mediation_record["arguments"] = {"report_id": RUN_ID}
            stdout_path = paths.tool_execution_artifact_path(
                RUN_ID, "execution-1", "stdout.txt"
            )

            with self.assertRaisesRegex(
                ValueError, "execution mediation has unknown fields"
            ):
                execute_tool_intent(
                    paths=paths,
                    run_id=RUN_ID,
                    execution_id="execution-1",
                    intent=_tool_intent(command=command),
                    tool_intent_path="intent.json",
                    mediation_record=mediation_record,
                    mediation_record_path=(
                        "mediation/20260529T123045Z-deadbeef/mediation-1.json"
                    ),
                    command=command,
                    executed_by="local-operator",
                    timeout_seconds=5.0,
                    execution_metadata={},
                    executed_at="2026-05-29T12:30:45Z",
                )

            self.assertFalse(stdout_path.exists())


def _tool_intent(*, command):
    arguments = {"report_id": RUN_ID}
    if command is not None:
        arguments["command"] = list(command)
    return {
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "arguments": arguments,
        "dry_run_supported": True,
        "justification": "Write one generated report.",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


def _mediation_record(*, mediation_decision):
    return {
        "schema_version": "execution-mediation.v1",
        "run_id": RUN_ID,
        "mediation_id": "mediation-1",
        "mediated_at": "2026-05-29T12:30:45Z",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "policy_decision": "gated",
        "mediation_decision": mediation_decision,
        "reason": "test mediation",
        "dry_run_result_path": "dry-runs/20260529T123045Z-deadbeef/dry-run-1.json",
        "approval_record_path": "approvals/20260529T123045Z-deadbeef/approval-1.json",
        "tool_intent_path": "intent.json",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }
