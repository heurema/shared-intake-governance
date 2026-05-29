# 03 — Provider Adapters

## Purpose

Provider adapters translate a provider-neutral request into a provider-specific invocation.

They are not:

- policy engines;
- profile owners;
- cache owners;
- sanitizers.

## Boundary

The shared core owns:

- source collection;
- sanitization;
- risk flags;
- policy;
- approvals;
- audit.

Adapters own only:

- request translation;
- provider invocation;
- response capture;
- usage metadata.

## Provider roles

### Claude

Best fit:

- interactive reviewed coding sessions;
- narrow tool scopes;
- human-in-the-loop editing and review.

Adapter concerns:

- explicit tool allow or deny lists;
- bare or reduced-context mode where needed;
- never use permission bypass modes from core policy.

### Gemini

Best fit:

- managed automation with stronger external policy surface;
- approval-mode and policy-file driven execution;
- high-governance workflows.

Adapter concerns:

- approval mode mapping;
- policy and admin-policy mapping;
- extension, hook, and MCP scope control.

### Vibe

Best fit:

- bounded low-friction worker;
- cost-capped or token-capped execution;
- narrow prompt or transformation tasks behind external guardrails.

Adapter concerns:

- agent preset mapping;
- narrow tool enablement;
- explicit budget boundaries.

## Shared adapter interface

Suggested logical interface:

```text
run(request, capabilities, context) -> result
```

Where:

- `request` is provider-neutral;
- `capabilities` comes from governance, not the adapter;
- `context` points to clean records and profile outputs only.

## Hard rules

Adapters must not:

- read raw untrusted payloads directly;
- expand tool permissions;
- carry embedded project-specific policy;
- store secrets in repo files;
- auto-approve destructive actions.
