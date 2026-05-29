# 09 — Operating Model

## Purpose

This document explains how the shared core should operate day to day once runtime slices exist.

It is intentionally more operational than the architecture doc.

## End-to-end flow

The intended steady-state flow is:

```text
collect once
  -> write raw evidence
  -> sanitize once
  -> write clean records
  -> project many profiles
  -> optionally summarize from clean records
  -> if action is requested, send tool intent through governance
```

The critical point is that shared intake stops at evidence and safe projection unless a later stage explicitly asks for action.

## Runtime roots

The runtime data root should stay outside git:

```text
~/.local/share/shared-intake-governance/
```

Suggested layout:

```text
raw/
  <source_id>/
    <yyyy-mm-dd>/
      <body-hash>.body
      <body-hash>.meta.json
clean/
  <record-id>.json
runs/
  <run-id>.manifest.json
source-health/
  <run-id>/
    <source-id>.json
audit/
  <run-id>.jsonl
profiles/
  <profile-id>/
    state/
    reports/
```

Keep repository docs and runtime data separate.

The canonical contract files for these runtime artifacts are:

- [../schemas/raw-metadata.schema.json](../schemas/raw-metadata.schema.json)
- [../schemas/clean-record.schema.json](../schemas/clean-record.schema.json)
- [../schemas/run-manifest.schema.json](../schemas/run-manifest.schema.json)
- [../schemas/source-health.schema.json](../schemas/source-health.schema.json)
- [../schemas/profile.schema.json](../schemas/profile.schema.json)

## Modes of operation

### 1. Backfill mode

Use when bootstrapping a source or rebuilding history.

Constraints:

- read-only intake only;
- bounded time window;
- no governance actions;
- explicit source pacing.

### 2. Daily collection mode

Use for recurring collection once the pipeline is stable.

Goal:

- fetch shared upstreams once;
- sanitize once;
- update multiple consumers from the same clean cache.

### 3. Shadow mode

Use when migrating a consumer from an existing local loop.

Goal:

- prove the shared cache can replace duplicate fetches;
- compare item quality and failure patterns before cutover.

### 4. Governance mode

Use only after collection and projection are already useful.

Goal:

- take proposed tool intents;
- classify capabilities;
- enforce dry-run and approval rules;
- record audit evidence.

## Health surfaces

Even before a UI exists, the runtime should record:

- source health per run;
- fetch errors and degradation reasons;
- raw write count;
- clean record count;
- per-profile projected item count;
- quarantine count;
- retry count when meaningful.

If a source is degraded, the system should say so explicitly instead of hiding it behind silence.

Current CLI behavior:

- `run-github-repo` writes one run manifest under `runs/`;
- `run-arxiv-rss-keywords` writes one run manifest under `runs/`;
- `run-source-config` reads one `source-config.v1` JSON file and writes one
  run manifest under `runs/`;
- `smoke-source-config` runs one `source-config.v1` JSON file with a smoke
  runtime root outside the repository and writes a do-not-commit marker;
- `project-profiles` reads existing clean records and writes one deterministic
  report per explicit profile path;
- `list-runs` reads existing run manifests and returns a deterministic
  inventory without writing runtime data;
- `list-clean-records` reads existing clean records and returns a deterministic
  inventory without writing runtime data;
- `inspect-record` reads one clean record by record id without writing runtime
  data;
- `list-profile-reports` reads generated profile reports and returns a
  deterministic inventory without writing runtime data;
- `inspect-profile-report` reads one profile report by profile id and output id
  without writing runtime data;
- `inspect-run` reads one run manifest and summarizes linked source health
  artifacts without writing runtime data;
- `show-source-health` reads one source health artifact without writing
  runtime data;
- all current run commands write one source health artifact under
  `source-health/`.

## Cost discipline

The architecture is meant to lower cost, not redistribute it invisibly.

Required discipline:

- fetch once for overlapping consumers;
- sanitize once;
- summarize only when a consumer truly needs it;
- cache model outputs by record and prompt when summarization exists;
- avoid duplicate downstream work when the same clean record is reused.

## Security posture during operation

Operationally, assume:

- network payloads are untrusted;
- raw cache is evidence, not model input;
- clean records are safer, not "trusted";
- risky items can still be quarantined and excluded;
- no action may cross into side effects without governance mediation.

## Failure handling

When a source fails:

1. record the failure;
2. record source health;
3. keep the run inspectable;
4. do not silently widen to weak fallback sources unless documented;
5. avoid poisoning downstream consumers with invented or partial results.

When sanitization fails:

1. preserve raw evidence;
2. fail closed for the affected item;
3. quarantine if partial interpretation could be unsafe.

## Cutover philosophy

Shared intake should replace duplicate fetches gradually.

The recommended cutover sequence is:

1. one shared source path
2. one consumer projection
3. one shadowed migration
4. one removal of duplicated upstream fetch
5. repeat

Avoid synchronized big-bang migrations across all consumers.

## What "good" looks like

A healthy operating model eventually gives:

- one fetch per upstream family per run;
- one sanitization pass per item;
- multiple consumers fed from the same clean cache;
- explicit degraded-source reporting;
- no hidden side effects;
- a readable audit trail when governance later exists.
