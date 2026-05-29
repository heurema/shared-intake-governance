# 02 — Data Contracts

## Contract families

The first stable contracts should cover:

1. raw source payload metadata;
2. clean normalized records;
3. run manifests;
4. source health;
5. source configs for one-source local runs;
6. project profiles;
7. profile projection reports;
8. profile-local runtime state;
9. tool intents passed into governance;
10. governance decisions returned by policy evaluation;
11. governance audit events;
12. approval records;
13. dry-run results;
14. execution mediation records;
15. tool execution result records;
16. provider request records;
17. provider result records.

Runtime writers validate artifacts before writing them. Read-only CLI
inspection surfaces also validate runtime artifacts before summarizing or
returning them, because runtime roots may contain hand-edited or corrupted
JSON outside the repository.

## Raw payload metadata

See [../schemas/raw-metadata.schema.json](../schemas/raw-metadata.schema.json).

Minimum fields:

```text
schema_version
run_id
source_id
source_type
fetch_status
fetched_at
request_url
canonical_url
http_status
etag
last_modified
content_type
body_hash
storage_path
collector_version
error
```

Source-specific metadata may add bounded contract fields such as
`source_trust` for `rss` feeds when that value is needed by the sanitizer.

The raw payload body remains outside the clean-record contract.
For failed fetches, `body_hash`, `storage_path`, `canonical_url`, and
`http_status` may be `null`, but the metadata file should still record the
failure as evidence.

Raw metadata files should be written next to raw bodies:

```text
raw/<source_id>/<yyyy-mm-dd>/<body-hash>.body
raw/<source_id>/<yyyy-mm-dd>/<body-hash>.meta.json
```

When there is no body because the fetch failed before a payload existed, the
metadata writer may use an implementation-defined failure filename under the
same source/date directory. The metadata contract, not the filename, is the
source of truth.
Runtime code validates raw metadata before writing it and before the sanitizer
consumes it. Sanitizer raw body reads must stay under the configured runtime
raw root.

## Clean record

See [../schemas/clean-record.schema.json](../schemas/clean-record.schema.json).

Important properties:

- one clean record maps to one canonical external item;
- `sanitized_summary` is safe model input;
- `risk_flags` and `quarantined` are explicit;
- `raw_hash` preserves traceability back to raw evidence;
- the contract is provider-neutral.

Clean record fields are already frozen for Phase 1 by
`schemas/clean-record.schema.json`. Runtime code should validate emitted clean
records against that schema before projection.

## Run manifest

See [../schemas/run-manifest.schema.json](../schemas/run-manifest.schema.json).

A run manifest records one invocation of the local pipeline. It should include:

```text
schema_version
run_id
mode
status
started_at
finished_at
runtime_root
raw_root
clean_root
profiles_root
sources
counts
source_health
```

The manifest is operational evidence. It should not contain credentials,
private source payload text, or generated reports.
Runtime code validates run manifests before writing them.

## Source health

See [../schemas/source-health.schema.json](../schemas/source-health.schema.json).

Source health records how one source behaved during one run.

Minimum fields:

```text
schema_version
run_id
source_id
source_type
status
checked_at
attempted_fetches
successful_fetches
failed_fetches
raw_records_written
degraded_reasons
last_error
next_retry_after
```

If a source is degraded or failed, downstream consumers should see that state
explicitly. Do not silently widen to weaker fallback sources.
Runtime code validates source health artifacts before writing them.

## Source config

See [../schemas/source-config.schema.json](../schemas/source-config.schema.json).

A source config defines exactly one reusable source input for a local run.
It exists so source definitions can live in files instead of only in CLI
arguments.

Supported Phase 1 source configs:

- `github_repo`
- `github_search`
- `arxiv_rss_keywords`
- `arxiv_query`
- `rss`

Source configs must not contain credentials, runtime state, scoring rules,
profile logic, or publication semantics.
Runtime code validates source configs before dispatching a source run.

## Profile config

See [../schemas/profile.schema.json](../schemas/profile.schema.json).

A profile may define:

- sources it accepts;
- keyword and source filters;
- scoring hints;
- output paths or logical output ids;
- optional provider preferences for summarization only.

Profiles must not define:

- destructive action permissions;
- credential material;
- adapter internals.

## Profile projection

See [../schemas/profile-projection.schema.json](../schemas/profile-projection.schema.json).

Profile projection reports are deterministic runtime artifacts produced from
the clean cache and one explicit profile. They preserve enough provenance for
consumer repos to apply their own ranking, report formatting, publication, or
dedupe decisions without re-reading raw source payloads.

Minimum fields:

```text
schema_version
profile_id
output_mode
generated_at
counts
items
```

