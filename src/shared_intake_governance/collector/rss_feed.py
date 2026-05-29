"""Read-only generic RSS feed collector."""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from shared_intake_governance.runtime import RawWriter, RuntimePaths


COLLECTOR_VERSION = "rss-feed.v1"
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SOURCE_TRUST = {
    "official",
    "maintainer",
    "platform",
    "secondary",
    "social",
    "unknown",
}


@dataclass(frozen=True)
class RssFeedSource:
    source_id: str
    feed_url: str
    source_trust: str = "secondary"

    def __post_init__(self) -> None:
        _safe_segment(self.source_id, "source_id")
        parsed = urllib.parse.urlparse(self.feed_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("feed_url must be an https URL")
        if self.source_trust not in _SOURCE_TRUST:
            raise ValueError("source_trust must be a supported trust value")

    @property
    def request_url(self) -> str:
        return self.feed_url

    @property
    def canonical_url(self) -> str:
        return self.feed_url


@dataclass(frozen=True)
class HttpRequest:
    url: str
    headers: Mapping[str, str]
    timeout_seconds: float


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class RssFeedCollectionResult:
    source_id: str
    fetch_status: str
    canonical_url: str
    request_url: str
    http_status: int | None
    body_hash: str | None
    body_path: Path | None
    metadata_path: Path


HttpGet = Callable[[HttpRequest], HttpResponse]


class RssFeedCollector:
    """Collect RSS feed evidence without sanitizing or projecting."""

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
        source: RssFeedSource,
        *,
        run_id: str,
        fetched_at: datetime | None = None,
    ) -> RssFeedCollectionResult:
        fetched_at_text = _format_utc(fetched_at or datetime.now(timezone.utc))
        request = HttpRequest(
            url=source.request_url,
            headers={
                "Accept": (
                    "application/rss+xml, application/xml;q=0.9, "
                    "text/xml;q=0.8, */*;q=0.7"
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
            "source_type": "rss",
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

        return RssFeedCollectionResult(
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
        source: RssFeedSource,
        run_id: str,
        fetched_at_text: str,
        exc: Exception,
    ) -> RssFeedCollectionResult:
        message = str(exc) or exc.__class__.__name__
        metadata = {
            "schema_version": "raw-metadata.v1",
            "run_id": run_id,
            "source_id": source.source_id,
            "source_type": "rss",
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
        return RssFeedCollectionResult(
            source_id=source.source_id,
            fetch_status="failed",
            canonical_url=source.canonical_url,
            request_url=source.request_url,
            http_status=None,
            body_hash=None,
            body_path=None,
            metadata_path=metadata_path,
        )


def _default_http_get(request: HttpRequest) -> HttpResponse:
    url_request = urllib.request.Request(
        request.url, headers=dict(request.headers), method="GET"
    )
    try:
        with urllib.request.urlopen(
            url_request, timeout=request.timeout_seconds
        ) as response:
            return HttpResponse(
                url=response.geturl(),
                status=response.status,
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        return HttpResponse(
            url=exc.geturl(),
            status=exc.code,
            headers=dict(exc.headers.items()),
            body=exc.read(),
        )


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_status(status: int, body: bytes) -> str:
    if 200 <= status <= 299 and body:
        return "success"
    if 200 <= status <= 299:
        return "degraded"
    return "failed"


def _response_error(status: int, body: bytes) -> dict[str, object] | None:
    if 200 <= status <= 299 and body:
        return None
    if 200 <= status <= 299:
        return {"kind": "empty_body", "message": f"HTTP {status}", "retryable": True}
    return {
        "kind": "http_error",
        "message": f"HTTP {status}",
        "retryable": status == 408 or status == 409 or status == 429 or status >= 500,
    }


def _failure_id(error: dict[str, object] | None) -> str | None:
    if error is None:
        return None
    return str(error["kind"]).replace("_", "-")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _safe_segment(value: str, label: str) -> str:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError(f"{label} must be a safe path segment")
    return value
