"""Narrow local pipeline CLI for current Phase 1 runtime slices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from shared_intake_governance.collector.github_repo import (
    GitHubRepoCollectionResult,
    GitHubRepoCollector,
    GitHubRepoSource,
)
from shared_intake_governance.projector import ProfileProjector
from shared_intake_governance.runtime import RuntimePaths, generate_run_id
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
    source = GitHubRepoSource(
        source_id=args.source_id,
        owner=args.owner,
        repo=args.repo,
        api_base_url=args.api_base_url,
    )
    collector = collector_factory(paths)
    collection = collector.collect(source, run_id=run_id)

    summary = _collection_summary(run_id, collection)
    if collection.fetch_status != "success":
        summary.update(
            {
                "status": "collection_failed",
                "clean_record_path": None,
                "projection_path": None,
                "projected_items": 0,
            }
        )
        _print_json(stdout, summary)
        return 2

    clean_record = CleanRecordEmitter(paths).emit_from_raw_metadata(
        collection.metadata_path
    )
    projection = ProfileProjector(paths).project(args.profile, output_id=output_id)
    summary.update(
        {
            "status": "completed",
            "clean_record_path": str(clean_record.path),
            "projection_path": str(projection.path),
            "projected_items": projection.report["counts"]["items_written"],
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
