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
2. `arxiv_query`

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
- `python -m shared_intake_governance.cli run-github-releases`
- `python -m shared_intake_governance.cli run-github-search`
- `python -m shared_intake_governance.cli run-arxiv-query`
- `python -m shared_intake_governance.cli run-rss-feed`
- `python -m shared_intake_governance.cli run-news-feed`
- `python -m shared_intake_governance.cli run-source-config`
- `python -m shared_intake_governance.cli smoke-source-config`
- `python -m shared_intake_governance.cli list-source-configs`
- `python -m shared_intake_governance.cli inspect-source-config`
- `python -m shared_intake_governance.cli list-source-sets`
- `python -m shared_intake_governance.cli inspect-source-set`
- `python -m shared_intake_governance.cli list-profiles`
- `python -m shared_intake_governance.cli inspect-profile`
- `python -m shared_intake_governance.cli check-source-set-profiles`
- `python -m shared_intake_governance.cli project-profiles`
- `python -m shared_intake_governance.cli list-runs`
- `python -m shared_intake_governance.cli list-clean-records`
- `python -m shared_intake_governance.cli inspect-record`
- `python -m shared_intake_governance.cli list-profile-state`
- `python -m shared_intake_governance.cli inspect-profile-state`
- `python -m shared_intake_governance.cli init-profile-seen-state`
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
- `python -m shared_intake_governance.cli list-provider-presets`
- `python -m shared_intake_governance.cli inspect-provider-preset`
- `python -m shared_intake_governance.cli record-provider-result`
- `python -m shared_intake_governance.cli invoke-provider-request`
- `python -m shared_intake_governance.cli inspect-run`
- `python -m shared_intake_governance.cli show-source-health`
- `sources/examples/github-signum.json`
- `sources/examples/github-releases-repo-governance.json`
- `sources/examples/github-releases-shared-intake.json`
- `sources/examples/github-search-code-agents.json`
- `sources/examples/arxiv-query-code-agents.json`
- `sources/examples/news-openai-blog.json`
- `sources/examples/rss-github-blog.json`
- `src/shared_intake_governance/cli/pipeline.py`
- `tests/test_cli_pipeline.py`

These commands intentionally cover only the implemented `github_repo`,
`github_releases`, `github_search`, `arxiv_query`, `rss`, and `news` paths.
They require explicit runtime root, profile path, source-specific inputs or one
validated `source-config.v1` file, and run/output identifiers. The smoke
command may allocate an isolated temporary runtime root when none is provided.
These commands also write:

- `runs/<run-id>.manifest.json`
- `source-health/<run-id>/<source-id>.json`