Projection items intentionally include sanitized summary text, risk flags,
source trust, canonical URL, and raw hash. They must not include credentials,
provider prompts, model outputs, or consumer-specific editorial decisions.
Runtime code validates projection reports before writing them and before using
them to update profile-local seen state.

## Profile state

See [../schemas/profile-state.schema.json](../schemas/profile-state.schema.json).

Profile state is profile-local runtime data, not repository truth and not shared
scoring state. The shared core may define an inspectable artifact shape, but
consumer repos still own product semantics such as publication cadence, final
report meaning, and dedupe policy.

Minimum fields:

```text
schema_version
profile_id
state_id
state_kind
updated_at
record_ids
```

The first `profile-state.v1` shape is intentionally small. It is suitable for
state inventories such as seen record ids or cursors, but it must not be used
to encode project-specific ranking or editorial decisions.
Runtime code validates profile state before consuming existing state and before
writing updated state.

The current `seen_records` update paths are explicit: `update-profile-seen-state`
merges record ids from one `profile-projection.v1` report into one
profile-local state file, and `project-profiles --update-seen-state` applies
the same merge to each generated profile report. Projection does not update
state unless that flag is provided, and the core still does not define consumer
publication or dedupe policy.

## Profile loading rules

Phase 1 profile loading should stay explicit and file-based:

- load profiles from an explicit path or a known example path;
- validate profiles against `schemas/profile.schema.json`;
- treat `required_risk_flags_absent` as `[]` when omitted;
- do not discover profiles by scanning arbitrary repositories;
- do not load credentials or provider adapter config from profiles;
- keep canonical consumer profiles in the consumer repo when they stop being
  examples.

## Tool intent

See [../schemas/tool-intent.schema.json](../schemas/tool-intent.schema.json).

The agent does not execute side effects directly.
It emits a tool intent for governance review.

Minimum properties:

```text
intent_id
profile_id
action_class
tool_name
arguments
dry_run_supported
justification
evidence_refs
```

Runtime code validates tool intents before governance policy, approval, dry-run,
mediation, or execution helpers consume them.

## Governance decision

See [../schemas/governance-decision.schema.json](../schemas/governance-decision.schema.json).

The first governance runtime slice evaluates one intent and returns a decision.
It can also append a minimal audit event when a runtime root and run id are
explicitly provided. It does not execute tools, create approvals, call
providers, or mutate unrelated runtime state.

Minimum properties:

```text
schema_version
intent_id
profile_id
action_class
tool_name
decision
reason
dry_run_supported
evidence_refs
```

Runtime code validates governance decisions before returning them from the
default evaluator, including optional audit references when audit logging is
requested.

## Governance audit event

See [../schemas/governance-audit-event.schema.json](../schemas/governance-audit-event.schema.json).

Governance audit events are append-only JSONL records under:

```text
audit/<run-id>.jsonl
```

Minimum properties:

```text
schema_version
run_id
event_type
recorded_at
intent_id
profile_id
action_class
tool_name
decision
reason
dry_run_supported
evidence_refs
tool_intent_path
```

Audit events should record the decision surface, not the full tool arguments.
Do not log secrets, credentials, private payloads, or unneeded side-effect
arguments into audit JSONL.
Runtime code validates governance audit events before appending them.

## Approval record

See [../schemas/approval-record.schema.json](../schemas/approval-record.schema.json).

Approval records are explicit local records that an operator approved or
rejected one tool intent. They do not execute the requested tool and do not
replace the later dry-run sidecar or execution mediation.

Approval records are written under:

```text
approvals/<run-id>/<approval-id>.json
```

Minimum properties:

```text
schema_version
run_id
approval_id
intent_id
profile_id
action_class
tool_name
approval_decision
approved_by
approved_at
justification
dry_run_ref
evidence_refs
tool_intent_path
```

Approval records should not include full tool arguments, credentials, or
private payloads. A later executor must still enforce policy, check approval
scope, and require dry-run evidence where applicable.
Runtime code validates approval records before writing them.

## Dry-run result

See [../schemas/dry-run-result.schema.json](../schemas/dry-run-result.schema.json).

Dry-run results are recorded evidence from a dry-run sidecar. The first runtime
slice records the result and artifact references, but does not execute the tool
itself and does not mediate side effects.

Dry-run results are written under:

```text
dry-runs/<run-id>/<dry-run-id>.json
```

Minimum properties:

```text
schema_version
run_id
dry_run_id
intent_id
profile_id
action_class
tool_name
dry_run_kind
result_status
recorded_by
recorded_at
summary
artifact_refs
evidence_refs
tool_intent_path
```

Dry-run results should not include full tool arguments, credentials, or private
payloads. They should point at external artifacts or summaries that can be
reviewed before an approval record is created.
Runtime code validates dry-run results before writing them.

