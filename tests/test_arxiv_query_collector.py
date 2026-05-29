import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.collector.arxiv_query import (  # noqa: E402
    ArxivQueryCollector,
    ArxivQuerySource,
    HttpResponse,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)
RUN_ID = "20260529T123045Z-deadbeef"
EXPECTED_URL = (
    "https://export.arxiv.org/api/query?"
    "search_query=all%3A%22coding+agent%22+AND+cat%3Acs.AI"
    "&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
)


class ArxivQueryCollectorTests(unittest.TestCase):
    def test_collect_writes_success_raw_body_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b"<feed><title>Arxiv query results</title></feed>"
            )
            seen_requests = []

            def fake_http_get(request):
                seen_requests.append(request)
                return HttpResponse(
                    url=request.url,
                    status=200,
                    headers={
                        "Content-Type": "application/atom+xml; charset=utf-8",
                        "ETag": '"abc"',
                        "Last-Modified": "Fri, 29 May 2026 12:30:00 GMT",
                    },
                    body=body,
                )

            collector = ArxivQueryCollector(paths, http_get=fake_http_get)
            source = ArxivQuerySource(
                source_id="arxiv-query-code-agents",
                query='all:"coding agent" AND cat:cs.AI',
                max_results=5,
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "success")
            self.assertEqual(result.canonical_url, EXPECTED_URL)
            self.assertEqual(result.http_status, 200)
            self.assertEqual(result.body_hash, hashlib.sha256(body).hexdigest())
            self.assertEqual(result.body_path.read_bytes(), body)

            self.assertEqual(len(seen_requests), 1)
            request = seen_requests[0]
            self.assertEqual(request.url, EXPECTED_URL)
            self.assertIn("application/atom+xml", request.headers["Accept"])
            self.assertIn("shared-intake-governance", request.headers["User-Agent"])
            self.assertEqual(request.timeout_seconds, 20.0)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(
                metadata,
                {
                    "schema_version": "raw-metadata.v1",
                    "run_id": RUN_ID,
                    "source_id": "arxiv-query-code-agents",
                    "source_type": "arxiv_query",
                    "fetch_status": "success",
                    "fetched_at": "2026-05-29T12:30:45Z",
                    "request_url": EXPECTED_URL,
                    "canonical_url": EXPECTED_URL,
                    "http_status": 200,
                    "etag": '"abc"',
                    "last_modified": "Fri, 29 May 2026 12:30:00 GMT",
                    "content_type": "application/atom+xml; charset=utf-8",
                    "body_hash": result.body_hash,
                    "storage_path": str(result.body_path),
                    "collector_version": "arxiv-query.v1",
                    "error": None,
                },
            )

    def test_collect_records_http_failure_without_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = b"<feed><title>service unavailable</title></feed>"

            def fake_http_get(request):
                return HttpResponse(
                    url=request.url,
                    status=503,
                    headers={"Content-Type": "application/atom+xml"},
                    body=body,
                )

            collector = ArxivQueryCollector(paths, http_get=fake_http_get)
            source = ArxivQuerySource(
                source_id="arxiv-query-code-agents",
                query='all:"coding agent" AND cat:cs.AI',
                max_results=5,
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "failed")
            self.assertEqual(result.http_status, 503)
            self.assertEqual(result.body_path.read_bytes(), body)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_type"], "arxiv_query")
            self.assertEqual(metadata["fetch_status"], "failed")
            self.assertEqual(metadata["canonical_url"], EXPECTED_URL)
            self.assertEqual(metadata["http_status"], 503)
            self.assertEqual(metadata["body_hash"], hashlib.sha256(body).hexdigest())
            self.assertEqual(metadata["storage_path"], str(result.body_path))
            self.assertEqual(
                metadata["error"],
                {
                    "kind": "http_error",
                    "message": "HTTP 503",
                    "retryable": True,
                },
            )

    def test_collect_records_transport_failure_without_body(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            def fake_http_get(request):
                raise TimeoutError("request timed out")

            collector = ArxivQueryCollector(paths, http_get=fake_http_get)
            source = ArxivQuerySource(
                source_id="arxiv-query-code-agents",
                query='all:"coding agent" AND cat:cs.AI',
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
                    "arxiv-query-code-agents", FETCHED_AT, "transport-error"
                ),
            )
            self.assertEqual(metadata["source_type"], "arxiv_query")
            self.assertEqual(metadata["canonical_url"], EXPECTED_URL)
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

    def test_source_rejects_unsafe_or_unbounded_inputs(self):
        invalid_cases = [
            {"source_id": "../bad", "query": "all:agent", "max_results": 5},
            {"source_id": "arxiv query", "query": "all:agent", "max_results": 5},
            {"source_id": "arxiv-query", "query": "", "max_results": 5},
            {"source_id": "arxiv-query", "query": "   ", "max_results": 5},
            {"source_id": "arxiv-query", "query": "<script>", "max_results": 5},
            {"source_id": "arxiv-query", "query": "all:agent\ncat:cs.AI", "max_results": 5},
            {"source_id": "arxiv-query", "query": "all:agent", "max_results": 0},
            {"source_id": "arxiv-query", "query": "all:agent", "max_results": 101},
            {
                "source_id": "arxiv-query",
                "query": "all:agent",
                "max_results": 5,
                "api_base_url": "http://export.arxiv.org/api/query",
            },
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    ArxivQuerySource(**case)


if __name__ == "__main__":
    unittest.main()
