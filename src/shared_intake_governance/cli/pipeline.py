"""Narrow local pipeline CLI for current Phase 1 runtime slices."""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from shared_intake_governance.collector.arxiv_rss_keywords import (
    ArxivRssKeywordsCollectionResult,
    ArxivRssKeywordsCollector,
    ArxivRssKeywordsSource,
)
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


_SMOKE_BOUNDARY_FILENAME = "SMOKE_RUNTIME_DO_NOT_COMMIT.txt"


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    collector_factory: type[GitHubRepoCollector] = GitHubRepoCollector,
    arxiv_collector_factory: type[ArxivRssKeywordsCollector] = (
        ArxivRssKeywordsCollector
    ),
) -> int:
    args = _parser().parse_args(argv)
    stdout = stdout or sys.stdout

    if args.command == "run-github-repo":
        return _run_github_repo(args, stdout, collector_factory)
    if args.command == "run-arxiv-rss-keywords":
        return _run_arxiv_rss_keywords(args, stdout, arxiv_collector_factory)
    if args.command == "run-source-config":
        return _run_source_config(
            args,
            stdout,
            collector_factory,
            arxiv_collector_factory,
        )
    if args.command == "smoke-source-config":
        return _smoke_source_config(
            args,
            stdout,
            collector_factory,
            arxiv_collector_factory,
        )
    if args.command == "list-runs":
        return _list_runs(args, stdout)
    if args.command == "list-clean-records":
        return _list_clean_records(args, stdout)
    if args.command == "inspect-record":
        return _inspect_record(args, stdout)
    if args.command == "inspect-run":
        return _inspect_run(args, stdout)
    if args.command == "show-source-health":
        return _show_source_health(args, stdout)

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


def _run_arxiv_rss_keywords(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[ArxivRssKeywordsCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = ArxivRssKeywordsSource(
        source_id=args.source_id,
        keywords=args.keywords,
        max_results=args.max_results,
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
                "clean_record_paths": [],
                "projection_path": None,
                "projected_items": 0,
                "run_manifest_path": str(evidence["run_manifest_path"]),
                "source_health_path": str(evidence["source_health_path"]),
            }
        )
        _print_json(stdout, summary)
        return 2

    clean_records = CleanRecordEmitter(paths).emit_all_from_raw_metadata(
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
            "clean_records_written": len(clean_records),
            "projected_profiles": 1,
            "quarantined_records": sum(
                1
                for clean_record in clean_records
                if clean_record.record["quarantined"]
            ),
            "failed_sources": 0,
        },
        raw_metadata=raw_metadata,
    )
    summary.update(
        {
            "status": "completed",
            "clean_record_paths": [
                str(clean_record.path) for clean_record in clean_records
            ],
            "projection_path": str(projection.path),
            "projected_items": projection.report["counts"]["items_written"],
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_source_config(
    args: argparse.Namespace,
    stdout: TextIO,
    github_collector_factory: type[GitHubRepoCollector],
    arxiv_collector_factory: type[ArxivRssKeywordsCollector],
) -> int:
    source_config = _load_source_config(args.source_config)
    source_type = source_config["source_type"]

    if source_type == "github_repo":
        return _run_github_repo(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                owner=source_config["owner"],
                repo=source_config["repo"],
                api_base_url=source_config["api_base_url"],
                run_id=args.run_id,
                output_id=args.output_id,
            ),
            stdout,
            github_collector_factory,
        )
    if source_type == "arxiv_rss_keywords":
        return _run_arxiv_rss_keywords(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                keywords=source_config["keywords"],
                max_results=source_config["max_results"],
                api_base_url=source_config["api_base_url"],
                run_id=args.run_id,
                output_id=args.output_id,
            ),
            stdout,
            arxiv_collector_factory,
        )

    raise ValueError(f"unsupported source_type: {source_type}")


def _smoke_source_config(
    args: argparse.Namespace,
    stdout: TextIO,
    github_collector_factory: type[GitHubRepoCollector],
    arxiv_collector_factory: type[ArxivRssKeywordsCollector],
) -> int:
    runtime_root = _prepare_smoke_runtime_root(args.runtime_root)
    captured_stdout = io.StringIO()
    exit_code = _run_source_config(
        argparse.Namespace(
            runtime_root=str(runtime_root),
            profile=args.profile,
            source_config=args.source_config,
            run_id=args.run_id,
            output_id=args.output_id,
        ),
        captured_stdout,
        github_collector_factory,
        arxiv_collector_factory,
    )
    summary = json.loads(captured_stdout.getvalue())
    summary.update(
        {
            "smoke_runtime_root": str(runtime_root),
            "smoke_runtime_policy": "do_not_commit",
            "runtime_boundary_path": str(
                runtime_root / _SMOKE_BOUNDARY_FILENAME
            ),
        }
    )
    _print_json(stdout, summary)
    return exit_code


