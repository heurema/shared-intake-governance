# Shared Intake Governance

Local-first shared intake and agent-governance core for multiple AI research, benchmark, news, and coding-agent workflows.

This is an early docs/contracts-first repository. It is useful as a reusable
architecture and contract baseline, but it is not a finished runtime package.

## What this repository is

This repository is the shared core below multiple project-specific R&D loops.

Its job is to make these things happen once instead of repeatedly in every consumer repo:

- fetch external signals;
- store immutable raw evidence;
- sanitize and risk-classify external text;
- project clean records into multiple consumer profiles;
- enforce provider-neutral guardrails before any side effects.

## What this repository is not

This repository is not:

- a replacement for project-level radars or briefs;
- a web app;
- a hosted control plane;
- a cloud sync service;
- a project-specific scoring engine;
- a place to store runtime cache or secrets in git.

## Why it exists

Several local projects already consume overlapping upstream signals such as:

- GitHub repositories, releases, and searches;
- arXiv feeds and queries;
- RSS and news sources;
- official project sites.

Running separate loops for each consumer causes the same problems repeatedly:

- duplicate fetch cost;
- repeated rate limits and anti-bot failures;
- repeated summarization cost;
- inconsistent prompt-injection handling;
- different safety rules for the same external text;
- duplicated maintenance across projects.

This repository exists to centralize the shared part without centralizing project-specific outputs.

## Current state

This repository is still docs/contracts-first, with a minimal file-based
runtime foundation now started.

What exists now:

- product brief;
- architecture;
- data contracts;
- provider adapter boundaries;
- threat model;
- onboarding guides for sources and consumers;
- operating model;
- implementation staging guide;
- example consumer profiles;
- example source configs;
- source config contract and validator for one-source local runs;
- minimal runtime path helpers and raw payload, validated and raw-root bounded
  raw metadata, and validated run manifest writers;
- minimal read-only `github_repo` collector that writes raw evidence only;
- minimal read-only `github_releases` collector that writes raw evidence only;
- minimal read-only `github_search` collector that writes raw evidence only;
- minimal read-only `arxiv_query` collector that writes raw evidence only;
- minimal read-only `rss` collector that writes raw evidence only;
- minimal read-only `news` collector that writes raw evidence only;
- minimal clean-record emitter with validated raw metadata input and raw-root
  bounded body reads for `github_repo`, `github_releases`, `github_search`,
  `arxiv_query`, `rss`, and `news` raw evidence;
- profile-projection contract for deterministic per-profile report artifacts;
- minimal explicit-profile projector that writes deterministic JSON reports;
- runtime validation for profile projection reports before write and seen-state
  consumption;
- profile-state contract and validator for profile-local runtime state artifacts;
- explicit `update-profile-seen-state` CLI that merges one profile report into
  a profile-local `seen_records` state artifact;
- narrow local CLI commands for `github_repo`, `github_releases`,
  `github_search`, `arxiv_query`, `rss`, and `news` collect, sanitize, and
  project paths;
- multi-profile CLI command that projects existing clean cache into multiple
  explicit profile reports;
- explicit `project-profiles --exclude-seen-state`, `run-source-config
  --exclude-seen-state`, and `smoke-source-config --exclude-seen-state` flags
  that read each profile's `seen_records` state artifact and omit already-seen
  record ids from projection reports without updating state;
- explicit `project-profiles --update-seen-state`, `run-source-config
  --update-seen-state`, and `smoke-source-config --update-seen-state` flags
  that merge generated report items into that profile's `seen_records` state
  artifact;
- source-set contract and example for grouping tracked `source-config.v1`
  refs without executing them;
- read-only `list-source-configs` CLI command for validating and listing the
  tracked source-config catalog without running sources;
- read-only `inspect-source-config` CLI command for validating one
  `source-config.v1` file without running it;
- read-only `inspect-source-set` CLI command for validating one source-set file
  and its referenced source-config files without running sources;
- config-driven one-source CLI command for source definitions stored in JSON;
- isolated smoke CLI command for live one-source checks with runtime data
  outside git;
- read-only CLI commands for validated listing and inspection of run manifests,
  clean records, profile state, profile reports, mediation records, and source
  health;
- reusable source-config recipes for explicit "new only, then mark seen"
  consumer loops;
- validated run manifest and source health artifacts from the CLI pipeline.
- validated tool-intent and governance-decision contracts with a read-only
  default governance evaluator CLI.
- governance audit event contract and optional validated append-only audit
  logging for evaluated tool intents.
- approval-record contract and local `record-approval` CLI for validated
  explicit approval or rejection records without tool execution.
- dry-run-result contract and local `record-dry-run` CLI for validated recorded
  dry-run evidence without tool execution.
- execution-mediation contract and local `mediate-tool-intent` CLI for
  validated pre-execution readiness checks over validated evidence without tool
  execution.
- tool-execution-result contract and local `execute-tool-intent` CLI for
  explicit governed local command execution with validated result records after
  validated ready mediation and exact argv binding from the tool intent.
