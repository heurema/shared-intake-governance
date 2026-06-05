# 11 — Local Runbook

## Purpose

This runbook shows the smallest current local flow for one tracked source
config and one tracked profile.

It writes runtime data outside the repository. Do not commit runtime output.

## Prerequisites

- Python 3
- Network access to the selected upstream source
- Run commands from the repository root

## Runtime root

Use a runtime root outside git:

```sh
export SIG_RUNTIME_ROOT="$HOME/.local/share/shared-intake-governance"
```

## GitHub repository source

GitHub collectors use unauthenticated API calls by default. To raise rate
limits locally, export `GITHUB_TOKEN` or `GH_TOKEN`; the token is read from the
environment and is not written to runtime artifacts.

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-github"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/github-signum.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
paths for raw metadata, raw body, clean record, projection, run manifest, and
source health.

## GitHub repository search source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-github-search"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/github-search-code-agents.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the GitHub repository search results.

## GitHub releases source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-github-releases"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/github-releases-shared-intake.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the GitHub release results.

## arXiv explicit query source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-arxiv-query"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/arxiv-query-code-agents.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the explicit arXiv query feed.

## RSS feed source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-rss"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/rss-github-blog.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the RSS feed.

## News feed source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-news"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/pulse.json \
  --source-config sources/examples/news-openai-blog.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the news feed.

## Project multiple profiles

Use this after one or more runs have written clean records:

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli project-profiles \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --profile profiles/examples/agent-bench-lab.json \
  --profile profiles/examples/pulse.json \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary with one projection path per profile.
Reports are written under `profiles/<profile-id>/reports/` inside the runtime
root.

To update profile-local seen state from the same generated reports, add the
explicit state flag:

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli project-profiles \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --profile profiles/examples/agent-bench-lab.json \
  --output-id "$SIG_RUN_ID" \
  --update-seen-state
```

This writes or merges `profiles/<profile-id>/state/seen-records.json` for each
projected profile. Without `--update-seen-state`, projection remains report
only.

## Isolated smoke run

Use this when you want a live one-source check without choosing a persistent
runtime root. The command creates a temporary runtime root outside the
repository and writes `SMOKE_RUNTIME_DO_NOT_COMMIT.txt` inside it.

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-smoke"

PYTHONPATH=src python3 -m shared_intake_governance.cli smoke-source-config \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/github-signum.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
`smoke_runtime_root`, `smoke_runtime_policy`, and `runtime_boundary_path`.

## Inspect output

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli list-runs \
  --runtime-root "$SIG_RUNTIME_ROOT"

PYTHONPATH=src python3 -m shared_intake_governance.cli list-clean-records \
  --runtime-root "$SIG_RUNTIME_ROOT"

export SIG_RECORD_ID="github_repo-0c06645da408f813"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-record \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --record-id "$SIG_RECORD_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli list-profile-state \
  --runtime-root "$SIG_RUNTIME_ROOT"

export SIG_STATE_ID="seen-records"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-profile-state \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile-id code-intel-kernel \
  --state-id "$SIG_STATE_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli list-profile-reports \
  --runtime-root "$SIG_RUNTIME_ROOT"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-profile-report \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile-id code-intel-kernel \
  --output-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-run \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli show-source-health \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --source-id github-signum
```

These commands are read-only. They do not fetch upstream sources and do not
write runtime files. `inspect-profile-state` requires an existing
`profile-state.v1` artifact under `profiles/<profile-id>/state/`;
`project-profiles` creates or updates it only when `--update-seen-state` is
provided.

To explicitly update a profile-local seen-records state from one generated
profile report:

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli update-profile-seen-state \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile-id code-intel-kernel \
  --profile-report "$SIG_RUNTIME_ROOT/profiles/code-intel-kernel/reports/$SIG_RUN_ID.json"
```

Expected output is one summary containing `profile_state_path` and the written
`profile-state.v1` object. The command merges report item `record_id` values
with existing state and keeps the resulting `record_ids` deterministic.

## Evaluate a tool intent

Use this for a local policy decision only. It does not execute the requested
tool and does not write approval records.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli evaluate-tool-intent \
  --intent path/to/tool-intent.json
```

Expected output is one `governance-decision.v1` JSON object. Current default
policy allows `read_only`, gates `edit_local`, and denies destructive, external,
or credentialed actions.

To append audit evidence for that evaluation:

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-governance"

PYTHONPATH=src python3 -m shared_intake_governance.cli evaluate-tool-intent \
  --intent path/to/tool-intent.json \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID"
```

This writes one `governance-audit-event.v1` JSONL line under
`audit/<run-id>.jsonl`. Audit events intentionally omit tool intent
`arguments`.

## Record a dry run

Use this to record dry-run evidence from a separate sidecar or manual
simulation. It does not execute the requested tool.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli record-dry-run \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --dry-run-id dry-run-1 \
  --intent path/to/tool-intent.json \
  --dry-run-kind read_only_simulation \
  --result-status passed \
  --recorded-by local-operator \
  --summary "Read-only simulation reviewed." \
  --artifact-ref dry-runs/dry-run-1.json
```

Expected output is one summary containing `dry_run_result_path` and the written
`dry-run-result.v1` object. Dry-run records intentionally omit tool intent
`arguments`.

## Record an approval

Use this only to record a local approval or rejection decision. It does not
execute the requested tool.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli record-approval \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --approval-id approval-1 \
  --intent path/to/tool-intent.json \
  --approval-decision approved \
  --approved-by local-operator \
  --justification "Dry run reviewed." \
  --dry-run-ref dry-runs/approval-1.json
