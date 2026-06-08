# 13 - Source Config Recipes

## Purpose

This document keeps reusable local command recipes for consumers that already
use `source-config.v1` files.

It is not a scheduler, wrapper script, daemon, or publication workflow. The
commands below call the existing local CLI directly and keep runtime data
outside git.

## One-source daily new-only pass

Use this when one consumer wants to:

1. fetch one shared source;
2. project only records that are not already in profile-local seen state;
3. mark the newly projected records as seen in the same explicit run.

```sh
export SIG_RUNTIME_ROOT="${SIG_RUNTIME_ROOT:-$HOME/.local/share/shared-intake-governance}"
export SIG_PROFILE="${SIG_PROFILE:-profiles/examples/code-intel-kernel.json}"
export SIG_SOURCE_CONFIG="${SIG_SOURCE_CONFIG:-sources/examples/github-search-code-agents.json}"
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-source-config"

PYTHONPATH=src python3 -m shared_intake_governance.cli run-source-config \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile "$SIG_PROFILE" \
  --source-config "$SIG_SOURCE_CONFIG" \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID" \
  --exclude-seen-state \
  --update-seen-state
```

Expected behavior:

- `--exclude-seen-state` reads
  `profiles/<profile-id>/state/seen-records.json` inside the runtime root when
  it exists and omits matching record ids from the generated projection report;
- `--update-seen-state` merges only the generated report item `record_id`
  values into that same profile-local `seen_records` state artifact;
- the command summary includes `excluded_seen`, `projected_items`,
  `profile_state_id`, `profile_state_path`, and
  `profile_state_record_count`;
- raw payloads, clean records, run manifests, source health, profile reports,
  and profile state stay under the runtime root, not in the repository.

## Consumer substitutions

Consumer repos should usually replace only these values:

- `SIG_PROFILE`: a valid profile JSON path owned by the consumer or passed from
  the consumer's runtime setup;
- `SIG_SOURCE_CONFIG`: one reusable `source-config.v1` JSON file;
- `SIG_RUNTIME_ROOT`: a local runtime data root outside git;
- `SIG_RUN_ID`: a stable run id chosen by the caller.

Do not put credentials, scoring logic, publication targets, or consumer-owned
seen state into a `source-config.v1` file.

Run `inspect-source-config` before wiring a source config into a consumer loop
when you only need to validate the file and inspect normalized defaults.

When a consumer needs a reusable list of several source configs, use a
`source-set.v1` file such as
[../sources/sets/code-intel-source-set.json](../sources/sets/code-intel-source-set.json).
The source set is only a contract-level list of refs; this recipe still runs
one source config at a time. Run `inspect-source-set` first when you need to
verify that the source-set refs still match the tracked source-config files.

## Smoke preflight

Use a smoke run before wiring a persistent daily caller. A smoke runtime root is
temporary and should not be committed.

```sh
export SIG_SMOKE_TEMPLATE="${TMPDIR:-/tmp}/sig-source-config-smoke.XXXXXX"
export SIG_SMOKE_ROOT="$(mktemp -d "$SIG_SMOKE_TEMPLATE")"
export SIG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-source-config-smoke"

PYTHONPATH=src python3 -m shared_intake_governance.cli smoke-source-config \
  --runtime-root "$SIG_SMOKE_ROOT" \
  --profile "$SIG_PROFILE" \
  --source-config "$SIG_SOURCE_CONFIG" \
  --run-id "$SIG_RUN_ID" \
  --output-id "$SIG_RUN_ID" \
  --exclude-seen-state \
  --update-seen-state
```

The smoke command updates only the smoke runtime root's profile-local
`seen_records` state. It does not prove that a consumer's persistent runtime
state has been updated.

## Inspection after a run

```sh
PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-run \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --run-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-profile-report \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile-id code-intel-kernel \
  --output-id "$SIG_RUN_ID"

PYTHONPATH=src python3 -m shared_intake_governance.cli inspect-profile-state \
  --runtime-root "$SIG_RUNTIME_ROOT" \
  --profile-id code-intel-kernel \
  --state-id seen-records
```

Replace `code-intel-kernel` with the `profile_id` from the selected profile.

## Boundaries

This recipe does not:

- define a schedule or automation engine;
- make state updates implicit;
- fetch more than one source config at a time;
- define consumer ranking, formatting, or publication behavior;
- widen failed source paths to fallback sources;
- make external source text trusted.

If a consumer needs a final brief, score, notification, or publication action,
keep that product logic in the consumer repo.