- provider-request contract and local `prepare-provider-request` CLI for
  validated `read_only` provider-neutral adapter request records that resolve
  exact provider command argv from a repo-owned preset allowlist without
  provider invocation.
- local `list-provider-presets` and `inspect-provider-preset` CLI commands for
  read-only inspection of the repo-owned provider preset allowlist.
- provider-result contract and local `record-provider-result` CLI for validated
  provider response refs and usage metadata without provider invocation.
- local `invoke-provider-request` CLI for running only the request-bound
  provider command resolved from the preset allowlist, passing provider-request
  JSON on stdin, storing stdout/stderr as runtime artifacts, and recording
  `provider-result.v1`. Current provider invocation is `read_only`-only.

What does not exist yet:

- source collector families beyond `github_repo`, `github_releases`,
  `github_search`, `arxiv_query`, `rss`, and `news`;
- sanitizer source mappings beyond `github_repo`, `github_releases`,
  `github_search`, `arxiv_query`, `rss`, and `news`;
- the retired `arxiv_rss_keywords` family; use `arxiv_query` for arXiv query
  transport or `rss` for explicit feed transport;
- multi-profile report shaping beyond deterministic per-profile JSON;
- consumer-specific dedupe behavior beyond explicit seen-record filtering;
  implicit profile-state updates remain out of current scope unless a new
  behavior decision replaces the explicit `--update-seen-state` gate;
- source-set runtime execution or batch runner;
- automatic command discovery, credential mapping, or provider/tool presets
  beyond the repo-owned read-only provider allowlist;
- SQLite;
- daemon;
- web UI.

## If you are an agent entering this repo

Start here:

1. read [docs/INDEX.md](docs/INDEX.md);
2. read [AGENTS.md](AGENTS.md);
3. if you need execution context, read [docs/06-agent-session-guide.md](docs/06-agent-session-guide.md);
4. if you need to add or change a source, read [docs/07-source-onboarding.md](docs/07-source-onboarding.md);
5. if you need to onboard a new consumer project, read [docs/08-consumer-onboarding.md](docs/08-consumer-onboarding.md);
6. if you need a reusable local source-config recipe, read [docs/13-source-config-recipes.md](docs/13-source-config-recipes.md);
7. if you need to continue implementation, read [docs/10-implementation-guide.md](docs/10-implementation-guide.md).

## Repository layout

```text
AGENTS.md            repo-specific operating rules for agents
README.md            quick orientation and entrypoint
docs/                canonical design, onboarding, threat model, roadmap
schemas/             JSON schemas for contracts
profiles/examples/   example consumer profiles
sources/examples/    example one-source run configs
src/                 minimal Python runtime helpers, collectors, sanitizer, projector, CLI
tests/               focused runtime, collector, sanitizer, projector, and CLI tests
```

## Runtime boundary

Runtime data belongs outside the repository. The expected local root is:

```text
~/.local/share/shared-intake-governance/
```

That runtime root should eventually hold:

- raw payload cache;
- clean normalized cache;
- run manifests;
- audit logs;
- per-profile local state;
- per-profile generated outputs.

## Core architectural decisions

These decisions are already made and should not be reopened casually:

1. `collect once, project many`
2. external text is data, never instructions
3. policy is provider-neutral
4. profiles stay separate even if cache is shared
5. file-based first, database later only if pressure proves it
6. destructive actions are denied by default
7. the core is a local repository, not a service

## Relationship to consumer projects

Consumer repos should own:

- their product-specific profile definitions;
- their scoring and filtering decisions;
- their seen state and report outputs;
- any final publication or action semantics.

This repository should own only the shared substrate:

- collection;
- normalization;
- sanitization;
- provenance;
- risk flags;
- governance contracts;
- adapter contracts.

## Next implementation step

The latest source-of-truth audit is
[docs/12-current-surface-audit.md](docs/12-current-surface-audit.md).

Before widening runtime scope again:

- verify docs, schemas, `AGENTS.md`, and CLI help describe the same current
  surface;
- keep any next runtime expansion to one explicit source, profile-state, or
  command boundary;
- do not add automatic command discovery, credentials, daemon, SQLite, UI, or
  provider/tool presets beyond the repo-owned read-only provider allowlist
  without a new explicit scope decision.

See [docs/10-implementation-guide.md](docs/10-implementation-guide.md) for the exact order.

## Open source and reuse

- [LICENSE](LICENSE)
- [NOTICE](NOTICE)
- [CONTRIBUTING](CONTRIBUTING.md)
- [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md)
- [SECURITY](SECURITY.md)
- [SUPPORT](SUPPORT.md)
- [TRADEMARKS](TRADEMARKS.md)

The repository is intended to be reusable as a local-first shared intake
governance reference. Consumer-specific profiles, scoring, reports, runtime
state, credentials, and publication flows should stay outside this core.

## License

[Apache License 2.0](LICENSE)
