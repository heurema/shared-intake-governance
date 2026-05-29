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

- GitHub repositories and searches;
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
- source config contract for one-source local runs;
- minimal runtime path helpers and raw payload/metadata/run manifest writers;
- minimal read-only `github_repo` collector that writes raw evidence only;
- minimal read-only `arxiv_rss_keywords` collector that writes raw evidence only;
- minimal clean-record emitter for `github_repo` and `arxiv_rss_keywords` raw evidence;
- minimal one-profile projector that writes deterministic JSON reports;
- narrow local CLI commands for `github_repo` and `arxiv_rss_keywords` collect,
  sanitize, and project paths;
- config-driven one-source CLI command for source definitions stored in JSON;
- run manifest and source health artifacts from the CLI pipeline.

What does not exist yet:

- source collector families beyond `github_repo` and `arxiv_rss_keywords`;
- sanitizer source mappings beyond `github_repo` and `arxiv_rss_keywords`;
- multi-profile projection/report shaping;
- governance broker runtime;
- provider adapter runtime;
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
6. if you need to continue implementation, read [docs/10-implementation-guide.md](docs/10-implementation-guide.md).

## Repository layout

```text
AGENTS.md            repo-specific operating rules for agents
README.md            quick orientation and entrypoint
docs/                canonical design, onboarding, threat model, roadmap
schemas/             JSON schemas for contracts
profiles/examples/   example consumer profiles
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

The next useful runtime slice is Phase 1:

- support `github_repo` and `arxiv_rss_keywords`;
- write immutable raw payloads;
- emit clean records with risk flags;
- project one profile from shared clean cache;
- do all of that without LLM dependence.

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
