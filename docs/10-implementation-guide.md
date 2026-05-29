# 10 — Implementation Guide

## Purpose

This document turns the architecture into an implementation order.

Use it when starting runtime code so the first cut stays small, safe, and useful.

## What not to do first

Do not start with:

- a web UI;
- a daemon;
- SQLite;
- provider adapters;
- cross-project automation orchestration;
- generic plugin systems;
- model summarization as a hard dependency.

Those are later concerns.

## Default implementation bias

Prefer:

- Python 3;
- stdlib first;
- file-based runtime;
- explicit JSON artifacts;
- narrow CLIs;
- deterministic tests.

This bias is pragmatic because the initial consumers already use Python-friendly automation and JSON artifacts.

## Proposed repository growth

When runtime work begins, grow the repo roughly like this:

```text
src/
  shared_intake_governance/
    cli/
    collector/
    sanitizer/
    projector/
    governance/
    adapters/
    runtime/
tests/
docs/
schemas/
profiles/examples/
```

This is a target shape, not a demand to scaffold everything immediately.

## Phase 1 target

The first runtime slice should prove:

1. one shared source fetch path works;
2. immutable raw evidence is written;
3. clean records are emitted from raw evidence;
4. one profile can project from the clean cache;
5. no LLM is required;
6. no side effects exist.

## Recommended first source paths

Start with these because they are both practical and already motivated by existing consumers:

1. `github_repo`
2. `arxiv_rss_keywords`

Why these first:

- they are useful across multiple consumers;
- they avoid the most brittle scraping paths;
- they cover a repository-centric and research-feed-centric source shape;
- they already exposed real rate-limit and transport issues in earlier local loops.

## Recommended first CLI surface

Keep the first CLI narrow.

Suggested commands:

- `collect`
- `sanitize`
- `project`

Optional later convenience:

- `run-daily`
- `inspect-record`
- `show-source-health`

Do not start with a mega-command that hides every phase.

Current CLI implementation:

- `python -m shared_intake_governance.cli run-github-repo`
- `python -m shared_intake_governance.cli run-github-search`
- `python -m shared_intake_governance.cli run-arxiv-rss-keywords`
- `python -m shared_intake_governance.cli run-arxiv-query`
- `python -m shared_intake_governance.cli run-rss-feed`
- `python -m shared_intake_governance.cli run-source-config`
- `python -m shared_intake_governance.cli smoke-source-config`
- `python -m shared_intake_governance.cli project-profiles`
- `python -m shared_intake_governance.cli list-runs`
- `python -m shared_intake_governance.cli list-clean-records`
- `python -m shared_intake_governance.cli inspect-record`
- `python -m shared_intake_governance.cli list-profile-state`
- `python -m shared_intake_governance.cli inspect-profile-state`
- `python -m shared_intake_governance.cli update-profile-seen-state`
- `python -m shared_intake_governance.cli list-profile-reports`
- `python -m shared_intake_governance.cli inspect-profile-report`
- `python -m shared_intake_governance.cli evaluate-tool-intent`
- `python -m shared_intake_governance.cli record-approval`
- `python -m shared_intake_governance.cli record-dry-run`
- `python -m shared_intake_governance.cli mediate-tool-intent`
- `python -m shared_intake_governance.cli list-mediation-records`
- `python -m shared_intake_governance.cli inspect-mediation-record`
- `python -m shared_intake_governance.cli execute-tool-intent`
- `python -m shared_intake_governance.cli prepare-provider-request`
- `python -m shared_intake_governance.cli record-provider-result`
- `python -m shared_intake_governance.cli invoke-provider-request`
- `python -m shared_intake_governance.cli inspect-run`
- `python -m shared_intake_governance.cli show-source-health`
- `sources/examples/github-signum.json`
- `sources/examples/github-search-code-agents.json`
- `sources/examples/arxiv-code-agents.json`
- `sources/examples/arxiv-query-code-agents.json`
- `sources/examples/rss-github-blog.json`
- `src/shared_intake_governance/cli/pipeline.py`
- `tests/test_cli_pipeline.py`

These commands intentionally cover only the implemented `github_repo`,
`github_search`, `arxiv_rss_keywords`, `arxiv_query`, and `rss` paths. They
require explicit runtime root, profile path, source-specific inputs or one
validated `source-config.v1` file, and run/output identifiers. The smoke
command may allocate an isolated temporary runtime root when none is provided.
These commands also write:

- `runs/<run-id>.manifest.json`
- `source-health/<run-id>/<source-id>.json`

