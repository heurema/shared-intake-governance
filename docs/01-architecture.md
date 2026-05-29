# 01 — Architecture

## Conceptual architecture

```text
upstream sources
  -> shared collector
  -> raw cache
  -> sanitizer and risk classifier
  -> clean cache
  -> per-profile projector
  -> profile reports and state
  -> optional summarizer
  -> governance broker
  -> provider adapter
  -> dry-run sidecar
  -> approval gate
  -> side effects, if approved
```

## Architectural principles

1. **Local-first:** no cloud control plane is required.
2. **Data before model:** collect and normalize before any LLM involvement.
3. **Data is untrusted:** external source text is never treated as instructions.
4. **Provider-neutral policy:** governance lives above adapters.
5. **Project separation:** profiles stay independent even when cache is shared.
6. **Small reversible slices:** prove the file-based path before adding runtime complexity.

## Main components

### 1. Shared collector

Responsibilities:

- fetch source payloads;
- apply source-specific retry and backoff;
- capture ETag or Last-Modified when available;
- write immutable raw payloads and fetch metadata;
- avoid scoring, summarization, and side effects.

### 2. Raw cache

Suggested runtime layout:

```text
~/.local/share/shared-intake-governance/
  raw/
    <source>/
      <yyyy-mm-dd>/
        <sha256>.json
        <sha256>.meta.json
```

The raw cache is evidence only.

### 3. Sanitizer and risk classifier

Responsibilities:

- normalize Unicode and whitespace;
- strip markup and control characters;
- cap field lengths;
- preserve canonical URL and attribution;
- classify suspicious instruction-like content;
- emit normalized clean records.

### 4. Clean cache

Suggested runtime layout:

```text
~/.local/share/shared-intake-governance/
  clean/
    <record-hash>.json
```

### 5. Per-profile projector

Each consumer profile reads the same clean cache and writes only its own state and outputs.

Suggested runtime layout:

```text
~/.local/share/shared-intake-governance/
  profiles/
    <profile>/
      state/
      reports/
```

### 6. Optional summarizer

If a model step is needed, it must read only clean records.

Cache key:

```text
record_hash + prompt_hash + provider + model
```

### 7. Governance broker

The governance broker owns:

- capability classes;
- allowlist and denylist rules;
- destructive-command classification;
- approval requirements;
- credential scope;
- audit trail.

### 8. Provider adapters

Adapters are thin translation layers only:

- `claude`
- `gemini`
- `vibe`

They must not hold policy truth or widen capabilities.

### 9. Dry-run sidecar

Any action with side effects should have a dry-run path first.

Preferred forms:

- disposable worktree;
- sandboxed container;
- read-only simulation;
- test-only execution path.

## Trust boundaries

1. `network -> raw cache`
   fetched bytes are untrusted.
2. `raw cache -> clean cache`
   sanitization and risk classification happen here.
3. `clean cache -> model context`
   untrusted text stays in explicit data fields only.
4. `plan -> side effect`
   approval and policy checks happen here.

## Storage decision

Start file-based.

Do not add SQLite until one of these becomes real:

- file scans are measurably slow;
- cross-profile lookup is painful;
- audit analysis needs indexed joins;
- cache size makes file-only traversal too expensive.
