# Docs Index

This repository is meant to be understandable by a new agent without oral context.
Use this file as the main navigation layer.

## Read this first

1. [00-product-brief.md](00-product-brief.md)
2. [01-architecture.md](01-architecture.md)
3. [06-agent-session-guide.md](06-agent-session-guide.md)
4. [02-data-contracts.md](02-data-contracts.md)
5. [05-threat-model.md](05-threat-model.md)

## If you need to do something specific

### Understand what this project is for

- [00-product-brief.md](00-product-brief.md)
- [01-architecture.md](01-architecture.md)
- [09-operating-model.md](09-operating-model.md)

### Enter this repo from another project and continue correctly

- [06-agent-session-guide.md](06-agent-session-guide.md)
- [10-implementation-guide.md](10-implementation-guide.md)

### Add or change a shared source

- [07-source-onboarding.md](07-source-onboarding.md)
- [02-data-contracts.md](02-data-contracts.md)
- [05-threat-model.md](05-threat-model.md)

### Add a new consumer project or recipient

- [08-consumer-onboarding.md](08-consumer-onboarding.md)
- [09-operating-model.md](09-operating-model.md)
- [../schemas/profile.schema.json](../schemas/profile.schema.json)

### Continue runtime implementation

- [10-implementation-guide.md](10-implementation-guide.md)
- [11-local-runbook.md](11-local-runbook.md)
- [13-source-config-recipes.md](13-source-config-recipes.md)
- [12-current-surface-audit.md](12-current-surface-audit.md)
- [04-mvp-roadmap.md](04-mvp-roadmap.md)
- [03-provider-adapters.md](03-provider-adapters.md)

### Run reusable source-config recipes

- [13-source-config-recipes.md](13-source-config-recipes.md)
- [../schemas/source-set.schema.json](../schemas/source-set.schema.json)
- [../sources/sets/code-intel-source-set.json](../sources/sets/code-intel-source-set.json)
- [11-local-runbook.md](11-local-runbook.md)
- [09-operating-model.md](09-operating-model.md)

### Review provider boundaries

- [03-provider-adapters.md](03-provider-adapters.md)
- [05-threat-model.md](05-threat-model.md)

## Canonical documents

1. [00-product-brief.md](00-product-brief.md)
2. [01-architecture.md](01-architecture.md)
3. [02-data-contracts.md](02-data-contracts.md)
4. [03-provider-adapters.md](03-provider-adapters.md)
5. [04-mvp-roadmap.md](04-mvp-roadmap.md)
6. [05-threat-model.md](05-threat-model.md)
7. [06-agent-session-guide.md](06-agent-session-guide.md)
8. [07-source-onboarding.md](07-source-onboarding.md)
9. [08-consumer-onboarding.md](08-consumer-onboarding.md)
10. [09-operating-model.md](09-operating-model.md)
11. [10-implementation-guide.md](10-implementation-guide.md)
12. [11-local-runbook.md](11-local-runbook.md)
13. [12-current-surface-audit.md](12-current-surface-audit.md)
14. [13-source-config-recipes.md](13-source-config-recipes.md)

## Schemas and examples

- [../schemas/raw-metadata.schema.json](../schemas/raw-metadata.schema.json)
- [../schemas/clean-record.schema.json](../schemas/clean-record.schema.json)
- [../schemas/run-manifest.schema.json](../schemas/run-manifest.schema.json)
- [../schemas/source-health.schema.json](../schemas/source-health.schema.json)
- [../schemas/source-config.schema.json](../schemas/source-config.schema.json)
- [../schemas/source-set.schema.json](../schemas/source-set.schema.json)
- [../schemas/profile.schema.json](../schemas/profile.schema.json)
- [../schemas/profile-projection.schema.json](../schemas/profile-projection.schema.json)
- [../schemas/profile-state.schema.json](../schemas/profile-state.schema.json)
- [../schemas/tool-intent.schema.json](../schemas/tool-intent.schema.json)
- [../schemas/governance-decision.schema.json](../schemas/governance-decision.schema.json)
- [../schemas/governance-audit-event.schema.json](../schemas/governance-audit-event.schema.json)
- [../schemas/approval-record.schema.json](../schemas/approval-record.schema.json)
- [../schemas/dry-run-result.schema.json](../schemas/dry-run-result.schema.json)
- [../schemas/execution-mediation.schema.json](../schemas/execution-mediation.schema.json)
- [../schemas/tool-execution-result.schema.json](../schemas/tool-execution-result.schema.json)
- [../schemas/provider-request.schema.json](../schemas/provider-request.schema.json)
- [../schemas/provider-result.schema.json](../schemas/provider-result.schema.json)
- [../profiles/examples/code-intel-kernel.json](../profiles/examples/code-intel-kernel.json)
- [../profiles/examples/agent-bench-lab.json](../profiles/examples/agent-bench-lab.json)
- [../profiles/examples/pulse.json](../profiles/examples/pulse.json)
- [../sources/examples/github-signum.json](../sources/examples/github-signum.json)
- [../sources/examples/github-releases-repo-governance.json](../sources/examples/github-releases-repo-governance.json)
- [../sources/examples/github-releases-shared-intake.json](../sources/examples/github-releases-shared-intake.json)
- [../sources/examples/github-search-code-agents.json](../sources/examples/github-search-code-agents.json)
- [../sources/examples/arxiv-query-code-agents.json](../sources/examples/arxiv-query-code-agents.json)
- [../sources/examples/news-openai-blog.json](../sources/examples/news-openai-blog.json)
- [../sources/examples/rss-github-blog.json](../sources/examples/rss-github-blog.json)
- [../sources/sets/code-intel-source-set.json](../sources/sets/code-intel-source-set.json)

