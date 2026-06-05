import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.collector.github_releases import (  # noqa: E402
    GitHubReleasesCollector,
    GitHubReleasesSource,
    HttpResponse,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)
RUN_ID = "20260529T123045Z-deadbeef"
EXPECTED_URL = (
    "https://api.github.com/repos/heurema/shared-intake-governance/releases"
    "?per_page=5"
)


class GitHubReleasesCollectorTests(unittest.TestCase):
    def test_collect_writes_success_raw_body_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = json.dumps(
                [
                    {
                        "html_url": (
                            "https://github.com/heurema/shared-intake-governance"
                            "/releases/tag/v1.0.0"
                        ),
                        "tag_name": "v1.0.0",
                        "name": "Shared Intake Governance v1.0.0",
                        "body": "Coding agent intake release notes.",
                        "published_at": "2026-05-28T10:00:00Z",
                    }
                ],
                sort_keys=True,
            ).encode("utf-8")
            seen_requests = []

            def fake_http_get(request):
                seen_requests.append(request)
                return HttpResponse(
                    url=request.url,
                    status=200,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "ETag": '"abc"',
                        "Last-Modified": "Fri, 29 May 2026 12:30:00 GMT",
                    },
                    body=body,
                )

            collector = GitHubReleasesCollector(paths, http_get=fake_http_get)
            source = GitHubReleasesSource(
                source_id="github-releases-shared-intake",
                owner="heurema",
                repo="shared-intake-governance",
                max_results=5,
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "success")
            self.assertEqual(
                result.canonical_url,
                "https://github.com/heurema/shared-intake-governance/releases",
            )
            self.assertEqual(result.request_url, EXPECTED_URL)
            self.assertEqual(result.http_status, 200)
            self.assertEqual(result.body_hash, hashlib.sha256(body).hexdigest())
            self.assertEqual(result.body_path.read_bytes(), body)

            self.assertEqual(len(seen_requests), 1)
            request = seen_requests[0]
            self.assertEqual(request.url, EXPECTED_URL)
            self.assertEqual(request.headers["Accept"], "application/vnd.github+json")
            self.assertIn("shared-intake-governance", request.headers["User-Agent"])
            self.assertEqual(request.headers["X-GitHub-Api-Version"], "2022-11-28")
            self.assertEqual(request.timeout_seconds, 20.0)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(
                metadata,
                {
                    "schema_version": "raw-metadata.v1",
                    "run_id": RUN_ID,
                    "source_id": "github-releases-shared-intake",
                    "source_type": "github_releases",
                    "fetch_status": "success",
                    "fetched_at": "2026-05-29T12:30:45Z",
                    "request_url": EXPECTED_URL,
                    "canonical_url": (
                        "https://github.com/heurema/shared-intake-governance/releases"
                    ),
                    "http_status": 200,
                    "etag": '"abc"',
                    "last_modified": "Fri, 29 May 2026 12:30:00 GMT",
                    "content_type": "application/json; charset=utf-8",
                    "body_hash": result.body_hash,
                    "storage_path": str(result.body_path),
                    "collector_version": "github-releases.v1",
                    "error": None,
                },
            )

    def test_collect_uses_github_token_from_env_when_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = b"[]"
            seen_requests = []

            def fake_http_get(request):
                seen_requests.append(request)
                return HttpResponse(
                    url=request.url,
                    status=200,
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    body=body,
                )

            collector = GitHubReleasesCollector(paths, http_get=fake_http_get)
            source = GitHubReleasesSource(
                source_id="github-releases-shared-intake",
                owner="heurema",
                repo="shared-intake-governance",
                max_results=5,
            )

            with mock.patch.dict(os.environ, {"GH_TOKEN": "test-gh-token"}, clear=False):
                collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(
                seen_requests[0].headers["Authorization"],
                "Bearer test-gh-token",
            )

    def test_collect_records_rate_limit_failure_without_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            def fake_http_get(request):
                return HttpResponse(
                    url=request.url,
                    status=403,
                    headers={
                        "Content-Type": "application/json",
                        "X-RateLimit-Remaining": "0",
                    },
                    body=b'{"message":"rate limit"}',
                )

            collector = GitHubReleasesCollector(paths, http_get=fake_http_get)
            source = GitHubReleasesSource(
                source_id="github-releases-shared-intake",
                owner="heurema",
                repo="shared-intake-governance",
                max_results=5,
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "failed")
            self.assertEqual(result.http_status, 403)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_type"], "github_releases")
            self.assertEqual(metadata["fetch_status"], "failed")
            self.assertEqual(
                metadata["error"],
                {
                    "kind": "rate_limited",
                    "message": "HTTP 403",
                    "retryable": True,
                },
            )

    def test_collect_records_transport_failure_without_body(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            def fake_http_get(request):
                raise TimeoutError("request timed out")

            collector = GitHubReleasesCollector(paths, http_get=fake_http_get)
            source = GitHubReleasesSource(
                source_id="github-releases-shared-intake",
                owner="heurema",
                repo="shared-intake-governance",
                max_results=5,
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "failed")
            self.assertIsNone(result.http_status)
            self.assertIsNone(result.body_hash)
            self.assertIsNone(result.body_path)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(
                result.metadata_path,
                paths.raw_failure_metadata_path(
                    "github-releases-shared-intake", FETCHED_AT, "transport-error"
                ),
            )
            self.assertEqual(metadata["source_type"], "github_releases")
            self.assertIsNone(metadata["body_hash"])
            self.assertIsNone(metadata["storage_path"])
            self.assertEqual(
                metadata["error"],
                {
                    "kind": "transport_error",
                    "message": "request timed out",
                    "retryable": True,
                },
            )

    def test_source_rejects_unsafe_or_unbounded_inputs(self):
        invalid_cases = [
            {
                "source_id": "../bad",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 5,
            },
            {
                "source_id": "github releases",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 5,
            },
            {
                "source_id": "github-releases",
                "owner": "../heurema",
                "repo": "shared-intake-governance",
                "max_results": 5,
            },
            {
                "source_id": "github-releases",
                "owner": "heurema",
                "repo": "shared/intake",
                "max_results": 5,
            },
            {
                "source_id": "github-releases",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 0,
            },
            {
                "source_id": "github-releases",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 101,
            },
            {
                "source_id": "github-releases",
                "owner": "heurema",
                "repo": "shared-intake-governance",
                "max_results": 5,
                "api_base_url": "http://api.github.com",
            },
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    GitHubReleasesSource(**case)


if __name__ == "__main__":
    unittest.main()
