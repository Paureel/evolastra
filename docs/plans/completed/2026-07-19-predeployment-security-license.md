# Plan: predeployment security and open-source license

_Harden the public release without overstating what software can guarantee_

---

Status: completed
Owner: Codex
Last updated: 2026-07-19

## Outcome

The public deployment and local Codex bridge have evidence-backed safeguards
against injection, unauthorized dispatch, active-content rendering, and common
web/API attacks. The repository ships under the OSI-approved MIT License with
its standard warranty and liability disclaimer, plus clear responsible-use and
security-reporting guidance.

## Context

The application is a static Netlify viewer paired to a loopback-only companion.
Natural-language Codex missions are inherently an untrusted-input boundary;
prompt injection cannot be mathematically eliminated, so release claims must
describe isolation, authorization, and blast-radius controls instead of claiming
absolute immunity.

Relevant contracts: [architecture invariants](../../architecture/invariants.md),
[threat model](../../security/threat-model.md), and
[privacy model](../../security/privacy-model.md).

## Scope

- Included: source/config security audit, prompt-boundary hardening, regression
  tests, deployment headers, security policy, license, and honest safety docs.
- Excluded: cloud multi-tenancy, public companion exposure, legal advice, and a
  guarantee that an LLM will never follow adversarial instructions.

## Steps

- [x] Audit frontend, FastAPI, Codex dispatch, dependencies, and deployment config.
- [x] Fix confirmed material weaknesses and add adversarial regressions.
- [x] Add MIT license, security policy, responsible-use notice, and release claims.
- [x] Run the complete release gate and record residual risk.

## Decisions and surprises

- MIT is used verbatim: modifying it with a use restriction would make the
  license non-standard and potentially no longer open source. Its existing
  warranty/liability disclaimer covers use and misuse broadly.
- Enforcing Trusted Types initially blocked the semantic-layout Web Worker. The
  final policy retains enforcement but permits only the named `evolastra-worker`
  policy and validates the exact same-origin development or hashed production
  worker path.
- Prompt injection cannot be eliminated. The shipped boundary separates trusted
  developer rules from untrusted context, runs Codex offline in the repository
  sandbox, filters ambient credentials, forbids escalation, and requires review.

## Validation

`npm run check` and `npm run verify` pass. The release gate includes 130 Python
tests, 45 frontend tests, seven Playwright browser/accessibility flows, strict
type checks, the production build, source and asset scans, npm audit, and the
hash-locked Python dependency audit. Both dependency audits report no known
vulnerabilities.
