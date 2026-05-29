# 02 — Data Contracts

## Contract families

The first stable contracts should cover:

1. raw source payload metadata;
2. clean normalized records;
3. project profiles;
4. tool intents passed into governance.

## Raw payload metadata

Minimum fields:

```text
source_id
fetched_at
request_url
canonical_url
http_status
etag
last_modified
content_type
body_hash
storage_path
```

The raw payload body remains outside the clean-record contract.

## Clean record

See [../schemas/clean-record.schema.json](../schemas/clean-record.schema.json).

Important properties:

- one clean record maps to one canonical external item;
- `sanitized_summary` is safe model input;
- `risk_flags` and `quarantined` are explicit;
- `raw_hash` preserves traceability back to raw evidence;
- the contract is provider-neutral.

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
