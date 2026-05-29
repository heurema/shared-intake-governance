import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.cli.pipeline import main  # noqa: E402
from shared_intake_governance.collector.github_repo import (  # noqa: E402
    GitHubRepoCollectionResult,
)
from shared_intake_governance.runtime import RawWriter, RuntimePaths  # noqa: E402


RUN_ID = "20260529T123045Z-deadbeef"


class CliPipelineTests(unittest.TestCase):
    def test_run_github_repo_pipeline_collects_sanitizes_and_projects(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runtime_root = root / "runtime"
            profile_path = _write_profile(root)
            stdout = io.StringIO()

            exit_code = main(
                [
                    "run-github-repo",
                    "--runtime-root",
                    str(runtime_root),
                    "--profile",
                    str(profile_path),
                    "--source-id",
                    "github-signum",
                    "--owner",
                    "heurema",
                    "--repo",
                    "signum",
                    "--run-id",
                    RUN_ID,
                    "--output-id",
                    RUN_ID,
                ],
                stdout=stdout,
                collector_factory=SuccessfulCollector,
            )

            summary = json.loads(stdout.getvalue())

            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["run_id"], RUN_ID)
            self.assertEqual(summary["source_id"], "github-signum")
            self.assertEqual(summary["fetch_status"], "success")
            self.assertEqual(summary["http_status"], 200)
            self.assertTrue(Path(summary["raw_metadata_path"]).exists())
            self.assertTrue(Path(summary["raw_body_path"]).exists())
            self.assertTrue(Path(summary["clean_record_path"]).exists())
            self.assertTrue(Path(summary["projection_path"]).exists())
            self.assertEqual(summary["projected_items"], 1)

            projection = json.loads(Path(summary["projection_path"]).read_text())
            self.assertEqual(projection["profile_id"], "code-intel-kernel")
            self.assertEqual(projection["counts"]["items_written"], 1)

    def test_run_github_repo_pipeline_fails_closed_when_collection_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runtime_root = root / "runtime"
            profile_path = _write_profile(root)
            stdout = io.StringIO()

            exit_code = main(
                [
                    "run-github-repo",
                    "--runtime-root",
                    str(runtime_root),
                    "--profile",
                    str(profile_path),
                    "--source-id",
                    "github-signum",
                    "--owner",
                    "heurema",
                    "--repo",
                    "signum",
                    "--run-id",
                    RUN_ID,
                    "--output-id",
                    RUN_ID,
                ],
                stdout=stdout,
                collector_factory=FailedCollector,
            )

            summary = json.loads(stdout.getvalue())

            self.assertEqual(exit_code, 2)
            self.assertEqual(summary["status"], "collection_failed")
            self.assertEqual(summary["fetch_status"], "failed")
            self.assertEqual(summary["http_status"], 403)
            self.assertTrue(Path(summary["raw_metadata_path"]).exists())
            self.assertIsNone(summary["raw_body_path"])
            self.assertIsNone(summary["clean_record_path"])
            self.assertIsNone(summary["projection_path"])
            self.assertFalse((runtime_root / "clean").exists())
            self.assertFalse((runtime_root / "profiles").exists())


class SuccessfulCollector:
    def __init__(self, paths, **kwargs):
        self.paths = paths

    def collect(self, source, *, run_id, fetched_at=None):
        writer = RawWriter(self.paths)
        fetched_at = fetched_at or datetime(
            2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc
        )
        body = json.dumps(
            {
                "full_name": f"{source.owner}/{source.repo}",
                "html_url": source.canonical_url,
                "description": "Coding agent benchmark toolkit.",
                "created_at": "2025-01-02T03:04:05Z",
                "license": {"spdx_id": "Apache-2.0"},
                "topics": ["coding-agent", "benchmark"],
            },
            sort_keys=True,
        ).encode("utf-8")
        raw_body = writer.write_body(source.source_id, fetched_at, body)
        metadata_path = writer.write_metadata(
            {
                "schema_version": "raw-metadata.v1",
                "run_id": run_id,
                "source_id": source.source_id,
                "source_type": "github_repo",
                "fetch_status": "success",
                "fetched_at": "2026-05-29T12:30:45Z",
                "request_url": source.request_url,
                "canonical_url": source.canonical_url,
                "http_status": 200,
                "etag": None,
                "last_modified": None,
                "content_type": "application/json",
                "body_hash": raw_body.body_hash,
                "storage_path": str(raw_body.path),
                "collector_version": "test",
                "error": None,
            }
        )
        return GitHubRepoCollectionResult(
            source_id=source.source_id,
            fetch_status="success",
            canonical_url=source.canonical_url,
            request_url=source.request_url,
            http_status=200,
            body_hash=raw_body.body_hash,
            body_path=raw_body.path,
            metadata_path=metadata_path,
        )


class FailedCollector:
    def __init__(self, paths, **kwargs):
        self.paths = paths

    def collect(self, source, *, run_id, fetched_at=None):
        writer = RawWriter(self.paths)
        fetched_at = fetched_at or datetime(
            2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc
        )
        metadata = {
            "schema_version": "raw-metadata.v1",
            "run_id": run_id,
            "source_id": source.source_id,
            "source_type": "github_repo",
            "fetch_status": "failed",
            "fetched_at": "2026-05-29T12:30:45Z",
            "request_url": source.request_url,
            "canonical_url": source.canonical_url,
            "http_status": 403,
            "etag": None,
            "last_modified": None,
            "content_type": "application/json",
            "body_hash": None,
            "storage_path": None,
            "collector_version": "test",
            "error": {
                "kind": "rate_limited",
                "message": "HTTP 403",
                "retryable": True,
            },
        }
        metadata_path = writer.write_metadata(metadata, failure_id="rate-limited")
        return GitHubRepoCollectionResult(
            source_id=source.source_id,
            fetch_status="failed",
            canonical_url=source.canonical_url,
            request_url=source.request_url,
            http_status=403,
            body_hash=None,
            body_path=None,
            metadata_path=metadata_path,
        )


def _write_profile(root):
    profile_path = root / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "code-intel-kernel",
                "description": "Code intelligence research intake.",
                "accepted_sources": ["github_repo"],
                "keywords": ["coding agent"],
                "required_risk_flags_absent": [
                    "instruction_like_content",
                    "tool_escalation_language",
                ],
                "output_mode": "research_digest",
            }
        ),
        encoding="utf-8",
    )
    return profile_path


if __name__ == "__main__":
    unittest.main()