```

Expected output is one summary containing `approval_record_path` and the
written `approval-record.v1` object. Approval records intentionally omit tool
intent `arguments`.

## Mediate a tool intent

Use this after recording dry-run and approval evidence. It writes a local
readiness record only; it does not execute the requested tool.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli mediate-tool-intent \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --mediation-id mediation-1 \
  --intent path/to/tool-intent.json \
  --dry-run-result "$SIG_RUNTIME_ROOT/dry-runs/$SIG_RUN_ID/dry-run-1.json" \
  --approval-record "$SIG_RUNTIME_ROOT/approvals/$SIG_RUN_ID/approval-1.json"
```

Expected output is one summary containing `mediation_record_path` and the
written `execution-mediation.v1` object. `read_only` intents can be `ready`
without dry-run or approval records. Side-effect classes require a matching
`passed` dry-run result and a matching `approved` approval record.

To inspect mediation evidence later:

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli list-mediation-records \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-mediation-record \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --mediation-id mediation-1
```

Both commands are read-only and should not create runtime files.

## Execute a tool intent

Use this only after mediation is `ready` and the exact local command is already
recorded in `tool-intent.v1` `arguments.command`. If mediation is blocked, does
not match the intent scope, or the supplied argv does not exactly match
`arguments.command`, the command is not invoked and a `blocked` execution
result is written.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli execute-tool-intent \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --execution-id execution-1 \
  --intent path/to/tool-intent.json \
  --mediation-record "$SIG_RUNTIME_ROOT/mediation/$SIG_RUN_ID/mediation-1.json" \
  --executed-by local-operator \
  --command path/to/tool-wrapper \
  --arg=--safe-mode \
  --timeout-seconds 30 \
  --metadata-key invocation_mode=explicit
```

The command receives the `tool-intent.v1` JSON on stdin only after the argv
binding check passes. The execution result omits full tool arguments and points
at stdout/stderr artifacts under `tool-executions/<run-id>/`. A zero exit code
records `succeeded`; a nonzero exit or timeout records `failed` with a compact
error object.

## Prepare a provider request

Use this after a `read_only` mediation record is `ready`. It writes a
provider-neutral adapter request only; it does not invoke the provider, execute
tools, read credentials, or translate side-effect mediations into provider
requests. Choose a repo-owned provider preset before preparing the request; the
resolved argv is recorded in the request and must not contain secrets.

Current read-only presets:

- `claude_readonly_local`
- `gemini_readonly_local`
- `agy_readonly_local`
- `vibe_readonly_local`

`claude_readonly_local` intentionally includes a preset-owned instruction
prompt in `resolved_command`. Current Claude CLI behavior is reliable when the
raw `provider-request.v1` JSON arrives on stdin as explicitly labeled
untrusted data; sending the JSON without that framing caused local timeouts.
`agy_readonly_local` targets the local Google `agy` CLI in sandboxed print
mode and also includes preset-owned untrusted-data framing.

Inspect the repo-owned allowlist before preparing a request:

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli list-provider-presets
PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-provider-preset \
  --preset agy_readonly_local
```

These commands do not invoke providers, read credentials, write runtime
artifacts, or discover local commands.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli prepare-provider-request \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --request-id provider-request-1 \
  --mediation-record "$SIG_RUNTIME_ROOT/mediation/$SIG_RUN_ID/mediation-1.json" \
  --preset claude_readonly_local \
  --context-ref profiles/code-intel-kernel/reports/report.json
```

Expected output is one summary containing `provider_request_path` and the
written `provider-request.v1` object. Provider request records intentionally
omit full tool arguments, credentials, raw source text, and provider-specific
policy truth. They include `preset_id`, `resolved_command`, and `command_hash`
from the repo-owned preset allowlist.
Current provider requests and capabilities are `read_only`-only.

## Record a provider result

Use this to record response references and usage metadata from a provider
attempt performed outside this core. It does not invoke the provider or store
full provider responses.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli record-provider-result \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --result-id provider-result-1 \
  --provider-request "$SIG_RUNTIME_ROOT/provider-requests/$SIG_RUN_ID/provider-request-1.json" \
  --result-status succeeded \
  --recorded-by local-operator \
  --summary "Provider completed the request." \
  --response-ref provider-results/provider-result-1.summary.json \
  --usage-key input_tokens=120 \
  --usage-key output_tokens=30
```

For failed or blocked results, provide `--error-kind` and `--error-message`.
Expected output is one summary containing `provider_result_path` and the
written `provider-result.v1` object.

## Invoke a provider request

Use this only for validated `read_only` provider requests and when an operator
has prepared the request from a repo-owned preset. The core does not accept
invoke-time command overrides, discover provider CLIs, load credentials, choose
defaults outside the preset allowlist, or execute the requested tool directly.
For smoke checks, use a fixture request or patched local preset in tests.

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli invoke-provider-request \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --result-id provider-result-1 \
  --provider-request "$SIG_RUNTIME_ROOT/provider-requests/$SIG_RUN_ID/provider-request-1.json" \
  --recorded-by local-operator \
  --timeout-seconds 30 \
  --usage-key invocation_mode=explicit
```

The request `provider`, `resolved_command`, and `command_hash` must match the
request `preset_id` in the repo-owned allowlist. A mismatch records `blocked`
and does not invoke the command. On a match, `resolved_command` receives the
`provider-request.v1` JSON on stdin. Stdout and stderr are written under
`provider-results/<run-id>/` and referenced from the `provider-result.v1`
record. A zero exit code records `succeeded`; a nonzero exit or timeout
records `failed` with a compact error object.

## Reset local runtime data

Only remove runtime data outside the repository:

```sh
rm -rf "$SIG_RUNTIME_ROOT"
```

Do not remove repository files or tracked examples.