The inspection commands are read-only and should not create runtime files. They
validate runtime artifacts before returning summaries or full objects.
The `project-profiles` command reads the shared clean cache and writes one
deterministic report per explicit profile path. With `--update-seen-state`, it
also merges each generated report into that profile's local `seen_records`
state artifact.
The profile-state inspection commands read existing `profile-state.v1`
artifacts only. The profile seen-state update command explicitly merges record
ids from one `profile-projection.v1` report into one `seen_records` state
artifact, validating existing and updated profile state. `project-profiles`
still does not update seen state implicitly or change projection behavior.
The governance evaluator reads one `tool-intent.v1` file and prints one
`governance-decision.v1` decision; when `--runtime-root` and `--run-id` are
provided together, it validates and appends one `governance-audit-event.v1`
JSONL record. It validates the input tool intent and output governance
decision, and it does not execute tools or create approvals.
The approval recorder reads one `tool-intent.v1` file and validates and writes
one `approval-record.v1` file. It does not execute tools or satisfy the future
dry-run sidecar requirement by itself.
The dry-run recorder reads one `tool-intent.v1` file and validates and writes
one `dry-run-result.v1` file. It records dry-run evidence only; it does not
execute the requested tool or mediate side effects.
The mediation command reads one `tool-intent.v1` file plus optional dry-run
and approval records, then validates and writes one `execution-mediation.v1`
readiness record. It does not execute the requested tool or call provider
adapters.
The mediation inspection commands read existing `execution-mediation.v1`
artifacts only and do not write runtime data.
The tool execution command reads one `tool-intent.v1` artifact plus one matching
validated `execution-mediation.v1` artifact. It refuses blocked or mismatched
mediation without invoking the command. When mediation is ready, it runs only
the explicit local command supplied by the operator, passes the tool intent JSON
on stdin, stores stdout/stderr as runtime artifacts, and writes one validated
`tool-execution-result.v1` artifact.
The provider request command reads one ready `execution-mediation.v1` artifact
and validates and writes one provider-neutral `provider-request.v1` artifact.
It validates the input mediation record and does not invoke providers, discover
credentials, or execute tools.
The provider result command reads one `provider-request.v1` artifact and
validates and writes one `provider-result.v1` artifact with response refs and
usage metadata. It validates the input provider request and does not invoke
providers or store full provider responses.
The provider invocation command reads one `provider-request.v1` artifact, runs
only the explicit local command supplied by the operator, validates the request
before passing provider request JSON on stdin, stores stdout/stderr as runtime
artifacts, and writes one `provider-result.v1` artifact. It does not discover
provider CLIs, load credentials, choose default provider commands, or execute
the requested tool directly.

For current manual invocation examples, see [11-local-runbook.md](11-local-runbook.md).

## Concrete implementation order

### Step 1: freeze the missing runtime contracts

Before code, confirm:

- raw metadata shape;
- runtime directory layout;
- clean record fields;
- profile loading rules;
- source health output shape.

If a runtime concept has no contract, document it first.

Current Phase 1 contract anchors:

- raw metadata shape: `schemas/raw-metadata.schema.json`
- runtime directory layout: `docs/09-operating-model.md`
- clean record fields: `schemas/clean-record.schema.json`
- profile loading rules: `docs/02-data-contracts.md`
- profile projection report shape: `schemas/profile-projection.schema.json`
- profile state shape: `schemas/profile-state.schema.json`
- source health output shape: `schemas/source-health.schema.json`
- run manifest shape: `schemas/run-manifest.schema.json`
- governance decision shape: `schemas/governance-decision.schema.json`
- governance audit event shape: `schemas/governance-audit-event.schema.json`
- approval record shape: `schemas/approval-record.schema.json`
- dry-run result shape: `schemas/dry-run-result.schema.json`
- execution mediation shape: `schemas/execution-mediation.schema.json`
- tool execution result shape: `schemas/tool-execution-result.schema.json`
- provider request shape: `schemas/provider-request.schema.json`
- provider result shape: `schemas/provider-result.schema.json`

If these anchors drift, update the docs or schemas before adding runtime code.

### Step 2: implement runtime path helpers

Create small helpers for:

- runtime root resolution;
- run id generation;
- source-local raw paths;
- clean-record paths;
- per-profile state and report paths.

Keep these deterministic and testable.

### Step 3: implement raw writers

Add file writers for:

- raw payload body;
- raw metadata JSON;
- run manifest or run metadata.

This should be usable before any source-specific collector exists.

Current implementation:

- `src/shared_intake_governance/runtime/paths.py`
- `src/shared_intake_governance/runtime/writers.py`
- `src/shared_intake_governance/source_config.py`
- `tests/test_runtime_paths_and_writers.py`
- `tests/test_source_config_examples.py`
- raw metadata artifacts are validated before writer output.
- run manifests are validated before writer output.
- source health artifacts are validated before writer output.
- source config files are validated before `run-source-config` and
  `smoke-source-config` dispatch to collectors.

### Step 4: implement one source collector family

Start with `github_repo` or `arxiv_rss_keywords`.

The collector should:

- fetch read-only data;
- capture response metadata;
- derive canonical identity;
- write raw evidence only.

It should not sanitize or score inline.

Current implementation:

- `src/shared_intake_governance/collector/github_repo.py`
- `src/shared_intake_governance/collector/github_search.py`
- `src/shared_intake_governance/collector/arxiv_rss_keywords.py`
- `src/shared_intake_governance/collector/arxiv_query.py`
- `src/shared_intake_governance/collector/rss_feed.py`
- `tests/test_github_repo_collector.py`
- `tests/test_github_search_collector.py`
- `tests/test_arxiv_rss_keywords_collector.py`
- `tests/test_arxiv_query_collector.py`
- `tests/test_rss_feed_collector.py`

