# 12 — Current Surface Audit

## Purpose

This document records the current source-of-truth surface before widening
runtime scope again.

It is not a roadmap and not a release note. Use it to distinguish:

- implemented and locally verified surfaces;
- explicit deferred scope;
- next safe expansion boundaries.

## Audit date

2026-06-08

## Current completion boundary

As of this audit, the non-deferred docs/contracts/runtime surface described in
the verified entrypoints below is implemented and locally verified.

This does not mean the repository is a finished hosted product or broad
automation platform. The remaining not-yet-implemented areas are explicit
deferred scope and require a new behavior decision before implementation.

## Verified source-of-truth entrypoints

- `README.md`
- `docs/INDEX.md`
- `docs/08-consumer-onboarding.md`
- `docs/10-implementation-guide.md`
- `docs/11-local-runbook.md`
- `docs/13-source-config-recipes.md`
- `AGENTS.md`

## Implemented source families

The current local runtime has read-only collectors, source config dispatch,
clean-record emission, projection support, source-health output, and run
manifest output for:

- `github_repo`
- `github_releases`
- `github_search`
- `arxiv_query`
- `rss`
- `news`

`custom` remains a contract-level source type for consumer-owned or future
runtime paths. It does not currently have a shared collector or source-config
dispatch path.
The retired `arxiv_rss_keywords` family is not active source surface because it
duplicated arXiv API query transport under an RSS/feed name. Use `arxiv_query`
for arXiv API query transport or `rss` for explicit feed transport.

## Implemented runtime boundaries

Current runtime code covers:

- runtime path helpers for local file-based artifacts;
- validated raw payload metadata, run manifests, and source health;
- source-config validation, examples, read-only source-config inventory, and
  read-only source-config inspection;
- contract-only source-set schema, example source-config refs, read-only
  source-set inventory, and read-only source-set inspection;
- profile config validation, examples, read-only profile inventory, and
  read-only profile inspection;
- read-only source-set/profile source-type compatibility preflight;
- clean-record emission from implemented source families;
- deterministic profile projection from the clean cache;
- explicit profile seen-state initialization without overwriting existing state;
- explicit profile seen-state filtering during multi-profile and one-source
  source-config projection;
- explicit profile seen-state updates;
- explicit source-config seen-state updates after one-source projection;
- read-only runtime inspection commands;
- governance decision evaluation and optional audit logging;
- approval, dry-run, mediation, and local tool-execution records;
- provider-neutral request and result records with preset-resolved provider
  command argv;
- read-only provider preset inspection;
- explicit local provider command invocation.

The runtime remains local-first and file-based. Runtime data belongs outside
the repository.

`inspect-source-config` validates one `source-config.v1` file and returns a
normalized summary. It does not fetch upstream sources, write runtime data,
read profile state, project profiles, or update seen state.
`list-source-configs` validates the tracked `sources/examples/*.json` catalog
rejects duplicate source ids across the catalog, and returns a deterministic
inventory under the same no-fetch/no-write boundary.
`list-source-sets` validates the tracked `sources/sets/*.json` catalog,
rejects duplicate source-set ids across the catalog, rejects duplicate source
ids and source config refs inside each source set, and validates each
referenced source-config file under the same no-fetch/no-write boundary.
`list-profiles` validates the tracked `profiles/examples/*.json` catalog and
returns a deterministic inventory under the same no-fetch/no-write boundary.
`inspect-profile` validates one profile config and returns its normalized
object without projecting, reading profile state, or writing runtime data.
`check-source-set-profiles` validates one source set, its referenced source
configs, and one or more profile configs, then reports matched and rejected
source types for each profile. It does not fetch sources, project profiles,
read profile state, schedule or batch source sets, or write runtime data.

The reusable source-config daily recipes in `docs/13-source-config-recipes.md`
are documentation-only. They describe explicit `run-source-config` and
`smoke-source-config` command shapes for consumers, but do not add a scheduler,
wrapper script, daemon, runtime command, publication workflow, or consumer
ranking policy.

The consumer onboarding handoff in `docs/08-consumer-onboarding.md` is also
documentation-only. It names the profile path, source-config path, runtime root,
profile-local `seen_records` ownership, and smoke preflight boundary that a
consumer should carry into its own repo or local runtime setup, but it does not
centralize consumer profiles, runtime state, scheduling, scoring, reporting, or
publication behavior in this shared core.

