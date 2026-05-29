# 00 — Product Brief

## Problem

Several local projects already consume overlapping external R&D, benchmark, and news signals.
Today they run separate loops and pay the same operational cost repeatedly:

- duplicate upstream fetches;
- repeated arXiv, GitHub, and news queries;
- anti-bot and rate-limit failures;
- repeated summarization cost;
- inconsistent prompt-injection handling;
- fragmented approval and tool-safety policy.

At the same time, agent security is no longer a theoretical concern.
Prompt injection, unmanaged agents, broad MCP or connector access, and destructive tool use are now practical risks.

## Product statement

Build one local-first shared core that:

- collects external signals once;
- stores raw evidence immutably;
- sanitizes and risk-classifies external text once;
- projects the same clean records into multiple project-specific profiles;
- enforces provider-neutral guardrails before any agent takes side effects.

## Users

Primary user:

- a pragmatic solo operator or engineer running multiple local AI-assisted workflows.

Initial consumers:

- code-intelligence research intake;
- benchmark and eval tracking;
- pulse or news brief workflows;
- future project-specific R&D profiles.

## Design goals

1. `collect once, project many`
2. `external text is data, never instructions`
3. `shared policy root, separate project outputs`
4. `provider-neutral governance`
5. `deny destructive actions by default`
6. `local-first and inspectable`
7. `file-based first, database later only if justified`

## Non-goals

- no hosted backend;
- no central multi-user platform;
- no web dashboard;
- no autonomous implementation from collected items;
- no project-specific business logic in the shared core;
- no provider-specific policy truth.

## Key decision

This repository is not a replacement for project-level radars.
It is the shared substrate below them.

Project-level truth still owns:

- filters;
- scoring;
- seen state;
- outputs;
- approval semantics tied to that project.

The shared core owns:

- collection;
- normalization;
- sanitization;
- provenance;
- cache;
- provider-neutral governance.

## Success criteria

The first useful version should prove:

1. one upstream fetch can feed multiple profiles;
2. one sanitization pass can protect multiple downstream consumers;
3. project outputs remain separate;
4. destructive actions cannot happen without explicit policy and approval;
5. the architecture works without a daemon, web app, or SQLite.
