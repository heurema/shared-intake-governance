"""Read-only generic news feed collector."""

from __future__ import annotations

import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from shared_intake_governance.collector.rss_feed import (
    HttpRequest,
    HttpResponse,
    _default_http_get,
    _failure_id,
    _fetch_status,
    _format_utc,
    _header,
    _response_error,
    _safe_segment,
)
from shared_intake_governance.runtime import RawWriter, RuntimePaths
from shared_intake_governance.validation import require_https_url


COLLECTOR_VERSION = "news-feed.v1"
_SOURCE_TRUST = {
    "official",
    "maintainer",
    "platform",
    "secondary",
    "social",
    "unknown",
}


@dataclass(frozen=True)
class NewsFeedSource:
    source_id: str
    feed_url: str
    source_trust: str = "secondary"

    def __post_init__(self) -> None:
        _safe_segment(self.source_id, "source_id")
        require_https_url(self.feed_url, "feed_url")
        if self.source_trust not in _SOURCE_TRUST:
            raise ValueError("source_trust must be a supported trust value")

    @property
    def request_url(self) -> str:
        return self.feed_url

    @property
    def canonical_url(self) -> str:
        return self.feed_url


@dataclass(frozen=True)
class NewsFeedCollectionResult:
    source_id: str
    fetch_status: str
    canonical_url: str
    request_url: str
    http_status: int | None
    body_hash: str | None
    body_path: Path | None
    metadata_path: Path


HttpGet = Callable[[HttpRequest], HttpResponse]


class NewsFeedCollector:
    """Collect news feed evidence without sanitizing or projecting."""

    def __init__(
        self,
        paths: RuntimePaths,
        *,
        http_get: HttpGet | None = None,
        timeout_seconds: float = 20.0,
        user_agent: str = "shared-intake-governance/0",
    ):
        self.raw_writer = RawWriter(paths)
        self.http_get = http_get or _default_http_get
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def collect(
        self,
        source: NewsFeedSource,
        *,
        run_id: str,
        fetched_at: datetime | None = None,
    ) -> NewsFeedCollectionResult:
        fetched_at_text = _format_utc(fetched_at or datetime.now(timezone.utc))
        request = HttpRequest(
            url=source.request_url,
            headers={
                "Accept": (
                    "application/rss+xml, application/atom+xml;q=0.9, "
                    "application/xml;q=0.8, text/xml;q=0.7, */*;q=0.6"
                ),
                "User-Agent": self.user_agent,
            },
            timeout_seconds=self.timeout_seconds,
        )

        try:
            response = self.http_get(request)
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            return self._record_transport_failure(source, run_id, fetched_at_text, exc)

        raw_body = None
        if response.body:
            raw_body = self.raw_writer.write_body(
                source.source_id, fetched_at_text, response.body
            )

        fetch_status = _fetch_status(response.status, response.body)
        error = _response_error(response.status, response.body)
        metadata = {
            "schema_version": "raw-metadata.v1",
            "run_id": run_id,
            "source_id": source.source_id,
            "source_type": "news",
            "fetch_status": fetch_status,
            "fetched_at": fetched_at_text,
            "request_url": request.url,
            "canonical_url": source.canonical_url,
            "http_status": response.status,
            "etag": _header(response.headers, "etag"),
            "last_modified": _header(response.headers, "last-modified"),
            "content_type": _header(response.headers, "content-type"),
            "body_hash": None if raw_body is None else raw_body.body_hash,
            "storage_path": None if raw_body is None else str(raw_body.path),
            "collector_version": COLLECTOR_VERSION,
            "source_trust": source.source_trust,
            "error": error,
        }
        metadata_path = self.raw_writer.write_metadata(
            metadata, failure_id=_failure_id(error)
        )

        return NewsFeedCollectionResult(
            source_id=source.source_id,
            fetch_status=fetch_status,
            canonical_url=source.canonical_url,
            request_url=request.url,
            http_status=response.status,
            body_hash=None if raw_body is None else raw_body.body_hash,
            body_path=None if raw_body is None else raw_body.path,
            metadata_path=metadata_path,
        )

    def _record_transport_failure(
        self,
        source: NewsFeedSource,
        run_id: str,
        fetched_at_text: str,
        exc: Exception,
    ) -> NewsFeedCollectionResult:
        message = str(exc) or exc.__class__.__name__
        metadata = {
            "schema_version": "raw-metadata.v1",
            "run_id": run_id,
            "source_id": source.source_id,
            "source_type": "news",
            "fetch_status": "failed",
            "fetched_at": fetched_at_text,
            "request_url": source.request_url,
            "canonical_url": source.canonical_url,
            "http_status": None,
            "etag": None,
            "last_modified": None,
            "content_type": None,
            "body_hash": None,
            "storage_path": None,
            "collector_version": COLLECTOR_VERSION,
            "source_trust": source.source_trust,
            "error": {
                "kind": "transport_error",
                "message": message,
                "retryable": True,
            },
        }
        metadata_path = self.raw_writer.write_metadata(
            metadata, failure_id="transport-error"
        )
        return NewsFeedCollectionResult(
            source_id=source.source_id,
            fetch_status="failed",
            canonical_url=source.canonical_url,
            request_url=source.request_url,
            http_status=None,
            body_hash=None,
            body_path=None,
            metadata_path=metadata_path,
        )
