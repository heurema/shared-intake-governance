# 02 — Data Contracts

## Contract families

The first stable contracts should cover:

1. raw source payload metadata;
2. clean normalized records;
3. run manifests;
4. source health;
5. project profiles;
6. tool intents passed into governance.

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
