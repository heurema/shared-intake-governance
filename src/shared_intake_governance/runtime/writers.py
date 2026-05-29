"""Writers for immutable raw evidence and operational artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import RuntimePaths


@dataclass(frozen=True)
class RawBodyWrite:
    body_hash: str
    path: Path


class RawWriter:
    """Write raw payload bodies and metadata before source collectors exist."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_body(
        self,
        source_id: str,
        fetched_at: str | datetime,
        body: bytes | bytearray | memoryview,
    ) -> RawBodyWrite:
        payload = bytes(body)
        body_hash = hashlib.sha256(payload).hexdigest()
        path = self.paths.raw_body_path(source_id, fetched_at, body_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return RawBodyWrite(body_hash=body_hash, path=path)

    def write_metadata(
        self, metadata: dict[str, Any], *, failure_id: str | None = None
    ) -> Path:
        source_id = str(metadata["source_id"])
        fetched_at = str(metadata["fetched_at"])
        body_hash = metadata.get("body_hash")

        if body_hash is None:
            if failure_id is None:
                failure_id = str(metadata["run_id"])
            path = self.paths.raw_failure_metadata_path(source_id, fetched_at, failure_id)
        else:
            path = self.paths.raw_metadata_path(source_id, fetched_at, str(body_hash))

        return _write_json(path, metadata)


class RunWriter:
    """Write run manifests as stable JSON artifacts."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_manifest(self, manifest: dict[str, Any]) -> Path:
        path = self.paths.run_manifest_path(str(manifest["run_id"]))
        return _write_json(path, manifest)


class SourceHealthWriter:
    """Write one source-health artifact for a run/source pair."""

    def __init__(self, paths: RuntimePaths):
        self.paths = paths

    def write_source_health(self, source_health: dict[str, Any]) -> Path:
        path = self.paths.source_health_path(
            str(source_health["run_id"]), str(source_health["source_id"])
        )
        return _write_json(path, source_health)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
