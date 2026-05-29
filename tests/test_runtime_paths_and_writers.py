import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.runtime import (  # noqa: E402
    AuditWriter,
    ApprovalWriter,
    DryRunWriter,
    MediationWriter,
    ProviderRequestWriter,
    ProviderResultWriter,
    RawWriter,
    RunWriter,
    RuntimePaths,
    generate_run_id,
)


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)


class RuntimePathTests(unittest.TestCase):
    def test_runtime_paths_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "runtime"
            paths = RuntimePaths(root)
            digest = "a" * 64

            self.assertEqual(paths.root, root)
            self.assertEqual(paths.raw_root, root / "raw")
            self.assertEqual(paths.clean_root, root / "clean")
            self.assertEqual(paths.runs_root, root / "runs")
            self.assertEqual(paths.source_health_root, root / "source-health")
            self.assertEqual(paths.audit_root, root / "audit")
            self.assertEqual(paths.approvals_root, root / "approvals")
            self.assertEqual(paths.dry_runs_root, root / "dry-runs")
            self.assertEqual(paths.mediation_root, root / "mediation")
            self.assertEqual(paths.provider_requests_root, root / "provider-requests")
            self.assertEqual(paths.provider_results_root, root / "provider-results")
            self.assertEqual(paths.profiles_root, root / "profiles")

            self.assertEqual(
                paths.raw_body_path("github-main", FETCHED_AT, digest),
                root / "raw" / "github-main" / "2026-05-29" / f"{digest}.body",
            )
            self.assertEqual(
                paths.raw_metadata_path("github-main", FETCHED_AT, digest),
                root / "raw" / "github-main" / "2026-05-29" / f"{digest}.meta.json",
            )
            self.assertEqual(
                paths.raw_failure_metadata_path(
                    "github-main", FETCHED_AT, "transport-timeout"
                ),
                root
                / "raw"
                / "github-main"
                / "2026-05-29"
                / "failed-transport-timeout.meta.json",
            )
            self.assertEqual(
                paths.clean_record_path("github-main-123"),
                root / "clean" / "github-main-123.json",
            )
            self.assertEqual(
                paths.run_manifest_path("20260529T123045Z-deadbeef"),
                root / "runs" / "20260529T123045Z-deadbeef.manifest.json",
            )
            self.assertEqual(
                paths.audit_log_path("20260529T123045Z-deadbeef"),
                root / "audit" / "20260529T123045Z-deadbeef.jsonl",
            )
            self.assertEqual(
                paths.approval_record_path(
                    "20260529T123045Z-deadbeef", "approval-1"
                ),
                root
                / "approvals"
                / "20260529T123045Z-deadbeef"
                / "approval-1.json",
            )
            self.assertEqual(
                paths.dry_run_result_path(
                    "20260529T123045Z-deadbeef", "dry-run-1"
                ),
                root
                / "dry-runs"
                / "20260529T123045Z-deadbeef"
                / "dry-run-1.json",
            )
            self.assertEqual(
                paths.mediation_record_path(
                    "20260529T123045Z-deadbeef", "mediation-1"
                ),
                root
                / "mediation"
                / "20260529T123045Z-deadbeef"
                / "mediation-1.json",
            )
            self.assertEqual(
                paths.provider_request_path(
                    "20260529T123045Z-deadbeef", "provider-request-1"
                ),
                root
                / "provider-requests"
                / "20260529T123045Z-deadbeef"
                / "provider-request-1.json",
            )
            self.assertEqual(
                paths.provider_result_path(
                    "20260529T123045Z-deadbeef", "provider-result-1"
                ),
                root
                / "provider-results"
                / "20260529T123045Z-deadbeef"
                / "provider-result-1.json",
            )
            self.assertEqual(
                paths.source_health_path("20260529T123045Z-deadbeef", "github-main"),
                root / "source-health" / "20260529T123045Z-deadbeef" / "github-main.json",
            )
            self.assertEqual(
                paths.profile_state_dir("pulse"),
                root / "profiles" / "pulse" / "state",
            )
            self.assertEqual(
                paths.profile_state_path("pulse", "seen-records"),
                root / "profiles" / "pulse" / "state" / "seen-records.json",
            )
            self.assertEqual(
                paths.profile_reports_dir("pulse"),
                root / "profiles" / "pulse" / "reports",
            )
            self.assertEqual(
                paths.profile_report_path("pulse", "20260529T123045Z-deadbeef"),
                root
                / "profiles"
                / "pulse"
                / "reports"
                / "20260529T123045Z-deadbeef.json",
            )

    def test_runtime_paths_reject_unsafe_segments(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            unsafe_values = ["", ".", "..", "../source", "source/name", "source name"]

            for value in unsafe_values:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        paths.clean_record_path(value)

            with self.assertRaises(ValueError):
                paths.raw_body_path("../source", FETCHED_AT, "a" * 64)
            with self.assertRaises(ValueError):
                paths.audit_log_path("../run")
            with self.assertRaises(ValueError):
                paths.approval_record_path("20260529T123045Z-deadbeef", "../approval")
            with self.assertRaises(ValueError):
                paths.dry_run_result_path("20260529T123045Z-deadbeef", "../dry-run")
            with self.assertRaises(ValueError):
                paths.mediation_record_path("20260529T123045Z-deadbeef", "../record")
            with self.assertRaises(ValueError):
                paths.provider_request_path("20260529T123045Z-deadbeef", "../request")
            with self.assertRaises(ValueError):
                paths.provider_result_path("20260529T123045Z-deadbeef", "../result")
            with self.assertRaises(ValueError):
                paths.profile_state_path("pulse", "../state")
            with self.assertRaises(ValueError):
                paths.profile_report_path("pulse", "../report")

    def test_generate_run_id_can_be_deterministic(self):
        self.assertEqual(
            generate_run_id(FETCHED_AT, token="deadbeef"),
            "20260529T123045Z-deadbeef",
        )


class RuntimeWriterTests(unittest.TestCase):
    def test_raw_writer_writes_body_and_metadata_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = RawWriter(paths)
            body = b'{"ok": true}\n'
            expected_hash = hashlib.sha256(body).hexdigest()

            raw_body = writer.write_body("github-main", FETCHED_AT, body)

            self.assertEqual(raw_body.body_hash, expected_hash)
            self.assertEqual(
                raw_body.path,
                paths.raw_body_path("github-main", FETCHED_AT, expected_hash),
            )
            self.assertEqual(raw_body.path.read_bytes(), body)

            metadata = _raw_metadata(raw_body)
            metadata_path = writer.write_metadata(metadata)
            first_write = metadata_path.read_text(encoding="utf-8")

            self.assertEqual(
                metadata_path,
                paths.raw_metadata_path("github-main", FETCHED_AT, expected_hash),
            )
            self.assertEqual(json.loads(first_write), metadata)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_metadata(metadata)
            self.assertEqual(metadata_path.read_text(encoding="utf-8"), first_write)

    def test_raw_writer_writes_failed_fetch_metadata_without_body(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = RawWriter(paths)
            metadata = _raw_metadata(None)
            metadata.update(
                {
                    "fetch_status": "failed",
                    "canonical_url": None,
                    "http_status": None,
                    "content_type": None,
                    "body_hash": None,
                    "storage_path": None,
                    "error": {
                        "kind": "timeout",
                        "message": "request timed out",
                        "retryable": True,
                    },
                }
            )

            metadata_path = writer.write_metadata(
                metadata, failure_id="transport-timeout"
            )

            self.assertEqual(
                metadata_path,
                paths.raw_failure_metadata_path(
                    "github-main", FETCHED_AT, "transport-timeout"
                ),
            )
            self.assertEqual(json.loads(metadata_path.read_text()), metadata)

    def test_run_writer_writes_manifest_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = RunWriter(paths)
            manifest = {
                "schema_version": "run-manifest.v1",
                "run_id": "20260529T123045Z-deadbeef",
                "mode": "daily_collection",
                "status": "completed",
                "started_at": "2026-05-29T12:30:45Z",
                "finished_at": "2026-05-29T12:31:45Z",
                "runtime_root": str(paths.root),
                "raw_root": str(paths.raw_root),
                "clean_root": str(paths.clean_root),
                "profiles_root": str(paths.profiles_root),
                "sources": ["github-main"],
                "counts": {
                    "raw_payloads_written": 1,
                    "raw_metadata_written": 1,
                    "clean_records_written": 0,
                    "projected_profiles": 0,
                    "quarantined_records": 0,
                    "failed_sources": 0,
                },
                "source_health": [],
            }

            manifest_path = writer.write_manifest(manifest)
            first_write = manifest_path.read_text(encoding="utf-8")

            self.assertEqual(
                manifest_path,
                paths.run_manifest_path("20260529T123045Z-deadbeef"),
            )
            self.assertEqual(json.loads(first_write), manifest)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_manifest(manifest)
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), first_write)

    def test_audit_writer_appends_jsonl_events(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = AuditWriter(paths)
            first_event = _audit_event("intent-1", "allowed")
            second_event = _audit_event("intent-2", "denied")

            audit_path = writer.write_event(first_event)
            writer.write_event(second_event)

            lines = audit_path.read_text(encoding="utf-8").splitlines()

            self.assertEqual(
                audit_path,
                paths.audit_log_path("20260529T123045Z-deadbeef"),
            )
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0]), first_event)
            self.assertEqual(json.loads(lines[1]), second_event)

    def test_approval_writer_writes_record_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = ApprovalWriter(paths)
            record = _approval_record()

            approval_path = writer.write_record(record)
            first_write = approval_path.read_text(encoding="utf-8")

            self.assertEqual(
                approval_path,
                paths.approval_record_path(
                    "20260529T123045Z-deadbeef", "approval-1"
                ),
            )
            self.assertEqual(json.loads(first_write), record)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_record(record)
            self.assertEqual(approval_path.read_text(encoding="utf-8"), first_write)

    def test_dry_run_writer_writes_result_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = DryRunWriter(paths)
            result = _dry_run_result()

            dry_run_path = writer.write_result(result)
            first_write = dry_run_path.read_text(encoding="utf-8")

            self.assertEqual(
                dry_run_path,
                paths.dry_run_result_path(
                    "20260529T123045Z-deadbeef", "dry-run-1"
                ),
            )
            self.assertEqual(json.loads(first_write), result)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_result(result)
            self.assertEqual(dry_run_path.read_text(encoding="utf-8"), first_write)

    def test_mediation_writer_writes_record_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = MediationWriter(paths)
            record = _mediation_record()

            mediation_path = writer.write_record(record)
            first_write = mediation_path.read_text(encoding="utf-8")

            self.assertEqual(
                mediation_path,
                paths.mediation_record_path(
                    "20260529T123045Z-deadbeef", "mediation-1"
                ),
            )
            self.assertEqual(json.loads(first_write), record)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_record(record)
            self.assertEqual(mediation_path.read_text(encoding="utf-8"), first_write)

    def test_provider_request_writer_writes_request_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = ProviderRequestWriter(paths)
            request = _provider_request()

            request_path = writer.write_request(request)
            first_write = request_path.read_text(encoding="utf-8")

            self.assertEqual(
                request_path,
                paths.provider_request_path(
                    "20260529T123045Z-deadbeef", "provider-request-1"
                ),
            )
            self.assertEqual(json.loads(first_write), request)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_request(request)
            self.assertEqual(request_path.read_text(encoding="utf-8"), first_write)

    def test_provider_result_writer_writes_result_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            writer = ProviderResultWriter(paths)
            result = _provider_result()

            result_path = writer.write_result(result)
            first_write = result_path.read_text(encoding="utf-8")

            self.assertEqual(
                result_path,
                paths.provider_result_path(
                    "20260529T123045Z-deadbeef", "provider-result-1"
                ),
            )
            self.assertEqual(json.loads(first_write), result)
            self.assertTrue(first_write.endswith("\n"))

            writer.write_result(result)
            self.assertEqual(result_path.read_text(encoding="utf-8"), first_write)


