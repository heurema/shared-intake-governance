# Security policy

Thanks for helping keep Shared Intake Governance and its users safe.

## Supported versions

Until the project publishes stable releases, the `main` branch is the only
supported line for security fixes.

Older commits, forks, and experimental branches may not receive patches.

## Reporting a vulnerability

Please do not open a public GitHub issue with full vulnerability details.

Preferred path:

1. Use GitHub private vulnerability reporting if it is available for this
   repository.
2. If private reporting is unavailable, open a minimal public issue requesting
   a private handoff, but do not include exploit details, secrets, tokens, or
   proof-of-concept material there.

Please include, when possible:

- affected paths, contracts, schemas, or assumptions;
- reproduction steps;
- impact assessment;
- any proposed remediation.

## What to expect

Maintainers will make a good-faith effort to:

- acknowledge the report in a reasonable time;
- assess the affected surface and severity;
- coordinate remediation and disclosure timing where appropriate.

## Security-sensitive surfaces

Security-sensitive surfaces include:

- external source intake and raw evidence handling;
- sanitization and risk-flag contracts;
- profile projection boundaries;
- provider-neutral tool intent and governance contracts;
- any future credentialed source, provider adapter, or side-effect broker;
- any future runtime path that writes reports, audit logs, or approval records.

## Disclosure guidance

Please avoid public disclosure until maintainers have had a reasonable chance
to investigate and prepare a fix or mitigation.

## Out of scope

This file is not a bug bounty program and does not create any right to
compensation.