## Execution mediation

See [../schemas/execution-mediation.schema.json](../schemas/execution-mediation.schema.json).

Execution mediation records are pre-execution readiness decisions. They combine
the default policy decision with optional dry-run and approval evidence. They
do not execute the requested tool, call providers, or grant capability by
themselves.

Mediation records are written under:

```text
mediation/<run-id>/<mediation-id>.json
```

Minimum properties:

```text
schema_version
run_id
mediation_id
mediated_at
intent_id
profile_id
action_class
tool_name
policy_decision
mediation_decision
reason
dry_run_result_path
approval_record_path
tool_intent_path
evidence_refs
```

Default mediation behavior:

- `read_only` intents may become `ready` without dry-run or approval evidence;
- side-effect classes require a matching `passed` dry-run result and a matching
  `approved` approval record;
- mismatched or missing evidence blocks mediation;
- mediation records should store refs and decision fields only, not full tool
  arguments, credentials, or private payloads.
Runtime code validates any provided `dry-run-result.v1` and
`approval-record.v1` evidence before mediation consumes it, then validates the
`execution-mediation.v1` record before writing it.

## Tool execution result

See [../schemas/tool-execution-result.schema.json](../schemas/tool-execution-result.schema.json).

Tool execution results record one explicit local command attempt after
`execution-mediation.v1` is `ready`. They do not discover commands, load
credentials, choose default tools, parse shell strings, or store full tool
intent arguments in the result.

Tool execution results are written under:

```text
tool-executions/<run-id>/<execution-id>.json
tool-executions/<run-id>/<execution-id>.stdout.txt
tool-executions/<run-id>/<execution-id>.stderr.txt
```

Minimum properties:

```text
schema_version
run_id
execution_id
intent_id
profile_id
action_class
tool_name
executed_by
executed_at
execution_status
summary
tool_intent_path
mediation_record_path
output_refs
execution_metadata
error
evidence_refs
```

If mediation is blocked or mismatched, the executor must write a `blocked`
result and must not invoke the supplied command. Successful and failed
executions should point at output artifacts instead of embedding command output
or tool arguments.
Runtime code validates the input `execution-mediation.v1` record before
consuming it, then validates tool execution results before writing them.

## Provider request

See [../schemas/provider-request.schema.json](../schemas/provider-request.schema.json).

Provider requests are provider-neutral adapter boundary records. They are
prepared from a ready execution mediation record and contain the provider name,
governance-derived capabilities, and context references. They do not invoke a
provider, execute tools, discover credentials, or grant capability by
themselves.

Provider requests are written under:

```text
provider-requests/<run-id>/<request-id>.json
```

Minimum properties:

```text
schema_version
run_id
request_id
prepared_at
provider
mediation_record_path
mediation_id
intent_id
profile_id
action_class
tool_name
policy_decision
mediation_decision
capabilities
context_refs
evidence_refs
```

Provider request records should not include full tool arguments, credentials,
raw source text, private payloads, or provider-specific policy truth.
Adapters must still enforce their own narrow translation boundary and must not
expand capabilities beyond the governance-derived request.
Runtime code validates provider requests before writing them.
Runtime code also validates the ready execution mediation record before
preparing a provider request.

## Provider result

See [../schemas/provider-result.schema.json](../schemas/provider-result.schema.json).

Provider results are adapter boundary records for response refs and usage
metadata. They may be recorded manually from a provider request or written by
the explicit local invocation runner. They do not store full provider
responses.

Provider results are written under:

```text
provider-results/<run-id>/<result-id>.json
provider-results/<run-id>/<result-id>.stdout.txt
provider-results/<run-id>/<result-id>.stderr.txt
```

Minimum properties:

```text
schema_version
run_id
result_id
request_id
provider
recorded_by
recorded_at
result_status
summary
provider_request_path
mediation_id
intent_id
profile_id
action_class
tool_name
response_refs
usage_metadata
error
evidence_refs
```

Provider result records should point at response artifacts or summaries rather
than embedding full responses. They should not include credentials, tool
arguments, raw source text, private payloads, or provider-specific policy truth.
Failed or blocked results should include a compact error object.
Runtime code validates provider results before writing them.
Runtime code also validates provider requests before recording provider results
or forwarding request JSON to an explicit local provider command.

## Capability classes

The governance broker should classify actions into at least:

```text
read_only
edit_local
destructive_local
external_side_effect
credentialed_remote
```

Default policy:

- `read_only`: allowed
- `edit_local`: gated
- `destructive_local`: denied unless explicitly approved
- `external_side_effect`: denied unless explicitly approved
- `credentialed_remote`: denied unless explicitly approved
