# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or include secrets, private analytical data, tokens, pairing codes, or exploit details in ordinary project discussions.

Use GitHub's private **Report a vulnerability** flow under the repository's
Security tab. Include the affected component, reproduction conditions, impact,
and the smallest safe proof of concept. If private vulnerability reporting is
temporarily unavailable, contact the repository owner privately through GitHub;
do not disclose exploit details in an issue or discussion.

## Supported scope

The current supported profile is single-user and local-first:

- The companion binds to loopback.
- Local Private requires bearer authentication.
- Pairing codes are one-use and short-lived.
- Browser grants are short-lived and origin-bound.
- The hosted viewer contains no database, ingestion service, or user-project
  storage. It serves one allowlisted aggregate-only public showcase.
- Redaction occurs before persistence and export.
- Codex ship missions use local stdio, a fixed workspace-write sandbox, no
  approval escalation, command network access disabled, web search disabled,
  filtered environment variables, and protocol-level developer guardrails.

## Prompt-injection boundary

No LLM application can promise that prompt injection is impossible. Evolastra
reduces this risk by keeping public-demo mode read-only, requiring explicit local
pairing and an explicit launch for Codex missions, separating trusted developer
instructions from user and imported analysis text, labeling imported context as
untrusted data, disabling web search and command network access, filtering
ambient credentials, and limiting writes to the repository workspace.

Repository files and direct mission text can still be adversarial. Do not keep
secrets in the workspace, do not paste instructions you do not trust, inspect
the generated Codex task and diff, and run the verification gate before accepting
changes. See [Responsible use](docs/security/responsible-use.md).

Production multi-user identity, tenant isolation, and remote API hosting are outside the verified scope. See the [threat model](docs/security/threat-model.md), [privacy model](docs/security/privacy-model.md), and [security controls report](docs/security/security_best_practices_report.md).

## Disclosure expectations

Please allow reasonable time to reproduce and fix a report before public
disclosure. Never include real credentials, patient-level data, private datasets,
or another person's project content in a report.