def _list_runs(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    manifests = []
    if paths.runs_root.exists():
        manifests = [
            _run_manifest_summary(path)
            for path in sorted(paths.runs_root.glob("*.manifest.json"))
        ]
    manifests.sort(key=lambda manifest: manifest["run_id"], reverse=True)
    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "run_count": len(manifests),
            "runs": manifests,
        },
    )
    return 0


def _list_clean_records(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    clean_records = []
    if paths.clean_root.exists():
        clean_records = [
            _clean_record_summary(path)
            for path in sorted(paths.clean_root.glob("*.json"))
        ]
    clean_records.sort(key=lambda record: record["record_id"])
    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "clean_record_count": len(clean_records),
            "clean_records": clean_records,
        },
    )
    return 0


def _inspect_record(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    clean_record_path = paths.clean_record_path(args.record_id)
    record = _read_json(clean_record_path)
    record = dict(record)
    record["clean_record_path"] = str(clean_record_path)
    _print_json(stdout, record)
    return 0


def _inspect_run(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    manifest_path = paths.run_manifest_path(args.run_id)
    manifest = _read_json(manifest_path)
    source_health = [
        _source_health_summary(Path(path)) for path in manifest["source_health"]
    ]
    _print_json(
        stdout,
        {
            "run_id": manifest["run_id"],
            "run_manifest_path": str(manifest_path),
            "mode": manifest["mode"],
            "status": manifest["status"],
            "sources": manifest["sources"],
            "counts": manifest["counts"],
            "source_health": source_health,
        },
    )
    return 0


def _show_source_health(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    source_health_path = paths.source_health_path(args.run_id, args.source_id)
    source_health = _read_json(source_health_path)
    source_health = dict(source_health)
    source_health["source_health_path"] = str(source_health_path)
    _print_json(stdout, source_health)
    return 0


def _run_manifest_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    return {
        "run_id": manifest["run_id"],
        "run_manifest_path": str(manifest_path),
        "mode": manifest["mode"],
        "status": manifest["status"],
        "started_at": manifest["started_at"],
        "finished_at": manifest["finished_at"],
        "sources": manifest["sources"],
        "counts": manifest["counts"],
        "source_health_count": len(manifest["source_health"]),
    }


def _clean_record_summary(clean_record_path: Path) -> dict[str, Any]:
    record = _read_json(clean_record_path)
    return {
        "clean_record_path": str(clean_record_path),
        "record_id": record["record_id"],
        "source_id": record["source_id"],
        "source_type": record["source_type"],
        "canonical_url": record["canonical_url"],
        "title": record["title"],
        "published_at": record.get("published_at"),
        "source_trust": record["source_trust"],
        "risk_flags": record["risk_flags"],
        "quarantined": record["quarantined"],
        "raw_hash": record["raw_hash"],
        "sanitizer_version": record["sanitizer_version"],
    }


def _source_health_summary(source_health_path: Path) -> dict[str, Any]:
    source_health = _read_json(source_health_path)
    return {
        "source_health_path": str(source_health_path),
        "source_id": source_health["source_id"],
        "source_type": source_health["source_type"],
        "status": source_health["status"],
        "degraded_reasons": source_health["degraded_reasons"],
        "last_error": source_health["last_error"],
    }


def _collection_summary(
    run_id: str,
    collection: GitHubRepoCollectionResult | ArxivRssKeywordsCollectionResult,
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


def _load_source_config(path: str | Path) -> dict[str, Any]:
    config = _read_json(Path(path))
    if config.get("schema_version") != "source-config.v1":
        raise ValueError("source config must use schema_version source-config.v1")
    _require_text(config, "source_type")
    _require_text(config, "source_id")

    source_type = config["source_type"]
    if source_type == "github_repo":
        _reject_unknown(
            config,
            {
                "schema_version",
                "source_type",
                "source_id",
                "owner",
                "repo",
                "api_base_url",
            },
        )
        _require_text(config, "owner")
        _require_text(config, "repo")
        config = dict(config)
        config.setdefault("api_base_url", "https://api.github.com")
        _require_text(config, "api_base_url")
        return config
    if source_type == "arxiv_rss_keywords":
        _reject_unknown(
            config,
            {
                "schema_version",
                "source_type",
                "source_id",
                "keywords",
                "max_results",
                "api_base_url",
            },
        )
        _require_string_list(config, "keywords")
        if not isinstance(config.get("max_results"), int):
            raise ValueError("max_results must be an integer")
        config = dict(config)
        config.setdefault("api_base_url", "https://export.arxiv.org/api/query")
        _require_text(config, "api_base_url")
        return config

    raise ValueError(f"unsupported source_type: {source_type}")


def _prepare_smoke_runtime_root(runtime_root: str | None) -> Path:
    if runtime_root is None:
        path = Path(
            tempfile.mkdtemp(prefix="shared-intake-governance-smoke-")
        ).resolve()
    else:
        path = Path(runtime_root).expanduser().resolve()
        if _is_relative_to(path, _repo_root()):
            raise ValueError("smoke runtime root must be outside the repository")
        path.mkdir(parents=True, exist_ok=True)

    boundary_path = path / _SMOKE_BOUNDARY_FILENAME
    boundary_path.write_text(
        "Smoke runtime data only. Do not commit this directory.\n",
        encoding="utf-8",
    )
    return path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _reject_unknown(config: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(config) - allowed)
    if unknown:
        raise ValueError(f"source config has unknown fields: {', '.join(unknown)}")


def _require_text(config: dict[str, Any], field: str) -> None:
    if not isinstance(config.get(field), str) or not config[field]:
        raise ValueError(f"{field} must be a non-empty string")


def _require_string_list(config: dict[str, Any], field: str) -> None:
    if not isinstance(config.get(field), list) or not all(
        isinstance(item, str) and item for item in config[field]
    ):
        raise ValueError(f"{field} must be a list of non-empty strings")


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

    arxiv = subparsers.add_parser(
        "run-arxiv-rss-keywords",
        help=(
            "Collect one arXiv keyword feed, emit clean records, and project "
            "one profile."
        ),
    )
    arxiv.add_argument("--runtime-root", required=True)
    arxiv.add_argument("--profile", required=True)
    arxiv.add_argument("--source-id", required=True)
    arxiv.add_argument("--keyword", dest="keywords", action="append", required=True)
    arxiv.add_argument("--max-results", required=True, type=int)
    arxiv.add_argument("--run-id")
    arxiv.add_argument("--output-id")
    arxiv.add_argument(
        "--api-base-url", default="https://export.arxiv.org/api/query"
    )

    source_config = subparsers.add_parser(
        "run-source-config",
        help="Run one source from a source-config.v1 JSON file.",
    )
    source_config.add_argument("--runtime-root", required=True)
    source_config.add_argument("--profile", required=True)
    source_config.add_argument("--source-config", required=True)
    source_config.add_argument("--run-id")
    source_config.add_argument("--output-id")

    smoke = subparsers.add_parser(
        "smoke-source-config",
        help=(
            "Run one source-config.v1 smoke with runtime data outside the "
            "repository."
        ),
    )
    smoke.add_argument("--runtime-root")
    smoke.add_argument("--profile", required=True)
    smoke.add_argument("--source-config", required=True)
    smoke.add_argument("--run-id")
    smoke.add_argument("--output-id")

    list_runs = subparsers.add_parser(
        "list-runs",
        help="List run manifests under one runtime root.",
    )
    list_runs.add_argument("--runtime-root", required=True)

    list_clean_records = subparsers.add_parser(
        "list-clean-records",
        help="List clean records under one runtime root.",
    )
    list_clean_records.add_argument("--runtime-root", required=True)

    inspect_record = subparsers.add_parser(
        "inspect-record",
        help="Read one clean record.",
    )
    inspect_record.add_argument("--runtime-root", required=True)
    inspect_record.add_argument("--record-id", required=True)

    inspect_run = subparsers.add_parser(
        "inspect-run",
        help="Read one run manifest and summarize source health.",
    )
    inspect_run.add_argument("--runtime-root", required=True)
    inspect_run.add_argument("--run-id", required=True)

    source_health = subparsers.add_parser(
        "show-source-health",
        help="Read one source-health artifact.",
    )
    source_health.add_argument("--runtime-root", required=True)
    source_health.add_argument("--run-id", required=True)
    source_health.add_argument("--source-id", required=True)
    return parser