The inspection commands are read-only and should not create runtime files. They
validate runtime artifacts or repo-tracked source-set/source-config refs before
returning summaries or full objects.
The repo-local `scripts/check_surface_consistency.py` guard compares the actual
argparse command surface to the `Current CLI implementation` list above. Run it
after adding, removing, renaming, or reordering CLI commands so docs drift is
caught before review.
The repo-local `scripts/check_source_type_consistency.py` guard compares
source type lists across code, schemas, and
`docs/12-current-surface-audit.md`. Run it after adding, removing, or retiring a
source type so contract/runtime/docs drift is caught before review.
The repo-local `scripts/check_provider_surface_consistency.py` guard compares
provider and provider-preset lists across the repo-owned allowlist, schemas,
runtime validators, and docs. Run it after adding, removing, or retiring a
provider preset so contract/runtime/docs drift is caught before review.
The repo-local `scripts/check_contract_anchor_consistency.py` guard compares
tracked JSON schemas against `docs/INDEX.md`, `docs/02-data-contracts.md`,
this implementation guide, and each schema `$id`. Run it after adding,
removing, renaming, or reordering a contract schema so contract/docs drift is
caught before review.
The repo-local `scripts/check_repo.py` runner executes the canonical local
verification checklist and removes generated `__pycache__` directories. Use
`python3 scripts/check_repo.py --list` to print the checklist without running
it.
The `project-profiles` command reads the shared clean cache and writes one
deterministic report per explicit profile path. With `--update-seen-state`, it
also merges each generated report into that profile's local `seen_records`
state artifact.
With `--exclude-seen-state`, it reads each profile's local `seen_records`
state artifact and omits already-seen record ids from that report without
updating state.
The `run-source-config` and `smoke-source-config` commands support the same
explicit read-only seen-state filter for one-source collect, sanitize, and
project runs.
The `list-source-configs` command validates tracked `source-config.v1` files
under `sources/examples/` and returns a deterministic inventory without
fetching, projecting, reading profile state, or writing runtime data. It
rejects duplicate `source_id` values across the tracked catalog.
The `inspect-source-config` command validates one `source-config.v1` file and
returns a normalized summary without fetching, projecting, reading profile
state, or writing runtime data.
The `list-source-sets` command validates tracked `source-set.v1` files under
`sources/sets/` and every referenced `source-config.v1` file without
collecting, projecting, scheduling, batching sources, or writing runtime data.
It rejects duplicate `source_set_id` values across the tracked catalog and
duplicate `source_id` and `source_config_path` values inside one source set
before resolving source config refs.
The `inspect-source-set` command validates one `source-set.v1` file and every
referenced `source-config.v1` file without collecting, projecting, scheduling,
or batching sources. It applies the same unique source id and source config ref
boundary.
The `list-profiles` command validates tracked profile configs under
`profiles/examples/` and returns a deterministic catalog without collecting,
projecting, reading profile state, or writing runtime data. Profile validation
rejects duplicate profile ids, empty accepted source lists, and source types
that are not in the profile schema allowlist.
The `inspect-profile` command validates one profile config and returns its
normalized object without collecting, projecting, reading profile state, or
writing runtime data.
The `check-source-set-profiles` command validates one source set, its
referenced source configs, and one or more profile configs, then reports which
sources match or are rejected by each profile's accepted source types. It does
not collect, project, schedule, batch, read profile state, or write runtime
data.
With `--update-seen-state`, `project-profiles`, `run-source-config`, and
`smoke-source-config` also explicitly merge generated report items into the
profile's local `seen_records` state artifact.
The profile-state inspection commands read existing `profile-state.v1`
artifacts only. The profile seen-state init command explicitly creates one
empty `seen_records` state artifact and refuses to overwrite an existing state.
The profile seen-state update command explicitly merges record ids from one
`profile-projection.v1` report into one `seen_records` state artifact,
validating existing and updated profile state. `project-profiles` still does
not update seen state implicitly.
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
the explicit local command supplied by the operator after confirming the argv
exactly matches `tool-intent.v1` `arguments.command`, passes the tool intent
JSON on stdin, stores stdout/stderr as runtime artifacts, and writes one
validated `tool-execution-result.v1` artifact.
The provider request command reads one ready `execution-mediation.v1` artifact
with `action_class: read_only` and validates and writes one provider-neutral
`provider-request.v1` artifact with a repo-owned preset id, resolved provider
command argv, and command hash. It validates the input mediation record and
does not invoke providers, discover credentials, execute tools, accept
arbitrary provider argv, or translate side-effect mediations into provider
requests.
The provider preset inspection commands resolve the repo-owned read-only
allowlist into JSON without invoking providers, discovering commands, reading
credentials, or writing runtime artifacts.
The provider result command reads one `provider-request.v1` artifact and
validates and writes one `provider-result.v1` artifact with response refs and
usage metadata. It validates the input provider request and does not invoke
providers or store full provider responses.
The provider invocation command reads one `provider-request.v1` artifact,
rejects invoke-time command overrides, confirms the request still matches its
repo-owned preset allowlist entry, validates the request before passing
provider request JSON on stdin to `resolved_command`, stores stdout/stderr as
runtime artifacts, and writes one `provider-result.v1` artifact. It does not
discover provider CLIs, load credentials, choose provider commands outside the
allowlist, or execute the requested tool directly. Current provider requests
are `read_only`-only, so provider invocation is not a side-effect execution
path.

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
- clean record fields: `schemas/clean-record.schema.json`
- run manifest shape: `schemas/run-manifest.schema.json`
- source health output shape: `schemas/source-health.schema.json`
- source config shape: `schemas/source-config.schema.json`
- source set shape: `schemas/source-set.schema.json`
- profile config shape: `schemas/profile.schema.json`
- profile projection report shape: `schemas/profile-projection.schema.json`
- profile state shape: `schemas/profile-state.schema.json`
- tool intent shape: `schemas/tool-intent.schema.json`
- governance decision shape: `schemas/governance-decision.schema.json`
- governance audit event shape: `schemas/governance-audit-event.schema.json`
- approval record shape: `schemas/approval-record.schema.json`
- dry-run result shape: `schemas/dry-run-result.schema.json`
- execution mediation shape: `schemas/execution-mediation.schema.json`
- tool execution result shape: `schemas/tool-execution-result.schema.json`
- provider request shape: `schemas/provider-request.schema.json`
- provider result shape: `schemas/provider-result.schema.json`
- runtime directory layout: `docs/09-operating-model.md`
- profile loading rules: `docs/02-data-contracts.md`

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
- non-null raw metadata `storage_path` values are bounded to the configured
  runtime raw root before writer output.
