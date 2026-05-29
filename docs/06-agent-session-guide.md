# 06 — Agent Session Guide

## Purpose

This document tells a new agent how to work in this repository without relying on prior chat context.

Use it when:

- you entered from another project and need to understand this repo quickly;
- you need to continue design or implementation work;
- you need to add a source, consumer, or safety rule;
- you need to decide what belongs in this core versus a consumer repo.

## One-sentence mental model

This repository is the local shared substrate that collects external evidence once, sanitizes it once, and safely feeds multiple project-specific consumers without becoming a service or swallowing their product logic.

## What to confirm first

Before changing anything, confirm these facts from the file tree:

1. whether runtime code exists yet;
2. which docs are already canonical;
3. whether the requested change belongs to shared core or to a consumer repo;
4. whether the requested change is docs-only, contract-only, or runtime work.

At the time of writing, this repo is still docs-first.

## Default read order for a fresh session

1. `README.md`
2. `AGENTS.md`
3. `docs/INDEX.md`
4. `docs/00-product-brief.md`
5. `docs/01-architecture.md`
6. `docs/02-data-contracts.md`
7. the task-specific playbook:
   - `docs/07-source-onboarding.md`
   - `docs/08-consumer-onboarding.md`
   - `docs/09-operating-model.md`
   - `docs/10-implementation-guide.md`

## What belongs here

This repository should contain shared concerns only:

- source adapters and collector contracts;
- raw and clean cache contracts;
- sanitizer and risk flags;
- governance broker contracts;
- provider adapter contracts;
- common operating model;
- reusable onboarding rules for sources and consumers.

## What does not belong here

Do not put these things in the shared core:

- project-specific editorial judgment;
- project-specific report formatting rules;
- project-specific scoring truth;
- consumer-owned seen state in git;
- credentials;
- per-project publication workflows;
- provider-specific policy truth.

## Decision filter

When a request comes in, classify it first.

### Case 1: "Add or fix a source"

This belongs here only if the source is reusable across more than one consumer or is logically part of the shared intake substrate.

If it is a one-off scrape or one project's local workaround, it probably belongs in that consumer repo instead.

### Case 2: "Add a new recipient or project"

This repo should document how to onboard the consumer and may eventually provide shared runtime support.

The consumer's canonical profile and outputs should still live with the consumer unless there is a specific reason not to.

### Case 3: "Add safety or governance"

This belongs here if it is provider-neutral and reusable:

- prompt-injection defenses;
- risk flags;
- capability classes;
- approval boundaries;
- audit contracts.

### Case 4: "Add a provider-specific behavior"

Only adapter translation belongs here.
Provider-specific policy should not override the shared governance model.

### Case 5: "Add product logic"

Stop and push it back to the consumer repo.

## Default execution posture

Prefer the smallest reversible step:

1. docs
2. contract
3. local runtime slice
4. tests
5. only later provider integration

Do not skip directly to a broad runtime if the contract or boundary is still unclear.

## How to continue implementation safely

If runtime work starts, keep the initial path strict:

- local only;
- file-based only;
- read-only intake first;
- no LLM required for Phase 1;
- no side effects without ready mediation and an explicit local command.

That means the first runtime cut should prove:

- shared fetch;
- raw cache write;
- clean record emission;
- projection into one profile.

## When entering from another project

If you arrived from a consumer repo:

1. identify whether that repo needs a new source, a new profile, or shared runtime support;
2. do not drag that repo's specific report semantics into this core;
3. keep consumer-specific outputs and seen state outside this repo;
4. if needed, document the integration path here and keep the consumer-specific change there.

## What a good handoff looks like

A good session here should leave behind at least one of:

- clearer docs;
- tighter contracts;
- example profile updates;
- a narrower implementation plan;
- a small tested runtime slice.

A bad session here adds broad abstractions, runtime sprawl, or provider-specific policy without proving the shared need.
