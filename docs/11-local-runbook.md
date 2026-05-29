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

## Inspect output

```sh
find "$SIG_RUNTIME_ROOT/runs" -type f -name '*.manifest.json'
find "$SIG_RUNTIME_ROOT/source-health" -type f -name '*.json'
find "$SIG_RUNTIME_ROOT/profiles/code-intel-kernel/reports" -type f -name '*.json'
```

## Reset local runtime data

Only remove runtime data outside the repository:

```sh
rm -rf "$SIG_RUNTIME_ROOT"
```

Do not remove repository files or tracked examples.
