import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared_intake_governance.collector.news_feed import (  # noqa: E402
    HttpResponse,
    NewsFeedCollector,
    NewsFeedSource,
)
from shared_intake_governance.runtime import RuntimePaths  # noqa: E402


FETCHED_AT = datetime(2026, 5, 29, 12, 30, 45, tzinfo=timezone.utc)
RUN_ID = "20260529T123045Z-deadbeef"
FEED_URL = "https://example.test/news.xml"


class NewsFeedCollectorTests(unittest.TestCase):
    def test_collect_writes_success_raw_body_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")
            body = (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b"<rss><channel><title>Example news</title></channel></rss>"
            )
            seen_requests = []

            def fake_http_get(request):
                seen_requests.append(request)
                return HttpResponse(
                    url=request.url,
                    status=200,
                    headers={
                        "Content-Type": "application/rss+xml; charset=utf-8",
                        "ETag": '"abc"',
                        "Last-Modified": "Fri, 29 May 2026 12:30:00 GMT",
                    },
                    body=body,
                )

            collector = NewsFeedCollector(paths, http_get=fake_http_get)
            source = NewsFeedSource(
                source_id="news-example",
                feed_url=FEED_URL,
                source_trust="official",
            )

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "success")
            self.assertEqual(result.canonical_url, FEED_URL)
            self.assertEqual(result.http_status, 200)
            self.assertEqual(result.body_hash, hashlib.sha256(body).hexdigest())
            self.assertEqual(result.body_path.read_bytes(), body)

            self.assertEqual(len(seen_requests), 1)
            request = seen_requests[0]
            self.assertEqual(request.url, FEED_URL)
            self.assertIn("application/rss+xml", request.headers["Accept"])
            self.assertIn("shared-intake-governance", request.headers["User-Agent"])
            self.assertEqual(request.timeout_seconds, 20.0)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(
                metadata,
                {
                    "schema_version": "raw-metadata.v1",
                    "run_id": RUN_ID,
                    "source_id": "news-example",
                    "source_type": "news",
                    "fetch_status": "success",
                    "fetched_at": "2026-05-29T12:30:45Z",
                    "request_url": FEED_URL,
                    "canonical_url": FEED_URL,
                    "http_status": 200,
                    "etag": '"abc"',
                    "last_modified": "Fri, 29 May 2026 12:30:00 GMT",
                    "content_type": "application/rss+xml; charset=utf-8",
                    "body_hash": result.body_hash,
                    "storage_path": str(result.body_path),
                    "collector_version": "news-feed.v1",
                    "source_trust": "official",
                    "error": None,
                },
            )

    def test_collect_records_transport_failure_without_body(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = RuntimePaths(Path(tmp_dir) / "runtime")

            def fake_http_get(request):
                raise TimeoutError("timed out")

            collector = NewsFeedCollector(paths, http_get=fake_http_get)
            source = NewsFeedSource(source_id="news-example", feed_url=FEED_URL)

            result = collector.collect(source, run_id=RUN_ID, fetched_at=FETCHED_AT)

            self.assertEqual(result.fetch_status, "failed")
            self.assertIsNone(result.http_status)
            self.assertIsNone(result.body_hash)
            self.assertIsNone(result.body_path)

            metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_type"], "news")
            self.assertEqual(metadata["source_trust"], "secondary")
            self.assertIsNone(metadata["body_hash"])
            self.assertIsNone(metadata["storage_path"])
            self.assertEqual(
                metadata["error"],
                {
                    "kind": "transport_error",
                    "message": "timed out",
                    "retryable": True,
                },
            )

    def test_source_rejects_unsafe_or_non_https_inputs(self):
        invalid_cases = [
            {"source_id": "../bad", "feed_url": FEED_URL},
            {"source_id": "news example", "feed_url": FEED_URL},
            {"source_id": "news-example", "feed_url": "http://example.test/news.xml"},
            {"source_id": "news-example", "feed_url": "https:///news.xml"},
            {
                "source_id": "news-example",
                "feed_url": FEED_URL,
                "source_trust": "private",
            },
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    NewsFeedSource(**case)


if __name__ == "__main__":
    unittest.main()
