# 12 — Current Surface Audit

## Purpose

This document records the current source-of-truth surface before widening
runtime scope again.

It is not a roadmap and not a release note. Use it to distinguish:

- implemented and locally verified surfaces;
- explicit deferred scope;
- next safe expansion boundaries.

## Audit date

2026-05-30

## Current completion boundary

As of this audit, the non-deferred docs/contracts/runtime surface described in
the verified entrypoints below is implemented and locally verified.

This does not mean the repository is a finished hosted product or broad
automation platform. The remaining not-yet-implemented areas are explicit
deferred scope and require a new behavior decision before implementation.

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
- `arxiv_query`
- `rss`
- `news`

`custom` remains a contract-level source type for consumer-owned or future
runtime paths. It does not currently have a shared collector or source-config
dispatch path.
The retired `arxiv_rss_keywords` family is not active source surface because it
duplicated arXiv API query transport under an RSS/feed name. Use `arxiv_query`
for arXiv API query transport or `rss` for explicit feed transport.

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
- profile seen-state record ids must be safe path segments, sorted, and unique;
- governance, tool-execution, and provider adapter artifacts reject unsafe
  `profile_id` values before those profile-scoped identities move across
  policy, mediation, execution, or provider boundaries;
- provider request and result artifacts preserve safe `mediation_id` values
  from execution mediation records;
- `intent_id` remains a logical correlation id for matching tool intent scope;
  it is not a runtime path segment in the current contracts;
- governed tool execution requires the supplied argv to exactly match
  `tool-intent.v1` `arguments.command` before invocation;
- provider request, provider result, and provider invocation boundaries are
  currently `read_only`-only and reject side-effect action classes;
- denied provider requests are rejected before provider-request records;
- embedded governance audit events reuse standalone audit id validation;
- `profile_id`, source ids, clean record ids, profile projection ids, raw
  metadata ids, run-manifest ids, source-health ids, governance audit ids,
  approval record ids, dry-run result ids, execution mediation ids, tool
  execution result ids, provider request ids, provider result ids, and
  profile-state ids use safe path segments at their relevant contract
  boundaries.

## Explicitly deferred scope

Do not treat these as missing bugs without a new behavior decision:

- source collector families beyond the implemented families listed above;
- sanitizer mappings beyond the implemented families listed above;
- consumer-specific ranking, editorial shaping, or dedupe policy;
- implicit profile-state updates without an explicit gate;
- automatic command discovery;
- credential mapping or default provider/tool presets;
- SQLite, daemon, web UI, cloud service, dashboard, or scheduler.

## Latest verification evidence

Local verification on 2026-05-30:

- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 195 tests
  after retiring `arxiv_rss_keywords` and adding execution-boundary tests.
- `jq empty schemas/*.json profiles/examples/*.json sources/examples/*.json`
  passed.
- `git diff --check` passed.
- `PYTHONPATH=src python3 -m compileall -q src tests` passed.
- `PYTHONPATH=src python3 -m shared_intake_governance.cli --help` passed.

Live isolated source smoke on 2026-05-30:

- command: `smoke-source-config` with
  `sources/examples/arxiv-query-code-agents.json` and
  `profiles/examples/code-intel-kernel.json`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 5 clean records, 1
  projection report, 3 projected items, 1 run manifest, and 1 healthy source
  health artifact;
- read-only inspection commands validated the smoke run manifest, source
  health artifact, and profile report.

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