The `source-set.v1` contract and
`sources/sets/code-intel-source-set.json` example are contract-only grouping
surfaces. `list-source-sets` validates the tracked source-set catalog, and
`inspect-source-set` reads one source-set file and validates each referenced
source-config file. Both commands reject duplicate source ids and source config
refs inside one source set. `list-source-sets` also rejects duplicate
source-set ids across the tracked catalog. No current runtime command
dispatches, schedules, or batches source sets.

## Contract hardening already in place

Current validators and schemas reject several invalid states before downstream
runtime paths consume them:

- denied governance decisions remain blocked during mediation;
- raw metadata status must match body/error state;
- source health counts must match success/failure counts;
- terminal run manifests must carry matching source-health refs;
- projection counts must match emitted and excluded records;
- projection counts include explicit `excluded_seen` records when a profile
  seen-state filter is applied;
- profile `accepted_sources` must be non-empty and must contain only supported
  source types before a profile can be inspected, projected, or checked against
  a source set;
- profile seen-state record ids must be safe path segments, sorted, and unique;
- source-config catalog entries must use unique `source_id` values before the
  catalog can be listed;
- source-set catalog entries must use unique `source_set_id` values before the
  catalog can be listed;
- source-set refs must use unique `source_id` and `source_config_path` values
  before inspection, compatibility preflight, or any future execution surface
  consumes them;
- GitHub `source-config.v1` `owner` and `repo` values are rejected unless they
  are safe GitHub path segments before collectors derive request URLs;
- governance, tool-execution, and provider adapter artifacts reject unsafe
  `profile_id` values before those profile-scoped identities move across
  policy, mediation, execution, or provider boundaries;
- provider request and result artifacts preserve safe `mediation_id` values
  from execution mediation records;
- `intent_id` remains a logical correlation id for matching tool intent scope;
  it is not a runtime path segment in the current contracts;
- governed tool execution requires the supplied argv to exactly match
  `tool-intent.v1` `arguments.command` before invocation;
- provider requests resolve command argv from a repo-owned read-only preset
  allowlist;
- provider preset inspection resolves only repo-owned allowlist entries and does
  not invoke providers, discover commands, read credentials, or write runtime
  artifacts;
- provider invocation rejects invoke-time command overrides and blocks requests
  whose provider command fields no longer match the allowlist preset;
- provider request, provider result, and provider invocation boundaries are
  currently `read_only`-only and reject side-effect action classes;
- denied provider requests are rejected before provider-request records;
- embedded governance audit events reuse standalone audit id validation;
- `profile_id`, source ids, clean record ids, profile projection ids, raw
  metadata ids, run-manifest ids, source-health ids, governance audit ids,
  approval record ids, dry-run result ids, execution mediation ids, tool
  execution result ids, provider request ids, provider result ids, and
  profile-state ids use safe path segments at their relevant contract
  boundaries.

## Explicitly deferred scope

Do not treat these as missing bugs without a new behavior decision:

- source collector families beyond the implemented families listed above;
- sanitizer mappings beyond the implemented families listed above;
- consumer-specific ranking, editorial shaping, or dedupe policy;
- implicit profile-state reads or updates without an explicit gate;
- source-set runtime execution or batch runners;
- automatic command discovery;
- credential mapping or provider/tool presets beyond the repo-owned read-only
  provider allowlist;
- SQLite, daemon, web UI, cloud service, dashboard, or scheduler.

## Latest verification evidence

Local verification on 2026-06-08:

- `python3 scripts/check_repo.py` passed with 273 tests after rejecting
  duplicate `source_id` values across the tracked source-config catalog.
- `python3 scripts/check_repo.py` passed with 272 tests after rejecting
  duplicate `source_set_id` values across the tracked source-set catalog.
- `python3 scripts/check_repo.py` passed with 271 tests after rejecting
  duplicate `source_config_path` values inside one `source-set.v1`.
- `python3 scripts/check_repo.py` passed with 268 tests after rejecting
  duplicate `source_id` values inside one `source-set.v1`.
- `python3 scripts/check_repo.py` passed with 265 tests after requiring
  non-empty profile `accepted_sources` in schema and runtime validation.
- `python3 scripts/check_repo.py` passed with 261 tests after aligning runtime
  profile `accepted_sources` validation with the profile schema allowlist.
- `python3 scripts/check_repo.py` passed with 257 tests after adding read-only
  source-set/profile compatibility preflight.
- `PYTHONPATH=src python3 -m shared_intake_governance.cli check-source-set-profiles --source-set sources/sets/code-intel-source-set.json --profile profiles/examples/code-intel-kernel.json --profile profiles/examples/pulse.json`
  returned `compatible: true` with 5 matched and 5 rejected source/profile
  pairs.
