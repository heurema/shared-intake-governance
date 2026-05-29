# 04 — MVP Roadmap

## Phase 0 — Contracts

Goal:

- freeze basic record, profile, and tool-intent schemas;
- freeze trust boundaries;
- define runtime directory layout.

Deliverables:

- docs;
- schemas;
- example profiles.

## Phase 1 — Shared intake

Goal:

- prove `collect once, project many` without any LLM requirement.

Scope:

- one or two source adapters;
- raw cache;
- clean cache;
- sanitizer and risk classifier;
- one projector.

Do not add:

- SQLite;
- daemon;
- provider runtime;
- side-effect execution.

## Phase 2 — Multi-profile projection

Goal:

- feed multiple consumers from the same clean cache.

Scope:

- per-profile filters;
- per-profile scoring;
- per-profile state;
- per-profile reports.
- explicit seen-record updates from generated reports.

Do not add:

- shared scoring state;
- automatic cross-profile decisions.

## Phase 3 — Governance broker

Goal:

- mediate side effects through explicit policy and approvals.

Scope:

- capability classes;
- allowlist and denylist rules;
- audit log;
- dry-run path;
- approval records.
- execution mediation;
- explicit local command execution records.

## Phase 4 — Provider adapters

Goal:

- connect Claude, Gemini, and Vibe through one neutral contract.

Scope:

- thin adapters only;
- no provider-owned policy truth;
- no adapter-specific project logic.
- explicit local provider command invocation records.

## Deferred

- web UI;
- daemon;
- SQLite;
- vector DB;
- plugin marketplace;
- cloud sync;
- multi-user control plane.
