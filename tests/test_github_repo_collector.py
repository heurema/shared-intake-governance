import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.collector.github_repo import (  # noqa: E402
    GitHubRepoCollector,
    GitHubRepoSource,
    HttpResponse,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)
RUN_ID = "20260529T123045Z-deadbeef"


class GitHubRepoCollectorTests(unittest.TestCase):
    def test_collect_writes_success_raw_body_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = (
                b'{"full_name":"heurema/signum",'
                b'"html_url":"https://github.com/heurema/signum"}\n'
            )
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

            collector = GitHubRepoCollector(paths, http_get=fake_http_get)
            source = GitHubRepoSource(
                source_id="github-signum", owner="heurema", repo="signum"
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "success")
            self.assertEqual(result.canonical_url, "https://github.com/heurema/signum")
            self.assertEqual(result.http_status, 200)
            self.assertEqual(result.body_hash, hashlib.sha256(body).hexdigest())
            self.assertEqual(result.body_path.read_bytes(), body)

            self.assertEqual(len(seen_requests), 1)
            request = seen_requests[0]
            self.assertEqual(
                request.url, "https://api.github.com/repos/heurema/signum"
            )
            self.assertEqual(request.headers["Accept"], "application/vnd.github+json")
            self.assertIn("shared-intake-governance", request.headers["User-Agent"])
            self.assertEqual(request.timeout_seconds, 20.0)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(
                metadata,
                {
                    "schema_version": "raw-metadata.v1",
                    "run_id": RUN_ID,
                    "source_id": "github-signum",
                    "source_type": "github_repo",
                    "fetch_status": "success",
                    "fetched_at": "2026-05-29T12:30:45Z",
                    "request_url": "https://api.github.com/repos/heurema/signum",
                    "canonical_url": "https://github.com/heurema/signum",
                    "http_status": 200,
                    "etag": '"abc"',
                    "last_modified": "Fri, 29 May 2026 12:30:00 GMT",
                    "content_type": "application/json; charset=utf-8",
                    "body_hash": result.body_hash,
                    "storage_path": str(result.body_path),
                    "collector_version": "github-repo.v1",
                    "error": None,
                },
            )

    def test_collect_records_rate_limit_like_response_without_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = b'{"message":"API rate limit exceeded"}\n'

            def fake_http_get(request):
                return HttpResponse(
                    url=request.url,
                    status=403,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "X-RateLimit-Remaining": "0",
                    },
                    body=body,
                )

            collector = GitHubRepoCollector(paths, http_get=fake_http_get)
            source = GitHubRepoSource(
                source_id="github-signum", owner="heurema", repo="signum"
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "failed")
            self.assertEqual(result.http_status, 403)
            self.assertEqual(result.body_path.read_bytes(), body)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["fetch_status"], "failed")
            self.assertEqual(
                metadata["canonical_url"], "https://github.com/heurema/signum"
            )
            self.assertEqual(metadata["http_status"], 403)
            self.assertEqual(metadata["body_hash"], hashlib.sha256(body).hexdigest())
            self.assertEqual(metadata["storage_path"], str(result.body_path))
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

            collector = GitHubRepoCollector(paths, http_get=fake_http_get)
            source = GitHubRepoSource(
                source_id="github-signum", owner="heurema", repo="signum"
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
                    "github-signum", FETCHED_AT, "transport-error"
                ),
            )
            self.assertEqual(
                metadata["canonical_url"], "https://github.com/heurema/signum"
            )
            self.assertIsNone(metadata["http_status"])
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

    def test_source_rejects_unsafe_path_and_url_segments(self):
        invalid_cases = [
            {"source_id": "../bad", "owner": "heurema", "repo": "signum"},
            {"source_id": "github-signum", "owner": "../heurema", "repo": "signum"},
            {"source_id": "github-signum", "owner": "heurema", "repo": "sig/num"},
            {"source_id": "github signum", "owner": "heurema", "repo": "signum"},
            {
                "source_id": "github-signum",
                "owner": "heurema",
                "repo": "signum",
                "api_base_url": "https:///api",
            },
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    GitHubRepoSource(**case)


if __name__ == "__main__":
    unittest.main()