def _raw_metadata(raw_body):
    return {
        "schema_version": "raw-metadata.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "source_id": "github-main",
        "source_type": "github_repo",
        "fetch_status": "success",
        "fetched_at": "2026-05-29T12:30:45Z",
        "request_url": "https://api.github.com/repos/heurema/signum",
        "canonical_url": "https://github.com/heurema/signum",
        "http_status": 200,
        "etag": '"abc"',
        "last_modified": None,
        "content_type": "application/json",
        "body_hash": None if raw_body is None else raw_body.body_hash,
        "storage_path": None if raw_body is None else str(raw_body.path),
        "collector_version": "test",
        "error": None,
    }


def _audit_event(intent_id, decision):
    return {
        "schema_version": "governance-audit-event.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "event_type": "tool_intent_evaluated",
        "recorded_at": "2026-05-29T12:30:45Z",
        "intent_id": intent_id,
        "profile_id": "code-intel-kernel",
        "action_class": "read_only",
        "tool_name": "inspect-record",
        "decision": decision,
        "reason": "test decision",
        "dry_run_supported": False,
        "evidence_refs": ["clean/github_repo-good.json"],
        "tool_intent_path": "intent.json",
    }


def _approval_record():
    return {
        "schema_version": "approval-record.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "approval_id": "approval-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "approval_decision": "approved",
        "approved_by": "local-operator",
        "approved_at": "2026-05-29T12:30:45Z",
        "justification": "Dry run reviewed.",
        "dry_run_ref": "dry-runs/approval-1.json",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
        "tool_intent_path": "intent.json",
    }


