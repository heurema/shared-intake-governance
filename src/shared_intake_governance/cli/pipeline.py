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

from shared_intake_governance.collector.arxiv_query import (
    ArxivQueryCollectionResult,
    ArxivQueryCollector,
    ArxivQuerySource,
)
from shared_intake_governance.collector.github_repo import (
    GitHubRepoCollectionResult,
    GitHubRepoCollector,
    GitHubRepoSource,
)
from shared_intake_governance.collector.github_releases import (
    GitHubReleasesCollector,
    GitHubReleasesSource,
)
from shared_intake_governance.collector.github_search import (
    GitHubSearchCollectionResult,
    GitHubSearchCollector,
    GitHubSearchSource,
)
from shared_intake_governance.collector.news_feed import (
    NewsFeedCollectionResult,
    NewsFeedCollector,
    NewsFeedSource,
)
from shared_intake_governance.collector.rss_feed import (
    RssFeedCollectionResult,
    RssFeedCollector,
    RssFeedSource,
)
from shared_intake_governance.adapters import (
    invoke_provider_request,
    prepare_provider_request,
    record_provider_result,
)
from shared_intake_governance.governance import (
    evaluate_tool_intent,
    mediate_tool_intent,
    validate_governance_decision,
    validate_tool_intent,
)
from shared_intake_governance.executor import execute_tool_intent
from shared_intake_governance.provider_presets import (
    provider_preset_ids,
    resolve_provider_preset,
)
from shared_intake_governance.projector import (
    ProfileProjector,
    load_seen_records_state,
    load_profile,
    update_seen_records_state,
    validate_profile_projection,
    validate_profile_state,
)
from shared_intake_governance.runtime import (
    AuditWriter,
    ApprovalWriter,
    DryRunWriter,
    MediationWriter,
    ProviderRequestWriter,
    ProviderResultWriter,
    RunWriter,
    RuntimePaths,
    SourceHealthWriter,
    ToolExecutionWriter,
    generate_run_id,
    validate_execution_mediation,
    validate_run_manifest,
    validate_source_health,
)
from shared_intake_governance.sanitizer import CleanRecordEmitter, validate_clean_record
from shared_intake_governance.source_config import (
    inspect_source_config,
    list_source_configs,
    load_source_config,
)
from shared_intake_governance.source_set import inspect_source_set