## Runtime code

- [../src/shared_intake_governance/runtime/paths.py](../src/shared_intake_governance/runtime/paths.py)
- [../src/shared_intake_governance/runtime/writers.py](../src/shared_intake_governance/runtime/writers.py)
- [../src/shared_intake_governance/validation.py](../src/shared_intake_governance/validation.py)
- [../src/shared_intake_governance/source_config.py](../src/shared_intake_governance/source_config.py)
- [../src/shared_intake_governance/collector/github_auth.py](../src/shared_intake_governance/collector/github_auth.py)
- [../src/shared_intake_governance/collector/github_repo.py](../src/shared_intake_governance/collector/github_repo.py)
- [../src/shared_intake_governance/collector/github_releases.py](../src/shared_intake_governance/collector/github_releases.py)
- [../src/shared_intake_governance/collector/github_search.py](../src/shared_intake_governance/collector/github_search.py)
- [../src/shared_intake_governance/collector/arxiv_query.py](../src/shared_intake_governance/collector/arxiv_query.py)
- [../src/shared_intake_governance/collector/news_feed.py](../src/shared_intake_governance/collector/news_feed.py)
- [../src/shared_intake_governance/collector/rss_feed.py](../src/shared_intake_governance/collector/rss_feed.py)
- [../src/shared_intake_governance/sanitizer/clean_records.py](../src/shared_intake_governance/sanitizer/clean_records.py)
- [../src/shared_intake_governance/projector/profile.py](../src/shared_intake_governance/projector/profile.py)
- [../src/shared_intake_governance/projector/profile_state.py](../src/shared_intake_governance/projector/profile_state.py)
- [../src/shared_intake_governance/governance/policy.py](../src/shared_intake_governance/governance/policy.py)
- [../src/shared_intake_governance/governance/mediation.py](../src/shared_intake_governance/governance/mediation.py)
- [../src/shared_intake_governance/executor/tool_execution.py](../src/shared_intake_governance/executor/tool_execution.py)
- [../src/shared_intake_governance/provider_presets.py](../src/shared_intake_governance/provider_presets.py)
- [../src/shared_intake_governance/source_set.py](../src/shared_intake_governance/source_set.py)
- [../src/shared_intake_governance/adapters/provider_invocation.py](../src/shared_intake_governance/adapters/provider_invocation.py)
- [../src/shared_intake_governance/adapters/provider_request.py](../src/shared_intake_governance/adapters/provider_request.py)
- [../src/shared_intake_governance/adapters/provider_result.py](../src/shared_intake_governance/adapters/provider_result.py)
- [../src/shared_intake_governance/cli/pipeline.py](../src/shared_intake_governance/cli/pipeline.py)
- [../tests/test_docs_index.py](../tests/test_docs_index.py)
- [../tests/test_runtime_paths_and_writers.py](../tests/test_runtime_paths_and_writers.py)
- [../tests/test_source_config_examples.py](../tests/test_source_config_examples.py)
- [../tests/test_source_set_contract.py](../tests/test_source_set_contract.py)
- [../tests/test_profile_config_schema.py](../tests/test_profile_config_schema.py)
- [../tests/test_profile_projection_schema.py](../tests/test_profile_projection_schema.py)
- [../tests/test_profile_state.py](../tests/test_profile_state.py)
- [../tests/test_governance_policy.py](../tests/test_governance_policy.py)
- [../tests/test_governance_mediation.py](../tests/test_governance_mediation.py)
- [../tests/test_tool_execution.py](../tests/test_tool_execution.py)
- [../tests/test_provider_presets.py](../tests/test_provider_presets.py)
- [../tests/test_provider_invocation.py](../tests/test_provider_invocation.py)
- [../tests/test_provider_request.py](../tests/test_provider_request.py)
- [../tests/test_provider_result.py](../tests/test_provider_result.py)
- [../tests/test_github_repo_collector.py](../tests/test_github_repo_collector.py)
- [../tests/test_github_releases_collector.py](../tests/test_github_releases_collector.py)
- [../tests/test_github_search_collector.py](../tests/test_github_search_collector.py)
- [../tests/test_arxiv_query_collector.py](../tests/test_arxiv_query_collector.py)
- [../tests/test_news_feed_collector.py](../tests/test_news_feed_collector.py)
- [../tests/test_rss_feed_collector.py](../tests/test_rss_feed_collector.py)
- [../tests/test_clean_records_and_projection.py](../tests/test_clean_records_and_projection.py)
- [../tests/test_cli_pipeline.py](../tests/test_cli_pipeline.py)