### Step 5: implement sanitizer and clean-record emission

The sanitizer should:

- normalize text;
- strip markup;
- cap lengths;
- emit risk flags;
- set `quarantined` when required;
- write clean records.

Current implementation:

- `src/shared_intake_governance/sanitizer/clean_records.py`
- `tests/test_clean_records_and_projection.py`
- `github_repo` raw JSON maps to one clean record.
- `github_search` raw JSON repository search results map to one clean record
  per repository item.
- `arxiv_rss_keywords` raw Atom feeds map to one clean record per entry.
- `arxiv_query` raw Atom feeds map to one clean record per entry.
- `rss` raw XML feeds map to one clean record per item.
- single-record emission rejects multi-entry raw evidence instead of silently
  dropping records; use all-record emission for feed-shaped sources.

### Step 6: implement one projector

The first projector should:

- load one profile;
- filter by accepted source families and keywords;
- exclude disallowed risk flags;
- write a deterministic per-profile output.

Keep the first output simple, even JSON-only if needed.

Current implementation:

- `src/shared_intake_governance/projector/profile.py`
- `src/shared_intake_governance/projector/profile_state.py`
- `tests/test_clean_records_and_projection.py`
- `tests/test_profile_state.py`
- profile projection reports are validated before write and before seen-state
  updates consume them.
- `project-profiles` CLI can run the same projector for multiple explicit
  profile paths from one clean cache.
- `project-profiles --update-seen-state` can explicitly merge each generated
  projection report into that profile's local `seen_records` state file.
- `update-profile-seen-state` CLI can explicitly merge one projection report
  into one profile-local `seen_records` state file.

### Step 7: add tests before more features

Before expanding source coverage, test:

- runtime path resolution;
- raw write determinism;
- sanitization behavior;
- risk flagging behavior;
- profile filtering;
- dedupe or identity behavior if applicable.

### Step 8: add second source family

Only after the first path is stable.
The second source should prove the contracts are genuinely reusable, not tuned to one transport.

## What Phase 1 should leave behind

After Phase 1, the repo should be able to demonstrate:

- shared raw cache;
- shared clean cache;
- one or more clean records from real sources;
- one or more projected outputs for one consumer profile;
- no LLM dependence;
- no side-effect execution.

That is the proof point for the whole architecture.

## Phase 2 and later

Only after Phase 1 is solid:

- project multiple profiles from the same clean cache;
- add per-profile state and report shaping;
- then add governance broker contracts and runtime;
- only then add provider adapters.

Current governance runtime:

- `src/shared_intake_governance/governance/policy.py`
- `src/shared_intake_governance/governance/mediation.py`
- `src/shared_intake_governance/executor/tool_execution.py`
- `tests/test_governance_policy.py`
- `tests/test_governance_mediation.py`
- `tests/test_tool_execution.py`
- `evaluate-tool-intent` implements only the default policy evaluator.
- `evaluate-tool-intent --runtime-root ... --run-id ...` appends audit
  evidence for evaluated intents.
- `record-approval` writes explicit local approval or rejection records.
- `record-dry-run` writes recorded dry-run evidence for a tool intent.
- `mediate-tool-intent` writes a pre-execution readiness record from one tool
  intent plus optional validated dry-run and approval records.
- `list-mediation-records` and `inspect-mediation-record` provide read-only
  mediation inventory and inspection.
- read-only runtime inventory and inspection commands validate artifacts before
  returning summaries or full objects.
- `execute-tool-intent` writes one `tool-execution-result.v1` artifact after
  validating and checking ready mediation, then running only an explicit local
  command.
- tool intents, optional mediation evidence, and governance decisions are
  validated before the governance runtime consumes or returns them.

Current provider adapter boundary:

- `src/shared_intake_governance/adapters/provider_invocation.py`
- `src/shared_intake_governance/adapters/provider_request.py`
- `src/shared_intake_governance/adapters/provider_result.py`
- `tests/test_provider_invocation.py`
- `tests/test_provider_request.py`
- `tests/test_provider_result.py`
- `prepare-provider-request` writes a provider-neutral request record from one
  ready mediation record without invoking providers.
- `record-provider-result` writes provider response refs and usage metadata
  from one provider request without invoking providers.
- `invoke-provider-request` runs one explicit local command with the provider
  request JSON on stdin after validating the request, stores stdout/stderr as
  response refs, and records a provider result.

Still missing:

- implicit profile-state updates from `project-profiles` or consumer-specific
  dedupe behavior;
- source collector families beyond `github_repo`, `github_search`,
  `arxiv_rss_keywords`, `arxiv_query`, and `rss`;
- sanitizer source mappings beyond `github_repo`, `github_search`,
  `arxiv_rss_keywords`, `arxiv_query`, and `rss`;
- provider/tool command discovery, credential mapping, or default presets.

## Handoff rule for the next session

If the next session starts runtime work, it should begin by checking whether the repo still matches this document.

If reality has drifted, update this document before widening the implementation.
