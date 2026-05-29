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

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-run \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli show-source-health \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID" \
  --source-id github-signum
```

These commands are read-only. They do not fetch upstream sources and do not
write runtime files.

## Reset local runtime data

Only remove runtime data outside the repository:

```sh
rm -rf "$SIG_RUNTIME_ROOT"
```

Do not remove repository files or tracked examples.
