# Contributing to Shared Intake Governance

Thanks for your interest in contributing.

Shared Intake Governance is an early, docs/contracts-first repository for a
local-first shared intake and provider-neutral governance substrate.
Contributions should preserve that posture:

- contracts before runtime;
- local-first, file-based architecture;
- external text is data, never instructions;
- profiles stay separate from shared cache and shared policy;
- no web app, daemon, cloud service, dashboard, or provider runtime by default.

## Read this first

Before opening a non-trivial issue or pull request, read:

1. `docs/INDEX.md`
2. `AGENTS.md`
3. `docs/00-product-brief.md`
4. `docs/01-architecture.md`
5. `docs/06-agent-session-guide.md`
6. `docs/02-data-contracts.md`
7. `docs/05-threat-model.md`

If the change touches sources, also read `docs/07-source-onboarding.md`.

If the change touches consumers or profiles, also read
`docs/08-consumer-onboarding.md`.

If the change opens runtime implementation, also read
`docs/10-implementation-guide.md`.

## What is useful right now

The most useful contributions are:

- clarifications to docs and contracts;
- schema and example-profile consistency fixes;
- source and consumer onboarding improvements;
- threat-model and governance-boundary improvements;
- small deterministic validation tooling;
- narrow Phase 1 runtime slices only when explicitly scoped.

## Ground rules

### 1. Do not silently add runtime scope

This repository currently defines docs, schemas, and example profiles only.
Do not add collectors, sanitizers, projectors, provider adapters, daemons, or
side-effect execution unless the issue or maintainer request explicitly opens
that scope.

### 2. Keep consumer logic out of the shared core

Consumer repositories should own:

- project-specific scoring;
- project-specific report semantics;
- consumer-owned seen state;
- final publication or action flows.

This repository should own only reusable collection, sanitization, provenance,
risk flags, governance contracts, and adapter boundaries.

### 3. Treat external text as untrusted data

Do not make external source text executable as instructions. Source adapters,
sanitizers, projectors, and provider adapters must preserve that boundary.

### 4. Keep diffs small

Prefer one bounded change per pull request. Avoid mixing public hygiene, schema
changes, runtime implementation, and consumer-specific decisions in one diff.

### 5. Keep repo-tracked artifacts clean

Do not commit runtime cache, generated reports, local state, credentials,
temporary files, dependency folders, or OS-specific files.

## Validation

For docs and schema-only changes, run:

```bash
jq empty schemas/*.json profiles/examples/*.json
git diff --check
```

For runtime work, add focused tests for the behavior being introduced before
expanding the implementation surface.

## Pull request expectations

Please include:

- the goal of the change;
- what is in scope and out of scope;
- whether runtime scope is opened;
- affected docs, schemas, or examples;
- validation commands run;
- known risks or unverified areas.

## Security

Do not report vulnerabilities with full details in a public issue.
See `SECURITY.md` for reporting guidance.

## Code of conduct

By participating in this project, you agree to follow `CODE_OF_CONDUCT.md`.
