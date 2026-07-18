# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or include secrets, private analytical data, tokens, pairing codes, or exploit details in ordinary project discussions.

For this private repository, contact the repository owner directly through GitHub. Include the affected component, reproduction conditions, impact, and the smallest safe proof of concept. The owner will acknowledge the report, assess severity, and coordinate remediation before wider disclosure.

## Supported scope

The current supported profile is single-user and local-first:

- The companion binds to loopback.
- Local Private requires bearer authentication.
- Pairing codes are one-use and short-lived.
- Browser grants are short-lived and origin-bound.
- The hosted viewer contains no database, ingestion service, or analysis storage.
- Redaction occurs before persistence and export.

Production multi-user identity, tenant isolation, and remote API hosting are outside the verified scope. See the [threat model](docs/security/threat-model.md), [privacy model](docs/security/privacy-model.md), and [security controls report](docs/security/security_best_practices_report.md).
