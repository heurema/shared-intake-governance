# 08 — Consumer Onboarding

## Purpose

This document defines how to connect a new consumer project or recipient to the shared intake core.

A consumer can be:

- a research radar;
- a benchmark brief;
- a news or pulse digest;
- a project-specific R&D feed;
- a future governed coding-agent workflow.

## Core idea

Consumers share intake and safety infrastructure.
They do not share product judgment.

That means:

- cache can be shared;
- sanitization can be shared;
- governance contracts can be shared;
- profile scoring, seen state, and outputs remain consumer-specific.

## What a consumer owns

Each consumer should own:

- its purpose;
- its accepted sources;
- its keyword and topic filters;
- its risk tolerance;
- its scoring logic;
- its seen state;
- its report format;
- its publication or action workflow.

## What the shared core owns

The shared core should own only:

- source collection;
- raw evidence storage;
- clean record production;
- shared risk flags;
- governance contracts;
- provider adapter boundaries.

## Where consumer configuration should live

Target model:

- canonical profile lives with the consumer repo;
- local runtime state lives outside git;
- this repository keeps example profiles and shared documentation.

That keeps product semantics close to the actual project while preserving shared runtime reuse.

## Onboarding checklist

Before adding a consumer, answer:

1. What is the consumer trying to decide or produce?
2. Which shared source families are actually relevant?
3. Which keywords or filters matter?
4. Which risk flags must be absent before an item is usable?
5. What report or output mode fits this consumer?
6. Does the consumer require model summarization, or is deterministic projection enough at first?
7. What existing local loop should eventually be replaced or reduced?
8. Which `source-config.v1` file should feed the first reusable one-source run?
9. Where will the local runtime root and profile-local `seen_records` state
   live?
10. What smoke preflight proves the source/profile wiring before persistent
    state is updated?

## Recommended onboarding flow

### Step 1: define the consumer purpose sharply

Bad:

- "general AI updates"

Good:

- "code-intelligence research intake grounded in repository evidence"
- "benchmark mechanics and verifier changes for coding-agent evals"
- "market and product pulse with explicit confidence handling"

Purpose sharpness prevents profile sprawl.

### Step 2: create a minimal profile

Start with the smallest profile that can produce useful output.

The current profile contract includes:

- `profile_id`
- `description`
- `accepted_sources`
- `keywords`
- `required_risk_flags_absent`
- `output_mode`
- `provider_preferences`

See [../schemas/profile.schema.json](../schemas/profile.schema.json).

### Step 3: define the source-config handoff

For a one-source local loop, use the reusable command shape in
[13-source-config-recipes.md](13-source-config-recipes.md). The consumer
handoff should identify only these shared-runtime inputs:

- `SIG_PROFILE`: the profile JSON path selected for this consumer;
- `SIG_SOURCE_CONFIG`: one validated `source-config.v1` file;
- `SIG_RUNTIME_ROOT`: a local runtime data root outside git;
- `SIG_RUN_ID`: the caller's run id.

The profile-local `seen_records` artifact remains runtime state under
`profiles/<profile-id>/state/seen-records.json` inside `SIG_RUNTIME_ROOT`. Do
not move that state into this repository or into a source config.

If a consumer needs to name several reusable source configs, use a
`source-set.v1` file such as
[../sources/sets/code-intel-source-set.json](../sources/sets/code-intel-source-set.json).
That file is only a contract-level list of source-config refs. It is not a
scheduler or batch runner. Use `list-source-sets` to inspect the tracked
source-set catalog and `inspect-source-set` to validate one source-set ref list
before copying the handoff into a consumer repo.

Before wiring a persistent daily caller, run `smoke-source-config` with the same
profile and source config. A smoke run proves fetch, sanitize, projection, and
state-update wiring inside its smoke runtime root only; it does not prove that
the consumer's persistent `seen_records` state has been updated.

### Step 4: decide where outputs live

Keep outputs with the consumer or its runtime area, not in the shared core repo.

Typical ownership split:

- shared core repo:
  - schemas
  - shared adapters
  - shared docs
- consumer repo:
  - canonical profile
  - project-specific scoring
  - project-specific reports
- runtime data root:
  - cache
  - audit
  - local state

### Step 5: run in shadow mode

Before cutting over a consumer from its old loop:

1. feed it from shared clean cache;
2. keep the old loop available;
3. compare item quality, missed signals, and noise;
4. only then remove duplicated upstream fetches.

Shadow mode is the safe default because it proves reuse before deletion.

### Step 6: cut over one consumer at a time

Do not migrate every project simultaneously.

Recommended order:

1. one research-oriented consumer;
2. one benchmark or news-oriented consumer;
3. the remaining consumers after the shared cache path proves stable.

## Consumer examples in this repository

The example profiles show three distinct consumer shapes:

- `code-intel-kernel`
- `agent-bench-lab`
- `pulse`

They are examples, not permanent truth for those projects.

## What not to centralize

Do not centralize these into the shared core:

- per-consumer scoring rules that may diverge;
- editorial or founder-facing framing;
- report templates tightly tied to one repo;
- publication cadence decisions;
- project-specific approval semantics beyond shared governance contracts.

## Common migration mistakes

### Mistake 1: sharing too much

If two consumers care about the same upstream but not the same decision, they should still have separate profiles and outputs.

### Mistake 2: sharing too little

If three consumers fetch the same upstream separately, the architecture is failing its main goal.

### Mistake 3: moving seen state into the core repo

Seen state is runtime data or consumer-owned state, not repo documentation.

### Mistake 4: making a generic profile too early

Prefer three sharp profiles over one vague mega-profile.

## Done criteria

A consumer onboarding is complete when:

1. the consumer purpose is explicit;
2. the profile contract is valid;
3. relevant sources are clear;
4. risk tolerance is explicit;
5. output ownership is clear;
6. source-config handoff inputs are explicit;
7. profile-local `seen_records` ownership is clear;
8. smoke preflight and shadow mode are defined.
