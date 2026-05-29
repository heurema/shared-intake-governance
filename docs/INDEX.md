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
- [04-mvp-roadmap.md](04-mvp-roadmap.md)
- [03-provider-adapters.md](03-provider-adapters.md)

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

## Schemas and examples

- [../schemas/raw-metadata.schema.json](../schemas/raw-metadata.schema.json)
- [../schemas/clean-record.schema.json](../schemas/clean-record.schema.json)
- [../schemas/run-manifest.schema.json](../schemas/run-manifest.schema.json)
- [../schemas/source-health.schema.json](../schemas/source-health.schema.json)
- [../schemas/source-config.schema.json](../schemas/source-config.schema.json)
- [../schemas/profile.schema.json](../schemas/profile.schema.json)
- [../schemas/profile-state.schema.json](../schemas/profile-state.schema.json)
- [../schemas/tool-intent.schema.json](../schemas/tool-intent.schema.json)
- [../schemas/governance-decision.schema.json](../schemas/governance-decision.schema.json)
- [../schemas/governance-audit-event.schema.json](../schemas/governance-audit-event.schema.json)
- [../schemas/approval-record.schema.json](../schemas/approval-record.schema.json)
- [../schemas/dry-run-result.schema.json](../schemas/dry-run-result.schema.json)
- [../schemas/execution-mediation.schema.json](../schemas/execution-mediation.schema.json)
- [../schemas/provider-request.schema.json](../schemas/provider-request.schema.json)
- [../schemas/provider-result.schema.json](../schemas/provider-result.schema.json)
- [../profiles/examples/code-intel-kernel.json](../profiles/examples/code-intel-kernel.json)
- [../profiles/examples/agent-bench-lab.json](../profiles/examples/agent-bench-lab.json)
- [../profiles/examples/pulse.json](../profiles/examples/pulse.json)
- [../sources/examples/github-signum.json](../sources/examples/github-signum.json)
- [../sources/examples/arxiv-code-agents.json](../sources/examples/arxiv-code-agents.json)

## Runtime code

- [../src/shared_intake_governance/runtime/paths.py](../src/shared_intake_governance/runtime/paths.py)
- [../src/shared_intake_governance/runtime/writers.py](../src/shared_intake_governance/runtime/writers.py)
- [../src/shared_intake_governance/collector/github_repo.py](../src/shared_intake_governance/collector/github_repo.py)
- [../src/shared_intake_governance/collector/arxiv_rss_keywords.py](../src/shared_intake_governance/collector/arxiv_rss_keywords.py)
- [../src/shared_intake_governance/sanitizer/clean_records.py](../src/shared_intake_governance/sanitizer/clean_records.py)
- [../src/shared_intake_governance/projector/profile.py](../src/shared_intake_governance/projector/profile.py)
- [../src/shared_intake_governance/adapters/provider_request.py](../src/shared_intake_governance/adapters/provider_request.py)
- [../src/shared_intake_governance/adapters/provider_result.py](../src/shared_intake_governance/adapters/provider_result.py)
- [../src/shared_intake_governance/cli/pipeline.py](../src/shared_intake_governance/cli/pipeline.py)
- [../tests/test_runtime_paths_and_writers.py](../tests/test_runtime_paths_and_writers.py)
- [../tests/test_governance_mediation.py](../tests/test_governance_mediation.py)
- [../tests/test_provider_request.py](../tests/test_provider_request.py)
- [../tests/test_provider_result.py](../tests/test_provider_result.py)
- [../tests/test_github_repo_collector.py](../tests/test_github_repo_collector.py)
- [../tests/test_arxiv_rss_keywords_collector.py](../tests/test_arxiv_rss_keywords_collector.py)
- [../tests/test_clean_records_and_projection.py](../tests/test_clean_records_and_projection.py)
- [../tests/test_cli_pipeline.py](../tests/test_cli_pipeline.py)
