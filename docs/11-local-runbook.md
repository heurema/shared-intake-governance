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

## arXiv keyword source

```sh
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-arxiv"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile profiles/examples/code-intel-kernel.json \
  --source-config sources/examples/arxiv-code-agents.json \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID"
```

Expected output is one JSON summary printed to stdout. The summary includes
all clean record paths emitted from the Atom feed.

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
`profile-state.v1` artifact under `profiles/<profile-id>/state/`; current
projector commands do not create or update profile state.

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

## Reset local runtime data

Only remove runtime data outside the repository:

```sh
rm -rf "$SIG_RUNTIME_ROOT"
```

Do not remove repository files or tracked examples.