- `python3 scripts/check_repo.py` passed with 254 tests after adding read-only
  profile catalog inspection.
- `python3 scripts/check_repo.py` passed after adding the explicit
  `init-profile-seen-state` boundary.
- `python3 scripts/check_repo.py` passed after adding the canonical local
  verification runner.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 245 tests
  after adding the contract anchor consistency guard.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 244 tests
  after adding the provider surface consistency guard.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 243 tests
  after adding the source-type consistency guard.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 242 tests
  after adding the CLI/docs surface consistency guard.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 241 tests
  after adding read-only `list-source-sets` inventory.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 239 tests
  after adding read-only `list-source-configs` inventory.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 237 tests
  after adding read-only `inspect-source-config` validation.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 235 tests
  after adding read-only `inspect-source-set` validation.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 233 tests
  after adding the contract-only `source-set.v1` schema and example.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 230 tests
  after linking consumer onboarding to the source-config recipe handoff.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 229 tests
  after adding the canonical source-config recipe doc and navigation guard.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 228 tests
  after adding explicit seen-state updates to `run-source-config` and
  `smoke-source-config`.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 226 tests
  after adding explicit seen-state filtering to `run-source-config` and
  `smoke-source-config`.

Local verification on 2026-06-05:

- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 224 tests
  after adding explicit seen-state filtering to `project-profiles`.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 222 tests
  after hardening GitHub `owner` and `repo` source-config validation.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 220 tests
  after adding the read-only `github_releases` source family.
- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 210 tests
  after adding read-only provider preset inspection commands and
  `agy_readonly_local`.
- `jq empty schemas/*.json profiles/examples/*.json sources/examples/*.json`
  passed.
- `git diff --check` passed.
- `PYTHONPATH=src python3 -m compileall -q src tests` passed.
- `PYTHONPATH=src python3 -m shared_intake_governance.cli --help` passed.

Local verification on 2026-05-30:

- `PYTHONPATH=src python3 -m unittest discover -s tests` passed with 206 tests
  after adding optional GitHub auth headers, empty-result sanitizer coverage,
  broader GitHub search query operators, and Claude preset prompt framing.
- `jq empty schemas/*.json profiles/examples/*.json sources/examples/*.json`
  passed.
- `git diff --check` passed.
- `PYTHONPATH=src python3 -m compileall -q src tests` passed.
- `PYTHONPATH=src python3 -m shared_intake_governance.cli --help` passed.

Live isolated source smoke on 2026-05-30:

- command: `smoke-source-config` with
  `sources/examples/arxiv-query-code-agents.json` and
  `profiles/examples/code-intel-kernel.json`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 5 clean records, 1
  projection report, 3 projected items, 1 run manifest, and 1 healthy source
  health artifact;
- read-only inspection commands validated the smoke run manifest, source
  health artifact, and profile report.

Live isolated source smoke on 2026-06-05:

- command: `smoke-source-config` with
  `sources/examples/github-releases-shared-intake.json` and
  `profiles/examples/code-intel-kernel.json`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 0 clean records, 1
  projection report, 0 projected items, 1 run manifest, and 1 healthy source
  health artifact;
- upstream payload was a valid JSON array with 0 release items at smoke time;
- read-only inspection commands validated the smoke run manifest, source
  health artifact, and profile report.

Live isolated source smoke on 2026-06-05:

- command: `smoke-source-config` with
  `sources/examples/github-releases-repo-governance.json` and
  `profiles/examples/code-intel-kernel.json`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 0 projected items, 1 run manifest, and 1 healthy source
  health artifact;
- upstream payload was a valid JSON array with 3 release items at smoke time;
- projected items were 0 because the example profile does not accept
  `github_releases`; this smoke proves the non-empty collection and
  clean-record emission path;
- read-only inspection commands validated the smoke run manifest, source
  health artifact, and profile report.

Live isolated source smoke on 2026-06-05:

- command: `smoke-source-config` with
  `sources/examples/github-releases-repo-governance.json` and a temporary
  profile outside the repository that accepts `github_releases`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 3 projected items, 1 run manifest, and 1 healthy source
  health artifact;
- projected release records were `v0.5.0`, `v0.4.0`, and `v0.1.0`, all from
  `https://github.com/heurema/repo-governance/releases`;
- read-only inspection commands validated the smoke run manifest, source
  health artifact, profile report, and clean record summaries.

Local profile-state filtering receipt on 2026-06-05:

