# 07 — Source Onboarding

## Purpose

This document defines how to add a new shared source path to the intake core.

The goal is not just "fetch more things".
The goal is to add reusable, safe, inspectable intake paths that multiple consumers can rely on.

## When a source belongs in the shared core

A source belongs here if most of these are true:

- more than one consumer can use it;
- it provides external evidence, not project-local product state;
- it can be fetched read-only;
- it has a stable canonical URL or equivalent identity;
- it fits the trust and safety model of shared intake;
- maintaining the adapter once here is cheaper than duplicating it elsewhere.

If the source is specific to one project's private business logic, keep it in that consumer repo.

## Current source families

The current contract surface already anticipates these `source_type` values:

- `github_repo`
- `github_search`
- `arxiv_query`
- `arxiv_rss_keywords`
- `rss`
- `news`
- `custom`

Prefer reusing one of these families before introducing a new one.

Current runtime implementation:

- `github_repo` has a minimal read-only collector that calls the GitHub REST
  repository endpoint and writes raw evidence only.
- `arxiv_rss_keywords` has a minimal read-only collector that calls the
  official arXiv API query endpoint and writes raw Atom evidence only.
- `rss` has a minimal read-only collector that fetches one explicit HTTPS feed
  URL and writes raw XML evidence only.
- clean-record emission exists for `github_repo` raw JSON,
  `arxiv_rss_keywords` raw Atom entries, and `rss` XML items.

## Source selection rules

Prefer sources in this order when possible:

1. official project site or official feed
2. official API
3. official platform metadata
4. maintainer-owned secondary source
5. general secondary source
6. social-only source

Higher-trust sources make the whole downstream stack safer and cheaper.

## Hard boundaries

Collectors must not:

- execute side effects;
- evaluate project-specific scoring;
- call mutation-capable tools;
- treat source text as instructions;
- bypass anti-bot or rate-limit protections with gray-hat tricks;
- store secrets in repo files.

## Before adding a source

Answer these questions first:

1. What real consumers need this source?
2. Can an existing source family already cover it?
3. What is the canonical identity for one item from this source?
4. What fields are worth preserving in raw form?
5. What fields are safe to surface in clean form?
6. What are the rate limit, anti-bot, auth, and terms constraints?
7. What source trust class should items from this source default to?
8. What prompt-injection or instruction-like content can appear here?

If you cannot answer these, do not start runtime code yet.

## Recommended onboarding flow

### Step 1: choose the adapter family

Decide whether the source can reuse an existing family:

- GitHub repo metadata
- GitHub search or activity
- arXiv query
- arXiv RSS keywords
- generic RSS
- generic news
- custom

Only introduce a new family when the transport, identity model, or extraction pattern is materially different.

### Step 2: define raw evidence shape

At minimum, the raw layer must preserve:

- `schema_version`
- `run_id`
- `source_id`
- `source_type`
- `fetch_status`
- `request_url`
- `canonical_url`
- `http_status`
- `fetched_at`
- `content_type`
- `body_hash`
- `storage_path`
- `collector_version`
- `error`
- `etag` when available
- `last_modified` when available

The point of the raw layer is evidence, not convenience.
See [../schemas/raw-metadata.schema.json](../schemas/raw-metadata.schema.json).

### Step 3: define clean record mapping

Map one source item into one clean record.

At minimum, define:

- how `record_id` is derived;
- how `canonical_url` is chosen;
- which text becomes `title`;
- which text becomes `sanitized_summary`;
- how `published_at` is set;
- what `source_trust` defaults to;
- which `risk_flags` may be emitted;
- when `quarantined` becomes `true`.

If one upstream page contains many logical items, split them before projection.

### Step 4: define sanitization and risk handling

Treat all external text as untrusted.

At minimum, sanitizer behavior should cover:

- HTML or markup stripping;
- Unicode and whitespace normalization;
- control character removal;
- maximum field lengths;
- imperative or instruction-like language detection;
- tool-escalation phrase detection;
- direct credential or secret bait detection when possible.

### Step 5: define health and failure behavior

Every source path should have an explicit failure policy.

Document:

- timeout behavior;
- retry policy;
- backoff policy;
- what counts as degraded versus failed;
- whether there is an official fallback path;
- what should be recorded in source health output.

Source health output should validate against
[../schemas/source-health.schema.json](../schemas/source-health.schema.json).

Do not silently widen the source path during failure.

### Step 6: define acceptance tests

The first implementation for a source should come with tests for:

- stable identity derivation;
- raw metadata capture;
- sanitization of representative text;
- risk flagging of malicious or instruction-like content;
- dedupe behavior if the source can emit near-duplicates.

## Rate limit and anti-bot rules

This matters because shared intake can easily hit the same upstreams for multiple consumers.

Required discipline:

- prefer official feeds and APIs;
- honor documented pacing requirements;
- use `ETag` and `Last-Modified` when available;
- retry only within bounded rules;
- record source health instead of hiding failures;
- do not use browser automation or challenge bypass for core intake unless the architecture is explicitly extended for it.

If a source is routinely blocked by anti-bot, do not normalize that as a core dependency.
Look for a more official transport path.

## When to add a new `source_type`

Add a new `source_type` only if all are true:

- the transport or data model is materially different from current families;
- multiple consumers can benefit from the new family;
- reuse through `custom` would make contracts vague or misleading;
- the new type improves safety or clarity rather than just naming preference.

If the difference is only query parameters or keywords, do not add a new `source_type`.

## Done criteria

A source onboarding is complete when:

1. the source belongs in the shared core;
2. the identity model is explicit;
3. the raw evidence contract is explicit;
4. the clean record mapping is explicit;
5. risk handling is explicit;
6. failure behavior is explicit;
7. tests or test plan exist;
8. at least one consumer use case is clear.

## Bad source additions

These are anti-patterns:

- adding a source because one prompt mentioned it once;
- adding a new family when keywords on an existing family would do;
- adding scraping that depends on brittle UI parsing without strong need;
- storing pre-summarized opinion instead of raw evidence;
- hiding rate-limit failures behind silent fallback to weak sources;
- letting one consumer's local convenience distort the shared model.
