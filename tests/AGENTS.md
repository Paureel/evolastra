# Test instructions

_Local guidance for deterministic regression and release evidence_

---

Scope: `tests/` and browser tests under `apps/web/e2e/`.

Read the [testing strategy](../docs/development/testing.md) before changing a
contract assertion.

## 🧪 Test rules

- Assert the intended invariant, not incidental implementation detail.
- Reproduce a defect with the smallest deterministic regression before fixing it.
- Do not weaken assertions, change seeds, add retries, or mark a failure expected
  merely to obtain a pass.
- Keep tests isolated from the user's local database, token, service, and private
  data.
- Browser tests must wait on observable UI state rather than arbitrary sleeps.
- Strict expected failures require a tracked defect and a removal condition.

Run the smallest suite first, `npm run check` during iteration, and
`npm run verify` before handoff.
