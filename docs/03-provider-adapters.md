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
- `capabilities` comes from governance, not the adapter; in the current runtime
  this boundary accepts only `read_only`;
- `context` points to clean records and profile outputs only.

The first runtime boundary for this interface is the local
`provider-request.v1` artifact. It is prepared from a ready mediation record and
contains provider, capability, bound command argv, context, and evidence
references only. It does not invoke the provider.

The paired `provider-result.v1` artifact records response references, summary,
usage metadata, and compact errors after a provider attempt is externally
performed or simulated. It should not embed full provider responses.

The current local invocation runner is deliberately narrower than a provider
SDK adapter. It consumes one validated `provider-request.v1` file, runs only
the explicit command supplied by the operator when it exactly matches the
request-bound command argv, passes the request JSON on stdin, stores
stdout/stderr as runtime artifacts, and writes a `provider-result.v1` record.
It does not discover provider CLIs, load credentials, choose defaults, or
execute requested tools directly.

## Hard rules

Adapters must not:

- read raw untrusted payloads directly;
- expand tool permissions;
- carry embedded project-specific policy;
- store secrets in repo files;
- auto-approve destructive actions.
- invent provider commands or credentials.
