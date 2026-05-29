# 05 — Threat Model

## Main threats

### 1. Prompt injection from external content

Risk:

- source text contains imperative instructions or tool-shaped payloads;
- downstream model treats them as instructions instead of data.

Mitigations:

- raw and clean cache separation;
- explicit data-only wrapping;
- risk flags and quarantine;
- no mutation-capable tools when processing external text.

### 2. Unmanaged agent with tool access

Risk:

- agent receives filesystem, network, or connector access without central policy mediation;
- destructive behavior happens through normal tools rather than model hallucination alone.

Mitigations:

- provider-neutral governance broker;
- deny destructive classes by default;
- explicit approval gate;
- tool intents instead of direct side effects.

### 3. Credential blast radius

Risk:

- broad tokens or shared credentials allow one compromised workflow to affect unrelated systems.

Mitigations:

- scoped credentials;
- per-profile or per-run credential mapping;
- no secrets in repo files;
- audit of credentialed actions.

### 4. False trust in sanitizer

Risk:

- one sanitizer bug propagates bad assumptions to every profile.

Mitigations:

- immutable raw cache;
- sanitizer versioning;
- re-sanitization support;
- defense-in-depth at model call boundaries.

### 5. Approval theater

Risk:

- approval exists on paper, but risky actions are still effectively auto-approved through broad presets.

Mitigations:

- capability classes;
- explicit dry-run output review;
- separate destructive and external-side-effect classes;
- audit trail for every approved action.

## Default security posture

Before later phases, the system should still be safe if:

- no provider commands are explicitly invoked;
- no LLM summarizer is used;
- only collection, sanitization, and projection run.

That makes the shared core useful before the highest-risk execution surfaces exist.