def _dry_run_result():
    return {
        "schema_version": "dry-run-result.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "dry_run_id": "dry-run-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "dry_run_kind": "read_only_simulation",
        "result_status": "passed",
        "recorded_by": "local-operator",
        "recorded_at": "2026-05-29T12:30:45Z",
        "summary": "Simulated local write.",
        "artifact_refs": ["dry-runs/dry-run-1.json"],
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
        "tool_intent_path": "intent.json",
    }


def _mediation_record():
    return {
        "schema_version": "execution-mediation.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "mediation_id": "mediation-1",
        "mediated_at": "2026-05-29T12:30:45Z",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "policy_decision": "gated",
        "mediation_decision": "ready",
        "reason": "side-effect action has passed dry run and approved approval record",
        "dry_run_result_path": "dry-runs/20260529T123045Z-deadbeef/dry-run-1.json",
        "approval_record_path": "approvals/20260529T123045Z-deadbeef/approval-1.json",
        "tool_intent_path": "intent.json",
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


def _provider_request():
    return {
        "schema_version": "provider-request.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "request_id": "provider-request-1",
        "prepared_at": "2026-05-29T12:30:45Z",
        "provider": "claude",
        "mediation_record_path": "mediation/20260529T123045Z-deadbeef/mediation-1.json",
        "mediation_id": "mediation-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "policy_decision": "gated",
        "mediation_decision": "ready",
        "capabilities": ["edit_local"],
        "context_refs": ["profiles/code-intel-kernel/reports/report.json"],
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


def _provider_result():
    return {
        "schema_version": "provider-result.v1",
        "run_id": "20260529T123045Z-deadbeef",
        "result_id": "provider-result-1",
        "request_id": "provider-request-1",
        "provider": "claude",
        "recorded_by": "local-operator",
        "recorded_at": "2026-05-29T12:30:45Z",
        "result_status": "succeeded",
        "summary": "Provider completed the request.",
        "provider_request_path": "provider-requests/20260529T123045Z-deadbeef/provider-request-1.json",
        "mediation_id": "mediation-1",
        "intent_id": "intent-1",
        "profile_id": "code-intel-kernel",
        "action_class": "edit_local",
        "tool_name": "write-report",
        "response_refs": ["provider-results/provider-result-1.summary.json"],
        "usage_metadata": {"input_tokens": "120", "output_tokens": "30"},
        "error": None,
        "evidence_refs": ["profiles/code-intel-kernel/reports/report.json"],
    }


if __name__ == "__main__":
    unittest.main()
