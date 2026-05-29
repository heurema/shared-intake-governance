# 12 — Current Surface Audit

## Purpose

This document records the current source-of-truth surface before widening
runtime scope again.

It is not a roadmap and not a release note. Use it to distinguish:

- implemented and locally verified surfaces;
- explicit deferred scope;
- next safe expansion boundaries.

## Audit date

2026-05-29

## Verified source-of-truth entrypoints

- `README.md`
- `docs/INDEX.md`
- `docs/10-implementation-guide.md`
- `docs/11-local-runbook.md`
- `AGENTS.md`

## Implemented source families

The current local runtime has read-only collectors, source config dispatch,
clean-record emission, projection support, source-health output, and run
manifest output for:

- `github_repo`
- `github_search`
- `arxiv_rss_keywords`
- `arxiv_query`
- `rss`
- `news`

`custom` remains a contract-level source type for consumer-owned or future
runtime paths. It does not currently have a shared collector or source-config
dispatch path.

## Implemented runtime boundaries

Current runtime code covers:

- runtime path helpers for local file-based artifacts;
- validated raw payload metadata, run manifests, and source health;
- source-config validation and examples;
- clean-record emission from implemented source families;
- deterministic profile projection from the clean cache;
- explicit profile seen-state updates;
- read-only runtime inspection commands;
- governance decision evaluation and optional audit logging;
- approval, dry-run, mediation, and local tool-execution records;
- provider-neutral request and result records;
- explicit local provider command invocation.

The runtime remains local-first and file-based. Runtime data belongs outside
the repository.

## Contract hardening already in place

Current validators and schemas reject several invalid states before downstream
runtime paths consume them:

- denied governance decisions remain blocked during mediation;
- raw metadata status must match body/error state;
- source health counts must match success/failure counts;
- terminal run manifests must carry matching source-health refs;
- projection counts must match emitted and excluded records;
- profile seen-state record ids must be sorted and unique;
- denied provider requests are rejected before provider-request records;
- `profile_id`, source ids, raw metadata ids, run-manifest ids,
  source-health ids, and profile-state ids use safe path segments at their
  relevant contract boundaries.

## Explicitly deferred scope

Do not treat these as missing bugs without a new behavior decision:

- source collector families beyond the implemented families listed above;
- sanitizer mappings beyond the implemented families listed above;
- consumer-specific ranking, editorial shaping, or dedupe policy;
- implicit profile-state updates without an explicit gate;
- automatic command discovery;
- credential mapping or default provider/tool presets;
- SQLite, daemon, web UI, cloud service, dashboard, or scheduler.

## Verification commands

Use these checks after runtime or contract changes:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
jq empty schemas/*.json profiles/examples/*.json sources/examples/*.json
git diff --check
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m shared_intake_governance.cli --help
```

Remove generated `__pycache__` directories after compile checks.

## Next safe expansion rule

Before the next runtime expansion, choose exactly one of:

- one explicit source family;
- one explicit profile-state boundary;
- one explicit command or provider boundary;
- one contract/runtime validation mismatch.

Do not add a new system layer to solve a local contract gap.
