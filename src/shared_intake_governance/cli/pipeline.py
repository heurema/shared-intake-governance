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
from shared_intake_governance.governance import evaluate_tool_intent
from shared_intake_governance.projector import ProfileProjector, load_profile
from shared_intake_governance.runtime import (
    AuditWriter,
    ApprovalWriter,
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
    if args.command == "list-profile-reports":
        return _list_profile_reports(args, stdout)
    if args.command == "inspect-profile-report":
        return _inspect_profile_report(args, stdout)
    if args.command == "evaluate-tool-intent":
        return _evaluate_tool_intent(args, stdout)
    if args.command == "record-approval":
        return _record_approval(args, stdout)
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


def _project_profiles(args: argparse.Namespace, stdout: TextIO) -> int:
    paths = RuntimePaths(Path(args.runtime_root))
    output_id = args.output_id or generate_run_id()
    profile_paths = [Path(path) for path in args.profiles]
    for profile_path in profile_paths:
        load_profile(profile_path)

    projections = []
    projector = ProfileProjector(paths)
    for profile_path in profile_paths:
        projection = projector.project(profile_path, output_id=output_id)
        projections.append(
            {
                "profile_id": projection.report["profile_id"],
                "output_mode": projection.report["output_mode"],
                "projection_path": str(projection.path),
                "clean_records_seen": projection.report["counts"][
                    "clean_records_seen"
                ],
                "items_written": projection.report["counts"]["items_written"],
            }
        )

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
    state = dict(state)
    state["profile_state_path"] = str(state_path)
    _print_json(stdout, state)
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


def _profile_report_summary(profile_report_path: Path) -> dict[str, Any]:
    report = _read_json(profile_report_path)
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

    project_profiles = subparsers.add_parser(
        "project-profiles",
        help="Project multiple profiles from the existing clean cache.",
    )
    project_profiles.add_argument("--runtime-root", required=True)
    project_profiles.add_argument(
        "--profile", dest="profiles", action="append", required=True
    )
    project_profiles.add_argument("--output-id")

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