_SMOKE_BOUNDARY_FILENAME = "SMOKE_RUNTIME_DO_NOT_COMMIT.txt"


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    collector_factory: type[GitHubRepoCollector] = GitHubRepoCollector,
    github_releases_collector_factory: type[GitHubReleasesCollector] = (
        GitHubReleasesCollector
    ),
    github_search_collector_factory: type[GitHubSearchCollector] = (
        GitHubSearchCollector
    ),
    arxiv_query_collector_factory: type[ArxivQueryCollector] = ArxivQueryCollector,
    rss_collector_factory: type[RssFeedCollector] = RssFeedCollector,
    news_collector_factory: type[NewsFeedCollector] = NewsFeedCollector,
) -> int:
    args = _parser().parse_args(argv)
    stdout = stdout or sys.stdout

    if args.command == "run-github-repo":
        return _run_github_repo(args, stdout, collector_factory)
    if args.command == "run-github-releases":
        return _run_github_releases(args, stdout, github_releases_collector_factory)
    if args.command == "run-github-search":
        return _run_github_search(args, stdout, github_search_collector_factory)
    if args.command == "run-arxiv-query":
        return _run_arxiv_query(args, stdout, arxiv_query_collector_factory)
    if args.command == "run-rss-feed":
        return _run_rss_feed(args, stdout, rss_collector_factory)
    if args.command == "run-news-feed":
        return _run_news_feed(args, stdout, news_collector_factory)
    if args.command == "run-source-config":
        return _run_source_config(
            args,
            stdout,
            collector_factory,
            github_releases_collector_factory,
            github_search_collector_factory,
            arxiv_query_collector_factory,
            rss_collector_factory,
            news_collector_factory,
        )
    if args.command == "smoke-source-config":
        return _smoke_source_config(
            args,
            stdout,
            collector_factory,
            github_releases_collector_factory,
            github_search_collector_factory,
            arxiv_query_collector_factory,
            rss_collector_factory,
            news_collector_factory,
        )
    if args.command == "list-source-configs":
        return _list_source_configs(args, stdout)
    if args.command == "inspect-source-config":
        return _inspect_source_config(args, stdout)
    if args.command == "inspect-source-set":
        return _inspect_source_set(args, stdout)
    if args.command == "project-profiles":
        return _project_profiles(args, stdout)
    if args.command == "list-runs":
        return _list_runs(args, stdout)
    if args.command == "list-clean-records":
        return _list_clean_records(args, stdout)
    if args.command == "inspect-record":
        return _inspect_record(args, stdout)
    if args.command == "list-profile-state":
        return _list_profile_state(args, stdout)
    if args.command == "inspect-profile-state":
        return _inspect_profile_state(args, stdout)
    if args.command == "update-profile-seen-state":
        return _update_profile_seen_state(args, stdout)
    if args.command == "list-profile-reports":
        return _list_profile_reports(args, stdout)
    if args.command == "inspect-profile-report":
        return _inspect_profile_report(args, stdout)
    if args.command == "evaluate-tool-intent":
        return _evaluate_tool_intent(args, stdout)
    if args.command == "record-approval":
        return _record_approval(args, stdout)
    if args.command == "record-dry-run":
        return _record_dry_run(args, stdout)
    if args.command == "mediate-tool-intent":
        return _mediate_tool_intent(args, stdout)
    if args.command == "list-mediation-records":
        return _list_mediation_records(args, stdout)
    if args.command == "inspect-mediation-record":
        return _inspect_mediation_record(args, stdout)
    if args.command == "execute-tool-intent":
        return _execute_tool_intent(args, stdout)
    if args.command == "list-provider-presets":
        return _list_provider_presets(stdout)
    if args.command == "inspect-provider-preset":
        return _inspect_provider_preset(args, stdout)
    if args.command == "prepare-provider-request":
        return _prepare_provider_request(args, stdout)
    if args.command == "record-provider-result":
        return _record_provider_result(args, stdout)
    if args.command == "invoke-provider-request":
        return _invoke_provider_request(args, stdout)
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_github_search(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[GitHubSearchCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = GitHubSearchSource(
        source_id=args.source_id,
        query=args.query,
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_github_releases(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[GitHubReleasesCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = GitHubReleasesSource(
        source_id=args.source_id,
        owner=args.owner,
        repo=args.repo,
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_arxiv_query(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[ArxivQueryCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = ArxivQuerySource(
        source_id=args.source_id,
        query=args.query,
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_rss_feed(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[RssFeedCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = RssFeedSource(
        source_id=args.source_id,
        feed_url=args.feed_url,
        source_trust=args.source_trust,
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
            "run_manifest_path": str(evidence["run_manifest_path"]),
            "source_health_path": str(evidence["source_health_path"]),
        }
    )
    _print_json(stdout, summary)
    return 0


def _run_news_feed(
    args: argparse.Namespace,
    stdout: TextIO,
    collector_factory: type[NewsFeedCollector],
) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    run_id = args.run_id or generate_run_id()
    output_id = args.output_id or run_id
    started_at = _format_utc(datetime.now(timezone.utc))
    source = NewsFeedSource(
        source_id=args.source_id,
        feed_url=args.feed_url,
        source_trust=args.source_trust,
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
    projection = _project_profile(paths, args, output_id)
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
            "excluded_seen": projection.report["counts"]["excluded_seen"],
            **_maybe_update_seen_state_summary(paths, args, projection),
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
    github_releases_collector_factory: type[GitHubReleasesCollector],
    github_search_collector_factory: type[GitHubSearchCollector],
    arxiv_query_collector_factory: type[ArxivQueryCollector],
    rss_collector_factory: type[RssFeedCollector],
    news_collector_factory: type[NewsFeedCollector],
) -> int:
    source_config = load_source_config(args.source_config)
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
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            github_collector_factory,
        )
    if source_type == "github_releases":
        return _run_github_releases(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                owner=source_config["owner"],
                repo=source_config["repo"],
                max_results=source_config["max_results"],
                api_base_url=source_config["api_base_url"],
                run_id=args.run_id,
                output_id=args.output_id,
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            github_releases_collector_factory,
        )
    if source_type == "github_search":
        return _run_github_search(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                query=source_config["query"],
                max_results=source_config["max_results"],
                api_base_url=source_config["api_base_url"],
                run_id=args.run_id,
                output_id=args.output_id,
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            github_search_collector_factory,
        )
    if source_type == "arxiv_query":
        return _run_arxiv_query(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                query=source_config["query"],
                max_results=source_config["max_results"],
                api_base_url=source_config["api_base_url"],
                run_id=args.run_id,
                output_id=args.output_id,
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            arxiv_query_collector_factory,
        )
    if source_type == "rss":
        return _run_rss_feed(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                feed_url=source_config["feed_url"],
                source_trust=source_config["source_trust"],
                run_id=args.run_id,
                output_id=args.output_id,
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            rss_collector_factory,
        )
    if source_type == "news":
        return _run_news_feed(
            argparse.Namespace(
                runtime_root=args.runtime_root,
                profile=args.profile,
                source_id=source_config["source_id"],
                feed_url=source_config["feed_url"],
                source_trust=source_config["source_trust"],
                run_id=args.run_id,
                output_id=args.output_id,
                exclude_seen_state=args.exclude_seen_state,
                update_seen_state=args.update_seen_state,
                state_id=args.state_id,
            ),
            stdout,
            news_collector_factory,
        )

    raise ValueError(f"unsupported source_type: {source_type}")


def _project_profile(
    paths: RuntimePaths,
    args: argparse.Namespace,
    output_id: str,
) -> Any:
    profile_path = Path(args.profile)
    profile = load_profile(profile_path)
    exclude_record_ids: set[str] = set()
    if getattr(args, "exclude_seen_state", False):
        state_id = getattr(args, "state_id", "seen-records")
        seen_state = load_seen_records_state(
            paths=paths,
            profile_id=profile["profile_id"],
            state_id=state_id,
        )
        if seen_state is not None:
            exclude_record_ids = set(seen_state.state["record_ids"])
    return ProfileProjector(paths).project(
        profile_path,
        output_id=output_id,
        exclude_record_ids=exclude_record_ids,
    )


def _maybe_update_seen_state_summary(
    paths: RuntimePaths,
    args: argparse.Namespace,
    projection: Any,
) -> dict[str, Any]:
    if not getattr(args, "update_seen_state", False):
        return {}

    state_id = getattr(args, "state_id", "seen-records")
    profile_state = update_seen_records_state(
        paths=paths,
        profile_id=projection.report["profile_id"],
        profile_report=projection.report,
        state_id=state_id,
        updated_at=projection.report["generated_at"],
    )
    return {
        "profile_state_id": state_id,
        "profile_state_path": str(profile_state.path),
        "profile_state_record_count": len(profile_state.state["record_ids"]),
    }


def _smoke_source_config(
    args: argparse.Namespace,
    stdout: TextIO,
    github_collector_factory: type[GitHubRepoCollector],
    github_releases_collector_factory: type[GitHubReleasesCollector],
    github_search_collector_factory: type[GitHubSearchCollector],
    arxiv_query_collector_factory: type[ArxivQueryCollector],
    rss_collector_factory: type[RssFeedCollector],
    news_collector_factory: type[NewsFeedCollector],
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
            exclude_seen_state=args.exclude_seen_state,
            update_seen_state=args.update_seen_state,
            state_id=args.state_id,
        ),
        captured_stdout,
        github_collector_factory,
        github_releases_collector_factory,
        github_search_collector_factory,
        arxiv_query_collector_factory,
        rss_collector_factory,
        news_collector_factory,
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


def _project_profiles(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    output_id = args.output_id or generate_run_id()
    generated_at = datetime.now(timezone.utc)
    profile_paths = [Path(path) for path in args.profiles]
    for profile_path in profile_paths:
        load_profile(profile_path)

    projections = []
    projector = ProfileProjector(paths)
    for profile_path in profile_paths:
        profile = load_profile(profile_path)
        exclude_record_ids: set[str] = set()
        if args.exclude_seen_state:
            seen_state = load_seen_records_state(
                paths=paths,
                profile_id=profile["profile_id"],
                state_id=args.state_id,
            )
            if seen_state is not None:
                exclude_record_ids = set(seen_state.state["record_ids"])
        projection = projector.project(
            profile_path,
            output_id=output_id,
            generated_at=generated_at,
            exclude_record_ids=exclude_record_ids,
        )
        projection_summary = {
            "profile_id": projection.report["profile_id"],
            "output_mode": projection.report["output_mode"],
            "projection_path": str(projection.path),
            "clean_records_seen": projection.report["counts"][
                "clean_records_seen"
            ],
            "items_written": projection.report["counts"]["items_written"],
            "excluded_seen": projection.report["counts"]["excluded_seen"],
        }
        if args.update_seen_state:
            profile_state = update_seen_records_state(
                paths=paths,
                profile_id=projection.report["profile_id"],
                profile_report=projection.report,
                state_id=args.state_id,
                updated_at=projection.report["generated_at"],
            )
            projection_summary.update(
                {
                    "profile_state_id": args.state_id,
                    "profile_state_path": str(profile_state.path),
                    "profile_state_record_count": len(
                        profile_state.state["record_ids"]
                    ),
                }
            )
        projections.append(projection_summary)

    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "output_id": output_id,
            "profile_count": len(projections),
            "projections": projections,
        },
    )
    return 0


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
    validate_clean_record(record)
    record = dict(record)
    record["clean_record_path"] = str(clean_record_path)
    _print_json(stdout, record)
    return 0


def _list_profile_state(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    if args.profile_id:
        state_paths = sorted(paths.profile_state_dir(args.profile_id).glob("*.json"))
    elif paths.profiles_root.exists():
        state_paths = sorted(paths.profiles_root.glob("*/state/*.json"))
    else:
        state_paths = []

    states = [_profile_state_summary(path) for path in state_paths]
    states.sort(key=lambda state: (state["profile_id"], state["state_id"]))
    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "profile_state_count": len(states),
            "profile_states": states,
        },
    )
    return 0


def _inspect_profile_state(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    state_path = paths.profile_state_path(args.profile_id, args.state_id)
    state = _read_json(state_path)
    validate_profile_state(state)
    state = dict(state)
    state["profile_state_path"] = str(state_path)
    _print_json(stdout, state)
    return 0


def _update_profile_seen_state(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    profile_report_path = Path(args.profile_report)
    profile_report = _read_json(profile_report_path)
    result = update_seen_records_state(
        paths=paths,
        profile_id=args.profile_id,
        profile_report=profile_report,
        state_id=args.state_id,
        updated_at=_format_utc(datetime.now(timezone.utc)),
    )
    _print_json(
        stdout,
        {
            "profile_state_path": str(result.path),
            "profile_state": result.state,
        },
    )
    return 0


def _list_profile_reports(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    if args.profile_id:
        report_paths = sorted(paths.profile_reports_dir(args.profile_id).glob("*.json"))
    elif paths.profiles_root.exists():
        report_paths = sorted(paths.profiles_root.glob("*/reports/*.json"))
    else:
        report_paths = []

    reports = [_profile_report_summary(path) for path in report_paths]
    reports.sort(key=lambda report: (report["profile_id"], report["output_id"]))
    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "profile_report_count": len(reports),
            "profile_reports": reports,
        },
    )
    return 0


def _inspect_profile_report(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    report_path = paths.profile_report_path(args.profile_id, args.output_id)
    report = _read_json(report_path)
    validate_profile_projection(report)
    report = dict(report)
    report["profile_report_path"] = str(report_path)
    _print_json(stdout, report)
    return 0


def _evaluate_tool_intent(args: argparse.Namespace, stdout: TextIO) -> int:
    intent_path = Path(args.intent)
    intent = _read_json(intent_path)
    decision = evaluate_tool_intent(intent)
    decision = dict(decision)
    decision["tool_intent_path"] = str(intent_path)
    if bool(args.runtime_root) != bool(args.run_id):
        raise ValueError("runtime-root and run-id must be provided together")
    if args.runtime_root:
        paths = RuntimePaths(Path(args.runtime_root))
        event = _governance_audit_event(
            run_id=args.run_id,
            decision=decision,
            tool_intent_path=str(intent_path),
        )
        audit_log_path = AuditWriter(paths).write_event(event)
        decision["audit_log_path"] = str(audit_log_path)
        decision["audit_event"] = event
    validate_governance_decision(decision)
    _print_json(stdout, decision)
    return 0


def _governance_audit_event(
    *,
    run_id: str,
    decision: dict[str, Any],
    tool_intent_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": "governance-audit-event.v1",
        "run_id": run_id,
        "event_type": "tool_intent_evaluated",
        "recorded_at": _format_utc(datetime.now(timezone.utc)),
        "intent_id": decision["intent_id"],
        "profile_id": decision["profile_id"],
        "action_class": decision["action_class"],
        "tool_name": decision["tool_name"],
        "decision": decision["decision"],
        "reason": decision["reason"],
        "dry_run_supported": decision["dry_run_supported"],
        "evidence_refs": decision["evidence_refs"],
        "tool_intent_path": tool_intent_path,
    }


def _record_approval(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    intent_path = Path(args.intent)
    intent = _read_json(intent_path)
    validate_tool_intent(intent)
    record = _approval_record(
        run_id=args.run_id,
        approval_id=args.approval_id,
        intent=intent,
        approval_decision=args.approval_decision,
        approved_by=args.approved_by,
        justification=args.justification,
        dry_run_ref=args.dry_run_ref,
        tool_intent_path=str(intent_path),
    )
    approval_record_path = ApprovalWriter(paths).write_record(record)
    _print_json(
        stdout,
        {
            "approval_record_path": str(approval_record_path),
            "approval_record": record,
        },
    )
    return 0


def _approval_record(
    *,
    run_id: str,
    approval_id: str,
    intent: dict[str, Any],
    approval_decision: str,
    approved_by: str,
    justification: str,
    dry_run_ref: str | None,
    tool_intent_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": "approval-record.v1",
        "run_id": run_id,
        "approval_id": approval_id,
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": intent["action_class"],
        "tool_name": intent["tool_name"],
        "approval_decision": approval_decision,
        "approved_by": approved_by,
        "approved_at": _format_utc(datetime.now(timezone.utc)),
        "justification": justification,
        "dry_run_ref": dry_run_ref,
        "evidence_refs": intent["evidence_refs"],
        "tool_intent_path": tool_intent_path,
    }


def _record_dry_run(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    intent_path = Path(args.intent)
    intent = _read_json(intent_path)
    validate_tool_intent(intent)
    result = _dry_run_result(
        run_id=args.run_id,
        dry_run_id=args.dry_run_id,
        intent=intent,
        dry_run_kind=args.dry_run_kind,
        result_status=args.result_status,
        recorded_by=args.recorded_by,
        summary=args.summary,
        artifact_refs=args.artifact_refs or [],
        tool_intent_path=str(intent_path),
    )
    dry_run_result_path = DryRunWriter(paths).write_result(result)
    _print_json(
        stdout,
        {
            "dry_run_result_path": str(dry_run_result_path),
            "dry_run_result": result,
        },
    )
    return 0


def _mediate_tool_intent(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    intent_path = Path(args.intent)
    dry_run_result_path = None if args.dry_run_result is None else Path(args.dry_run_result)
    approval_record_path = (
        None if args.approval_record is None else Path(args.approval_record)
    )
    intent = _read_json(intent_path)
    dry_run_result = (
        None if dry_run_result_path is None else _read_json(dry_run_result_path)
    )
    approval_record = (
        None if approval_record_path is None else _read_json(approval_record_path)
    )
    record = mediate_tool_intent(
        run_id=args.run_id,
        mediation_id=args.mediation_id,
        intent=intent,
        tool_intent_path=str(intent_path),
        dry_run_result=dry_run_result,
        dry_run_result_path=(
            None if dry_run_result_path is None else str(dry_run_result_path)
        ),
        approval_record=approval_record,
        approval_record_path=(
            None if approval_record_path is None else str(approval_record_path)
        ),
        mediated_at=_format_utc(datetime.now(timezone.utc)),
    )
    mediation_record_path = MediationWriter(paths).write_record(record)
    _print_json(
        stdout,
        {
            "mediation_record_path": str(mediation_record_path),
            "mediation_record": record,
        },
    )
    return 0


def _list_mediation_records(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    if args.run_id:
        mediation_dir = paths.mediation_record_path(args.run_id, "probe").parent
        record_paths = sorted(mediation_dir.glob("*.json"))
    elif paths.mediation_root.exists():
        record_paths = sorted(paths.mediation_root.glob("*/*.json"))
    else:
        record_paths = []

    records = [_mediation_record_summary(path) for path in record_paths]
    records.sort(key=lambda record: (record["run_id"], record["mediation_id"]))
    _print_json(
        stdout,
        {
            "runtime_root": str(paths.root),
            "mediation_record_count": len(records),
            "mediation_records": records,
        },
    )
    return 0


def _inspect_mediation_record(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    record_path = paths.mediation_record_path(args.run_id, args.mediation_id)
    record = _read_json(record_path)
    validate_execution_mediation(record)
    record = dict(record)
    record["mediation_record_path"] = str(record_path)
    _print_json(stdout, record)
    return 0


def _execute_tool_intent(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    tool_intent_path = Path(args.intent)
    mediation_record_path = Path(args.mediation_record)
    intent = _read_json(tool_intent_path)
    mediation_record = _read_json(mediation_record_path)
    result = execute_tool_intent(
        paths=paths,
        run_id=args.run_id,
        execution_id=args.execution_id,
        intent=intent,
        tool_intent_path=str(tool_intent_path),
        mediation_record=mediation_record,
        mediation_record_path=str(mediation_record_path),
        command=[args.tool_command] + (args.tool_args or []),
        executed_by=args.executed_by,
        timeout_seconds=args.timeout_seconds,
        execution_metadata=_execution_metadata(args.metadata_keys or []),
        executed_at=_format_utc(datetime.now(timezone.utc)),
    )
    result_path = ToolExecutionWriter(paths).write_result(result)
    _print_json(
        stdout,
        {
            "tool_execution_result_path": str(result_path),
            "tool_execution_result": result,
        },
    )
    return 0 if result["execution_status"] == "succeeded" else 1


def _prepare_provider_request(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    mediation_record_path = Path(args.mediation_record)
    mediation_record = _read_json(mediation_record_path)
    request = prepare_provider_request(
        run_id=args.run_id,
        request_id=args.request_id,
        preset_id=args.preset_id,
        mediation_record=mediation_record,
        mediation_record_path=str(mediation_record_path),
        context_refs=args.context_refs or [],
        prepared_at=_format_utc(datetime.now(timezone.utc)),
    )
    provider_request_path = ProviderRequestWriter(paths).write_request(request)
    _print_json(
        stdout,
        {
            "provider_request_path": str(provider_request_path),
            "provider_request": request,
        },
    )
    return 0


def _list_provider_presets(stdout: TextIO) -> int:
    presets = [
        resolve_provider_preset(preset_id) for preset_id in provider_preset_ids()
    ]
    _print_json(
        stdout,
        {
            "provider_preset_count": len(presets),
            "provider_presets": presets,
        },
    )
    return 0


def _inspect_provider_preset(args: argparse.Namespace, stdout: TextIO) -> int:
    _print_json(
        stdout,
        {
            "provider_preset": resolve_provider_preset(args.preset_id),
        },
    )
    return 0


def _list_source_configs(args: argparse.Namespace, stdout: TextIO) -> int:
    _print_json(stdout, list_source_configs(args.repo_root))
    return 0


def _inspect_source_config(args: argparse.Namespace, stdout: TextIO) -> int:
    _print_json(stdout, inspect_source_config(args.source_config))
    return 0


def _inspect_source_set(args: argparse.Namespace, stdout: TextIO) -> int:
    _print_json(
        stdout,
        inspect_source_set(
            args.source_set,
            repo_root=args.repo_root,
        ),
    )
    return 0


def _record_provider_result(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    provider_request_path = Path(args.provider_request)
    provider_request = _read_json(provider_request_path)
    error = _provider_error(args.error_kind, args.error_message)
    result = record_provider_result(
        run_id=args.run_id,
        result_id=args.result_id,
        provider_request=provider_request,
        provider_request_path=str(provider_request_path),
        result_status=args.result_status,
        recorded_by=args.recorded_by,
        summary=args.summary,
        response_refs=args.response_refs or [],
        usage_metadata=_usage_metadata(args.usage_keys or []),
        error=error,
        recorded_at=_format_utc(datetime.now(timezone.utc)),
    )
    provider_result_path = ProviderResultWriter(paths).write_result(result)
    _print_json(
        stdout,
        {
            "provider_result_path": str(provider_result_path),
            "provider_result": result,
        },
    )
    return 0


def _invoke_provider_request(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    provider_request_path = Path(args.provider_request)
    provider_request = _read_json(provider_request_path)
    result = invoke_provider_request(
        paths=paths,
        run_id=args.run_id,
        result_id=args.result_id,
        provider_request=provider_request,
        provider_request_path=str(provider_request_path),
        recorded_by=args.recorded_by,
        timeout_seconds=args.timeout_seconds,
        usage_metadata=_usage_metadata(args.usage_keys or []),
        recorded_at=_format_utc(datetime.now(timezone.utc)),
    )
    provider_result_path = ProviderResultWriter(paths).write_result(result)
    _print_json(
        stdout,
        {
            "provider_result_path": str(provider_result_path),
            "provider_result": result,
        },
    )
    return 0 if result["result_status"] == "succeeded" else 1


def _dry_run_result(
    *,
    run_id: str,
    dry_run_id: str,
    intent: dict[str, Any],
    dry_run_kind: str,
    result_status: str,
    recorded_by: str,
    summary: str,
    artifact_refs: list[str],
    tool_intent_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": "dry-run-result.v1",
        "run_id": run_id,
        "dry_run_id": dry_run_id,
        "intent_id": intent["intent_id"],
        "profile_id": intent["profile_id"],
        "action_class": intent["action_class"],
        "tool_name": intent["tool_name"],
        "dry_run_kind": dry_run_kind,
        "result_status": result_status,
        "recorded_by": recorded_by,
        "recorded_at": _format_utc(datetime.now(timezone.utc)),
        "summary": summary,
        "artifact_refs": artifact_refs,
        "evidence_refs": intent["evidence_refs"],
        "tool_intent_path": tool_intent_path,
    }


def _inspect_run(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    manifest_path = paths.run_manifest_path(args.run_id)
    manifest = _read_json(manifest_path)
    validate_run_manifest(manifest)
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
    validate_source_health(source_health)
    source_health = dict(source_health)
    source_health["source_health_path"] = str(source_health_path)
    _print_json(stdout, source_health)
    return 0


def _run_manifest_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    validate_run_manifest(manifest)
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
    validate_clean_record(record)
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


def _profile_report_summary(profile_report_path: Path) -> dict[str, Any]:
    report = _read_json(profile_report_path)
    validate_profile_projection(report)
    return {
        "profile_id": report["profile_id"],
        "output_id": profile_report_path.stem,
        "profile_report_path": str(profile_report_path),
        "output_mode": report["output_mode"],
        "generated_at": report["generated_at"],
        "clean_records_seen": report["counts"]["clean_records_seen"],
        "items_written": report["counts"]["items_written"],
    }


def _profile_state_summary(profile_state_path: Path) -> dict[str, Any]:
    state = _read_json(profile_state_path)
    validate_profile_state(state)
    record_ids = state["record_ids"]
    if not isinstance(record_ids, list):
        raise ValueError("profile state record_ids must be a list")
    return {
        "profile_id": state["profile_id"],
        "state_id": state["state_id"],
        "profile_state_path": str(profile_state_path),
        "state_kind": state["state_kind"],
        "updated_at": state["updated_at"],
        "record_count": len(record_ids),
    }


def _source_health_summary(source_health_path: Path) -> dict[str, Any]:
    source_health = _read_json(source_health_path)
    validate_source_health(source_health)
    return {
        "source_health_path": str(source_health_path),
        "source_id": source_health["source_id"],
        "source_type": source_health["source_type"],
        "status": source_health["status"],
        "degraded_reasons": source_health["degraded_reasons"],
        "last_error": source_health["last_error"],
    }


def _mediation_record_summary(record_path: Path) -> dict[str, Any]:
    record = _read_json(record_path)
    validate_execution_mediation(record)
    return {
        "mediation_record_path": str(record_path),
        "run_id": record["run_id"],
        "mediation_id": record["mediation_id"],
        "mediated_at": record["mediated_at"],
        "intent_id": record["intent_id"],
        "profile_id": record["profile_id"],
        "action_class": record["action_class"],
        "tool_name": record["tool_name"],
        "policy_decision": record["policy_decision"],
        "mediation_decision": record["mediation_decision"],
        "reason": record["reason"],
        "dry_run_result_path": record["dry_run_result_path"],
        "approval_record_path": record["approval_record_path"],
        "tool_intent_path": record["tool_intent_path"],
    }


def _collection_summary(
    run_id: str,
    collection: (
        GitHubRepoCollectionResult
        | GitHubSearchCollectionResult
        | ArxivQueryCollectionResult
        | RssFeedCollectionResult
        | NewsFeedCollectionResult
    ),
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


def _usage_metadata(items: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key or not value:
            raise ValueError("usage-key must use key=value")
        metadata[key] = value
    return metadata


def _execution_metadata(items: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key or not value:
            raise ValueError("metadata-key must use key=value")
        metadata[key] = value
    return metadata


def _provider_error(kind: str | None, message: str | None) -> dict[str, str] | None:
    if kind is None and message is None:
        return None
    if not kind or not message:
        raise ValueError("provider error requires both kind and message")
    return {"kind": kind, "message": message}


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

    github_releases = subparsers.add_parser(
        "run-github-releases",
        help=(
            "Collect GitHub releases, emit clean records, and project one "
            "profile."
        ),
    )
    github_releases.add_argument("--runtime-root", required=True)
    github_releases.add_argument("--profile", required=True)
    github_releases.add_argument("--source-id", required=True)
    github_releases.add_argument("--owner", required=True)
    github_releases.add_argument("--repo", required=True)
    github_releases.add_argument("--max-results", required=True, type=int)
    github_releases.add_argument("--run-id")
    github_releases.add_argument("--output-id")
    github_releases.add_argument("--api-base-url", default="https://api.github.com")

    github_search = subparsers.add_parser(
        "run-github-search",
        help=(
            "Collect one GitHub repository search, emit clean records, and "
            "project one profile."
        ),
    )
    github_search.add_argument("--runtime-root", required=True)
    github_search.add_argument("--profile", required=True)
    github_search.add_argument("--source-id", required=True)
    github_search.add_argument("--query", required=True)
    github_search.add_argument("--max-results", required=True, type=int)
    github_search.add_argument("--run-id")
    github_search.add_argument("--output-id")
    github_search.add_argument("--api-base-url", default="https://api.github.com")

    arxiv_query = subparsers.add_parser(
        "run-arxiv-query",
        help=(
            "Collect one explicit arXiv query, emit clean records, and project "
            "one profile."
        ),
    )
    arxiv_query.add_argument("--runtime-root", required=True)
    arxiv_query.add_argument("--profile", required=True)
    arxiv_query.add_argument("--source-id", required=True)
    arxiv_query.add_argument("--query", required=True)
    arxiv_query.add_argument("--max-results", required=True, type=int)
    arxiv_query.add_argument("--run-id")
    arxiv_query.add_argument("--output-id")
    arxiv_query.add_argument(
        "--api-base-url", default="https://export.arxiv.org/api/query"
    )

    rss = subparsers.add_parser(
        "run-rss-feed",
        help="Collect one RSS feed, emit clean records, and project one profile.",
    )
    rss.add_argument("--runtime-root", required=True)
    rss.add_argument("--profile", required=True)
    rss.add_argument("--source-id", required=True)
    rss.add_argument("--feed-url", required=True)
    rss.add_argument("--source-trust", default="secondary")
    rss.add_argument("--run-id")
    rss.add_argument("--output-id")

    news = subparsers.add_parser(
        "run-news-feed",
        help="Collect one news feed, emit clean records, and project one profile.",
    )
    news.add_argument("--runtime-root", required=True)
    news.add_argument("--profile", required=True)
    news.add_argument("--source-id", required=True)
    news.add_argument("--feed-url", required=True)
    news.add_argument("--source-trust", default="secondary")
    news.add_argument("--run-id")
    news.add_argument("--output-id")

    source_config = subparsers.add_parser(
        "run-source-config",
        help="Run one source from a source-config.v1 JSON file.",
    )
    source_config.add_argument("--runtime-root", required=True)
    source_config.add_argument("--profile", required=True)
    source_config.add_argument("--source-config", required=True)
    source_config.add_argument("--run-id")
    source_config.add_argument("--output-id")
    source_config.add_argument(
        "--exclude-seen-state",
        action="store_true",
        help="Exclude records already present in profile-local seen state.",
    )
    source_config.add_argument(
        "--update-seen-state",
        action="store_true",
        help="Explicitly merge projected item IDs into profile-local seen state.",
    )
    source_config.add_argument(
        "--state-id",
        default="seen-records",
        help="Profile state id to read or update when seen-state flags are set.",
    )

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
    smoke.add_argument(
        "--exclude-seen-state",
        action="store_true",
        help="Exclude records already present in profile-local seen state.",
    )
    smoke.add_argument(
        "--update-seen-state",
        action="store_true",
        help="Explicitly merge projected item IDs into profile-local seen state.",
    )
    smoke.add_argument(
        "--state-id",
        default="seen-records",
        help="Profile state id to read or update when seen-state flags are set.",
    )

    list_source_configs_parser = subparsers.add_parser(
        "list-source-configs",
        help="List tracked source-config.v1 files without running them.",
    )
    list_source_configs_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to find sources/examples/*.json.",
    )

    inspect_source_config_parser = subparsers.add_parser(
        "inspect-source-config",
        help="Validate one source-config.v1 file without running it.",
    )
    inspect_source_config_parser.add_argument("--source-config", required=True)

    inspect_source_set_parser = subparsers.add_parser(
        "inspect-source-set",
        help="Validate one source-set.v1 file and its source-config refs.",
    )
    inspect_source_set_parser.add_argument("--source-set", required=True)
    inspect_source_set_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to resolve source_config_path refs.",
    )

    project_profiles = subparsers.add_parser(
        "project-profiles",
        help="Project multiple profiles from the existing clean cache.",
    )
    project_profiles.add_argument("--runtime-root", required=True)
    project_profiles.add_argument(
        "--profile", dest="profiles", action="append", required=True
    )
    project_profiles.add_argument("--output-id")
    project_profiles.add_argument(
        "--update-seen-state",
        action="store_true",
        help="Explicitly merge projected item IDs into profile-local seen state.",
    )
    project_profiles.add_argument(
        "--exclude-seen-state",
        action="store_true",
        help="Exclude records already present in profile-local seen state.",
    )
    project_profiles.add_argument(
        "--state-id",
        default="seen-records",
        help=(
            "Profile state id to read or update when seen-state flags are set."
        ),
    )

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

    list_profile_state = subparsers.add_parser(
        "list-profile-state",
        help="List profile state artifacts under one runtime root.",
    )
    list_profile_state.add_argument("--runtime-root", required=True)
    list_profile_state.add_argument("--profile-id")

    inspect_profile_state = subparsers.add_parser(
        "inspect-profile-state",
        help="Read one profile state artifact.",
    )
    inspect_profile_state.add_argument("--runtime-root", required=True)
    inspect_profile_state.add_argument("--profile-id", required=True)
    inspect_profile_state.add_argument("--state-id", required=True)

    update_profile_state = subparsers.add_parser(
        "update-profile-seen-state",
        help="Merge one profile report into a profile-local seen-records state.",
    )
    update_profile_state.add_argument("--runtime-root", required=True)
    update_profile_state.add_argument("--profile-id", required=True)
    update_profile_state.add_argument("--profile-report", required=True)
    update_profile_state.add_argument("--state-id", default="seen-records")

    list_profile_reports = subparsers.add_parser(
        "list-profile-reports",
        help="List profile report artifacts under one runtime root.",
    )
    list_profile_reports.add_argument("--runtime-root", required=True)
    list_profile_reports.add_argument("--profile-id")

    inspect_profile_report = subparsers.add_parser(
        "inspect-profile-report",
        help="Read one profile report artifact.",
    )
    inspect_profile_report.add_argument("--runtime-root", required=True)
    inspect_profile_report.add_argument("--profile-id", required=True)
    inspect_profile_report.add_argument("--output-id", required=True)

    evaluate_intent = subparsers.add_parser(
        "evaluate-tool-intent",
        help="Evaluate one tool-intent.v1 file without executing tools.",
    )
    evaluate_intent.add_argument("--intent", required=True)
    evaluate_intent.add_argument("--runtime-root")
    evaluate_intent.add_argument("--run-id")

    approval = subparsers.add_parser(
        "record-approval",
        help="Record one local approval decision without executing tools.",
    )
    approval.add_argument("--runtime-root", required=True)
    approval.add_argument("--run-id", required=True)
    approval.add_argument("--approval-id", required=True)
    approval.add_argument("--intent", required=True)
    approval.add_argument(
        "--approval-decision", choices=["approved", "rejected"], required=True
    )
    approval.add_argument("--approved-by", required=True)
    approval.add_argument("--justification", required=True)
    approval.add_argument("--dry-run-ref")

    dry_run = subparsers.add_parser(
        "record-dry-run",
        help="Record one dry-run result without executing tools.",
    )
    dry_run.add_argument("--runtime-root", required=True)
    dry_run.add_argument("--run-id", required=True)
    dry_run.add_argument("--dry-run-id", required=True)
    dry_run.add_argument("--intent", required=True)
    dry_run.add_argument(
        "--dry-run-kind",
        choices=[
            "disposable_worktree",
            "sandboxed_container",
            "read_only_simulation",
            "test_only_execution",
            "custom",
        ],
        required=True,
    )
    dry_run.add_argument(
        "--result-status", choices=["passed", "failed", "blocked"], required=True
    )
    dry_run.add_argument("--recorded-by", required=True)
    dry_run.add_argument("--summary", required=True)
    dry_run.add_argument("--artifact-ref", dest="artifact_refs", action="append")

    mediation = subparsers.add_parser(
        "mediate-tool-intent",
        help="Mediate one tool-intent.v1 file without executing tools.",
    )
    mediation.add_argument("--runtime-root", required=True)
    mediation.add_argument("--run-id", required=True)
    mediation.add_argument("--mediation-id", required=True)
    mediation.add_argument("--intent", required=True)
    mediation.add_argument("--dry-run-result")
    mediation.add_argument("--approval-record")

    list_mediation = subparsers.add_parser(
        "list-mediation-records",
        help="List execution-mediation.v1 records under one runtime root.",
    )
    list_mediation.add_argument("--runtime-root", required=True)
    list_mediation.add_argument("--run-id")

    inspect_mediation = subparsers.add_parser(
        "inspect-mediation-record",
        help="Read one execution-mediation.v1 record.",
    )
    inspect_mediation.add_argument("--runtime-root", required=True)
    inspect_mediation.add_argument("--run-id", required=True)
    inspect_mediation.add_argument("--mediation-id", required=True)

    tool_execution = subparsers.add_parser(
        "execute-tool-intent",
        help="Execute one explicit local command after ready mediation.",
    )
    tool_execution.add_argument("--runtime-root", required=True)
    tool_execution.add_argument("--run-id", required=True)
    tool_execution.add_argument("--execution-id", required=True)
    tool_execution.add_argument("--intent", required=True)
    tool_execution.add_argument("--mediation-record", required=True)
    tool_execution.add_argument("--executed-by", required=True)
    tool_execution.add_argument("--command", dest="tool_command", required=True)
    tool_execution.add_argument("--arg", dest="tool_args", action="append")
    tool_execution.add_argument("--timeout-seconds", type=float, default=30.0)
    tool_execution.add_argument("--metadata-key", dest="metadata_keys", action="append")

    provider_request = subparsers.add_parser(
        "prepare-provider-request",
        help="Prepare one provider-request.v1 record without invoking providers.",
    )
    provider_request.add_argument("--runtime-root", required=True)
    provider_request.add_argument("--run-id", required=True)
    provider_request.add_argument("--request-id", required=True)
    provider_request.add_argument("--mediation-record", required=True)
    provider_request.add_argument(
        "--preset",
        dest="preset_id",
        choices=provider_preset_ids(),
        required=True,
    )
    provider_request.add_argument(
        "--context-ref", dest="context_refs", action="append"
    )

    subparsers.add_parser(
        "list-provider-presets",
        help="List repo-owned read-only provider presets without invoking providers.",
    )

    inspect_provider_preset = subparsers.add_parser(
        "inspect-provider-preset",
        help="Read one repo-owned provider preset without invoking providers.",
    )
    inspect_provider_preset.add_argument(
        "--preset",
        dest="preset_id",
        choices=provider_preset_ids(),
        required=True,
    )

    provider_result = subparsers.add_parser(
        "record-provider-result",
        help="Record one provider-result.v1 artifact without invoking providers.",
    )
    provider_result.add_argument("--runtime-root", required=True)
    provider_result.add_argument("--run-id", required=True)
    provider_result.add_argument("--result-id", required=True)
    provider_result.add_argument("--provider-request", required=True)
    provider_result.add_argument(
        "--result-status", choices=["succeeded", "failed", "blocked"], required=True
    )
    provider_result.add_argument("--recorded-by", required=True)
    provider_result.add_argument("--summary", required=True)
    provider_result.add_argument("--response-ref", dest="response_refs", action="append")
    provider_result.add_argument("--usage-key", dest="usage_keys", action="append")
    provider_result.add_argument("--error-kind")
    provider_result.add_argument("--error-message")

    provider_invocation = subparsers.add_parser(
        "invoke-provider-request",
        help="Invoke one explicit local command for a provider-request.v1 record.",
    )
    provider_invocation.add_argument("--runtime-root", required=True)
    provider_invocation.add_argument("--run-id", required=True)
    provider_invocation.add_argument("--result-id", required=True)
    provider_invocation.add_argument("--provider-request", required=True)
    provider_invocation.add_argument("--recorded-by", required=True)
    provider_invocation.add_argument("--timeout-seconds", type=float, default=30.0)
    provider_invocation.add_argument("--usage-key", dest="usage_keys", action="append")

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
