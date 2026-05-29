import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.runtime import (  # noqa: E402
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
                paths.source_health_path("20260529T123045Z-deadbeef", "github-main"),
                root / "source-health" / "20260529T123045Z-deadbeef" / "github-main.json",
            )
            self.assertEqual(
                paths.profile_state_dir("pulse"),
                root / "profiles" / "pulse" / "state",
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


if __name__ == "__main__":
    unittest.main()
