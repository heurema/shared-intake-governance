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
- `python -m shared_intake_governance.cli run-arxiv-rss-keywords`
- `python -m shared_intake_governance.cli run-source-config`
- `python -m shared_intake_governance.cli smoke-source-config`
- `python -m shared_intake_governance.cli project-profiles`
- `python -m shared_intake_governance.cli list-runs`
- `python -m shared_intake_governance.cli list-clean-records`
- `python -m shared_intake_governance.cli inspect-record`
- `python -m shared_intake_governance.cli list-profile-reports`
- `python -m shared_intake_governance.cli inspect-profile-report`
- `python -m shared_intake_governance.cli inspect-run`
- `python -m shared_intake_governance.cli show-source-health`
- `sources/examples/github-signum.json`
- `sources/examples/arxiv-code-agents.json`
- `src/shared_intake_governance/cli/pipeline.py`
- `tests/test_cli_pipeline.py`

These commands intentionally cover only the implemented `github_repo` and
`arxiv_rss_keywords` paths. They require explicit runtime root, profile path,
source-specific inputs or one `source-config.v1` file, and run/output
identifiers. The smoke command may allocate an isolated temporary runtime root
when none is provided. These commands also write:

- `runs/<run-id>.manifest.json`
- `source-health/<run-id>/<source-id>.json`

The inspection commands are read-only and should not create runtime files.
The `project-profiles` command reads the shared clean cache and writes one
deterministic report per explicit profile path.

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
- source health output shape: `schemas/source-health.schema.json`
- run manifest shape: `schemas/run-manifest.schema.json`

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
- `tests/test_runtime_paths_and_writers.py`

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
- `src/shared_intake_governance/collector/arxiv_rss_keywords.py`
- `tests/test_github_repo_collector.py`
- `tests/test_arxiv_rss_keywords_collector.py`

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
- `arxiv_rss_keywords` raw Atom feeds map to one clean record per entry.
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
- `tests/test_clean_records_and_projection.py`
- `project-profiles` CLI can run the same projector for multiple explicit
  profile paths from one clean cache.

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

## Handoff rule for the next session

If the next session starts runtime work, it should begin by checking whether the repo still matches this document.

If reality has drifted, update this document before widening the implementation.