- run manifests are validated before writer output.
- source health artifacts are validated before writer output.
- source config files are validated before `run-source-config` and
  `smoke-source-config` dispatch to collectors.

### Step 4: implement one source collector family

Start with `github_repo` or `arxiv_query`.

The collector should:

- fetch read-only data;
- capture response metadata;
- derive canonical identity;
- write raw evidence only.

It should not sanitize or score inline.

Current implementation:

- `src/shared_intake_governance/collector/github_repo.py`
- `src/shared_intake_governance/collector/github_releases.py`
- `src/shared_intake_governance/collector/github_search.py`
- `src/shared_intake_governance/collector/arxiv_query.py`
- `src/shared_intake_governance/collector/news_feed.py`
- `src/shared_intake_governance/collector/rss_feed.py`
- `tests/test_github_repo_collector.py`
- `tests/test_github_releases_collector.py`
- `tests/test_github_search_collector.py`
- `tests/test_arxiv_query_collector.py`
- `tests/test_news_feed_collector.py`
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
- raw metadata is validated before sanitizer consumption.
- sanitizer raw body reads are bounded to the configured runtime raw root.
- `github_repo` raw JSON maps to one clean record.
- `github_releases` raw JSON release results map to one clean record per
  release item.
- `github_search` raw JSON repository search results map to one clean record
  per repository item.
- `arxiv_query` raw Atom feeds map to one clean record per entry.
- `rss` raw XML feeds map to one clean record per item.
- `news` raw XML feeds map to one clean record per item.
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
- `project-profiles --exclude-seen-state` can explicitly read each generated
  profile's local `seen_records` state file and omit matching record ids from
  the projection report without updating state.
- `run-source-config --exclude-seen-state` and `smoke-source-config
  --exclude-seen-state` apply the same explicit read-only filter during
  one-source projection.
- `run-source-config --update-seen-state` and `smoke-source-config
  --update-seen-state` explicitly merge the generated one-source report items
  into that profile's local `seen_records` state file.
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
  command that exactly matches `tool-intent.v1` `arguments.command`.
- tool intents, optional mediation evidence, and governance decisions are
  validated before the governance runtime consumes or returns them.

Current provider adapter boundary:

- `src/shared_intake_governance/adapters/provider_invocation.py`
- `src/shared_intake_governance/adapters/provider_request.py`
- `src/shared_intake_governance/adapters/provider_result.py`
- `src/shared_intake_governance/provider_presets.py`
- `tests/test_provider_invocation.py`
- `tests/test_provider_presets.py`
- `tests/test_provider_request.py`
- `tests/test_provider_result.py`
- `prepare-provider-request` writes a provider-neutral request record from one
  ready `read_only` mediation record with preset-resolved provider command argv
  and without invoking providers.
- `list-provider-presets` and `inspect-provider-preset` expose the repo-owned
  read-only preset allowlist without invoking providers.
- `record-provider-result` writes provider response refs and usage metadata
  from one provider request without invoking providers.
- `invoke-provider-request` runs the request-bound `resolved_command` with the
  provider request JSON on stdin after validating the request and preset
  binding, stores stdout/stderr as response refs, and records a provider
  result. This boundary is currently `read_only`-only.

Still missing:

- consumer-specific dedupe behavior; implicit profile-state updates remain out
  of current scope unless a new behavior decision replaces the explicit
  init or `--update-seen-state` gates;
- source collector families beyond `github_repo`, `github_releases`,
  `github_search`, `arxiv_query`, `rss`, and `news`;
- sanitizer source mappings beyond `github_repo`, `github_releases`,
  `github_search`, `arxiv_query`, `rss`, and `news`;
- provider/tool command discovery, credential mapping, or presets beyond the
  repo-owned read-only provider allowlist.

## Handoff rule for the next session

If the next session starts runtime work, it should begin by checking whether the repo still matches this document.

If reality has drifted, update this document before widening the implementation.
