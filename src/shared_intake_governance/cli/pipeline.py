"""Narrow local pipeline CLI for current Phase 1 runtime slices."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from shared_intake_governance.collector.github_repo import (
    GitHubRepoCollectionResult,
    GitHubRepoCollector,
    GitHubRepoSource,
)
from shared_intake_governance.projector import ProfileProjector
from shared_intake_governance.runtime import (
    RunWriter,
    RuntimePaths,
    SourceHealthWriter,
    generate_run_id,
)
from shared_intake_governance.sanitizer import CleanRecordEmitter


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    collector_factory: type[GitHubRepoCollector] = GitHubRepoCollector,
) -> int:
    args = _parser().parse_args(argv)
    stdout = stdout or sys.stdout

    if args.command == "run-github-repo":
        return _run_github_repo(args, stdout, collector_factory)

    raise ValueError(f"unsupported command: {args.command}")


def _run_github_repo(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[GitHubRepoCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = GitHubRepoSource(
        source_id=args.source_id,
        owner=args.owner,
        repo=args.repo,
        api_base_url=args.api_base_url,
    )
    collector = collector_factory(paths)
    collection = collector.collect(source, run_id=run_id)
    raw_metadata = _read_json(collection.metadata_path)

    summary = _collection_summary(run_id, collection)
    if collection.fetch_status != "success":
        evidence = _write_run_evidence(
            paths,
            run_id=run_id,
            source_id=source.source_id,
            status="failed",
            started_at=started_at,
            counts={
                "raw_payloads_written": 0,
                "raw_metadata_written": 1,
                "clean_records_written": 0,
                "projected_profiles": 0,
                "quarantined_records": 0,
                "failed_sources": 1,
            },
            raw_metadata=raw_metadata,
        )
        summary.update(
            {
                "status": "collection_failed",
                "clean_record_path": None,
                "projection_path": None,
                "projected_items": 0,
                "run_manifest_path": str(evidence["run_manifest_path"]),
                "source_health_path": str(evidence["source_health_path"]),
            }
        )
        _print_json(stdout, summary)
        return 2

    clean_record = CleanRecordEmitter(paths).emit_from_raw_metadata(
        collection.metadata_path
    )
    projection = ProfileProjector(paths).project(args.profile, output_id=output_id)
    evidence = _write_run_evidence(
        paths,
        run_id=run_id,
        source_id=source.source_id,
        status="completed",
        started_at=started_at,
        counts={
            "raw_payloads_written": 1 if collection.body_path is not None else 0,
            "raw_metadata_written": 1,
            "clean_records_written": 1,
            "projected_profiles": 1,
            "quarantined_records": 1 if clean_record.record["quarantined"] else 0,
            "failed_sources": 0,
        },
        raw_metadata=raw_metadata,
    )
    summary.update(
        {
            "status": "completed",
            "clean_record_path": str(clean_record.path),
            "projection_path": str(projection.path),
            "projected_items": projection.report["counts"]["items_written"],
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _collection_summary(
    run_id: str, collection: GitHubRepoCollectionResult
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "source_id": collection.source_id,
        "fetch_status": collection.fetch_status,
        "http_status": collection.http_status,
        "raw_metadata_path": str(collection.metadata_path),
        "raw_body_path": (
            None if collection.body_path is None else str(collection.body_path)
        ),
    }


def _write_run_evidence(
    paths: RuntimePaths,
    *,
    run_id: str,
    source_id: str,
    status: str,
    started_at: str,
    counts: dict[str, int],
    raw_metadata: dict[str, Any],
) -> dict[str, Path]:
    finished_at = _format_utc(datetime.now(timezone.utc))
    source_health = _source_health(run_id, source_id, finished_at, raw_metadata)
    source_health_path = SourceHealthWriter(paths).write_source_health(source_health)
    manifest_path = RunWriter(paths).write_manifest(
        {
            "schema_version": "run-manifest.v1",
            "run_id": run_id,
            "mode": "daily_collection",
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "runtime_root": str(paths.root),
            "raw_root": str(paths.raw_root),
            "clean_root": str(paths.clean_root),
            "profiles_root": str(paths.profiles_root),
            "sources": [source_id],
            "counts": counts,
            "source_health": [str(source_health_path)],
        }
    )
    return {
        "run_manifest_path": manifest_path,
        "source_health_path": source_health_path,
    }


def _source_health(
    run_id: str, source_id: str, checked_at: str, raw_metadata: dict[str, Any]
) -> dict[str, Any]:
    error = raw_metadata["error"]
    success = raw_metadata["fetch_status"] == "success"
    return {
        "schema_version": "source-health.v1",
        "run_id": run_id,
        "source_id": source_id,
        "source_type": raw_metadata["source_type"],
        "status": "healthy" if success else "failed",
        "checked_at": checked_at,
        "attempted_fetches": 1,
        "successful_fetches": 1 if success else 0,
        "failed_fetches": 0 if success else 1,
        "raw_records_written": 1,
        "degraded_reasons": [] if error is None else [str(error["kind"])],
        "last_error": error,
        "next_retry_after": None,
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_json(stdout: TextIO, payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True), file=stdout)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shared-intake-governance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser(
        "run-github-repo",
        help="Collect one GitHub repo, emit one clean record, and project one profile.",
    )
    run.add_argument("--runtime-root", required=True)
    run.add_argument("--profile", required=True)
    run.add_argument("--source-id", required=True)
    run.add_argument("--owner", required=True)
    run.add_argument("--repo", required=True)
    run.add_argument("--run-id")
    run.add_argument("--output-id")
    run.add_argument("--api-base-url", default="https://api.github.com")
    return parser