- command: `project-profiles` with a temporary runtime root outside the
  repository, a temporary profile, and `--exclude-seen-state`;
- input: 2 validated clean records and one profile-local
  `seen-records.json` containing `github_repo-seen`;
- result: `clean_records_seen=2`, `excluded_seen=1`, `items_written=1`;
- output item: `github_repo-new`;
- read-only `inspect-profile-report` validated the generated
  `profile-projection.v1` report;
- the existing `seen-records.json` state artifact was not modified.

Live source-config seen-state filtering receipt on 2026-06-08:

- command: `run-source-config` with
  `sources/examples/github-releases-repo-governance.json`, a temporary profile
  outside the repository that accepts `github_releases`, and
  `--exclude-seen-state`;
- runtime policy: temporary runtime root outside the repository;
- input: profile-local `seen-records.json` containing
  `github_releases-3addbbf8811b5e55` for `v0.5.0`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 2 projected items, 1 excluded-seen item, 1 run manifest,
  and 1 healthy source health artifact;
- read-only `inspect-profile-report` validated the generated
  `profile-projection.v1` report;
- the existing `seen-records.json` state artifact was not modified.

Live smoke source-config seen-state filtering receipt on 2026-06-08:

- command: `smoke-source-config` with an explicit temporary runtime root,
  `sources/examples/github-releases-repo-governance.json`, a temporary profile
  outside the repository that accepts `github_releases`, and
  `--exclude-seen-state`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- input: profile-local `seen-records.json` containing
  `github_releases-3addbbf8811b5e55` for `v0.5.0`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 2 projected items, 1 excluded-seen item, 1 run manifest,
  and 1 healthy source health artifact;
- read-only `inspect-profile-report` validated the generated
  `profile-projection.v1` report;
- the existing `seen-records.json` state artifact was not modified.

Live source-config seen-state update receipt on 2026-06-08:

- command: `run-source-config` with
  `sources/examples/github-releases-repo-governance.json`, a temporary profile
  outside the repository that accepts `github_releases`,
  `--exclude-seen-state`, and `--update-seen-state`;
- runtime policy: temporary runtime root outside the repository;
- input: profile-local `seen-records.json` containing
  `github_releases-3addbbf8811b5e55` for `v0.5.0`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 2 projected items, 1 excluded-seen item, 1 run manifest,
  and 1 healthy source health artifact;
- projected items were `github_releases-747c0df7c429fcae` for `v0.1.0` and
  `github_releases-db0d35dc75c97eb3` for `v0.4.0`;
- `seen-records.json` was updated from 1 record id to 3 sorted record ids.

Live smoke source-config seen-state update receipt on 2026-06-08:

- command: `smoke-source-config` with an explicit temporary runtime root,
  `sources/examples/github-releases-repo-governance.json`, a temporary profile
  outside the repository that accepts `github_releases`,
  `--exclude-seen-state`, and `--update-seen-state`;
- runtime policy: temporary runtime root outside the repository with
  `SMOKE_RUNTIME_DO_NOT_COMMIT.txt`;
- input: profile-local `seen-records.json` containing
  `github_releases-3addbbf8811b5e55` for `v0.5.0`;
- result: `status=completed`, `fetch_status=success`, `http_status=200`;
- output: 1 raw payload, 1 raw metadata artifact, 3 clean records, 1
  projection report, 2 projected items, 1 excluded-seen item, 1 run manifest,
  and 1 healthy source health artifact;
- projected items were `github_releases-747c0df7c429fcae` for `v0.1.0` and
  `github_releases-db0d35dc75c97eb3` for `v0.4.0`;
- `seen-records.json` was updated from 1 record id to 3 sorted record ids.

## Verification commands

Use these checks after runtime or contract changes:

```sh
python3 scripts/check_repo.py
```

Equivalent expanded checklist:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/check_surface_consistency.py
python3 scripts/check_source_type_consistency.py
python3 scripts/check_provider_surface_consistency.py
python3 scripts/check_contract_anchor_consistency.py
jq empty schemas/*.json profiles/examples/*.json sources/examples/*.json sources/sets/*.json
git diff --check
PYTHONPATH=src python3 -m compileall -q src tests scripts
PYTHONPATH=src python3 -m shared_intake_governance.cli --help
```

Remove generated `__pycache__` directories after compile checks.

## Next safe expansion rule

Before the next runtime expansion, choose exactly one of:

- one explicit source family;
- one explicit profile-state boundary;
- one explicit command or provider boundary;
- one contract/runtime validation mismatch.

Do not add a new system layer to solve a local contract gap.
