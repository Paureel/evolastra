# Quality and reliability report

_Executed evidence and remaining gaps for the 2026-07-17 local vertical slice_

---

## 📋 Summary

The dedicated reliability suite collects 24 tests and all 24 pass after fixes for the original five defects plus a release-gate cross-run identity collision. The tests cover ordering, idempotency, unknown events, replay, snapshots, projection integrity, simulator counts and identity, redacted exports, SSE cursor resume, mixed batches, and metric floods.

The complete Python suite was executed after the reliability, integration, payload-validation, and cross-run identity fixes. All 75 Python tests pass.

## 🧪 Executed commands

| Command | Result |
| --- | --- |
| `python -m pytest tests/quality tests/property tests/chaos -q -rxX` before fixes | 18 passed, 5 strict xfailed |
| `python -m pytest <five defect tests> --runxfail -q` before fixes | 5 failed as expected, reproducing `QUAL-001` through `QUAL-005` |
| `python -m pytest tests/quality tests/property tests/chaos -q` after fixes | 24 passed |
| `python -m ruff check tests/quality tests/property tests/chaos` | Passed |
| `python -m ruff format --check tests/quality tests/property tests/chaos` | Passed |
| `.venv\Scripts\python.exe scripts\verify.py` after all fixes | Practical gate passed; 75 Python, 3 frontend, and 2 Playwright scenarios passed |
| `$env:PYTHONPATH='apps/api'; python -m pytest tests/integrations -q` | 15 passed |
| `$env:PYTHONPATH='apps/api'; python -m pytest tests/security -q -rxX` before marker cleanup | Passed; `SEC-004` marker XPASSed and was subsequently removed |
| `npm --prefix apps/web run test` | Passed: 1 file, 3 tests |
| `npm --prefix apps/web run typecheck` | Passed |
| Clean `npm ci` followed by typecheck, tests, build, audit, and Playwright | Passed; zero known vulnerabilities |
| Clean Python install from `requirements.lock` with `--require-hashes`, then `pip check` and pytest | Passed; 75 tests and no broken requirements |
| Inline five-run, 100,000-event reducer benchmark after optimization | Correctness passed in all runs; 4.101 s median, 24,387 events/s median; regression alerts passed |

The final evidence uses repository-local and disposable clean environments, not the earlier shared global interpreter.

## 📊 Coverage matrix

| Requirement | Evidence | Status |
| --- | --- | --- |
| Monotonic per-run ordering | Generated reordered/gapped sequences | Executed and passing |
| Idempotent duplicate processing | 1, 2, 7, and 31 repeated deliveries | Executed and passing |
| Immutable conflicting duplicate | Same ID with changed payload | Executed and passing |
| Unknown entity tolerance | Future entity `v99` persisted and ignored | Executed and passing |
| Unknown known-entity version | Future node action/version | Executed and passing after `QUAL-002` fix |
| Snapshot equivalence | Sequence-50 snapshot vs independent replay | Executed and passing |
| Full rebuild determinism | Rebuild vs current projection | Executed and passing |
| Projection gap health | Deleted durable sequence | Executed and passing |
| Embedded projection lag | Stale `state.last_sequence` | Executed and passing after `QUAL-003` fix |
| Simulator contract | 213 events, two proposed directions, and required family counts | Executed and passing |
| Fixed-seed simulator identity | Two builds with same run and seed | Executed and passing after `QUAL-001` fix |
| Cross-run simulator identity | Two runs with the same seed have disjoint event IDs | Executed and passing after `QUAL-006` fix |
| Export redaction | JSONL and reproduction ZIP | Executed and passing |
| Obsidian member uniqueness | Colliding sanitized titles | Executed and passing after `QUAL-004` fix |
| SSE resume | Greater of query/header cursor | Executed and passing |
| Mixed-batch isolation | Valid, malformed, valid sequence | Executed and passing |
| Metric-flood durability | 510 durable samples, 500 projected | Executed and passing |
| Failed retry audit history | Invalid quarantine retried | Executed and passing after `QUAL-005` fix |

## ✅ Resolved defects

| ID | Severity | Initially reproduced behavior | Implemented resolution | Fresh verification |
| --- | --- | --- | --- | --- |
| `QUAL-001` | Medium | Same run ID and seed produced different event lists at index 0 | Simulator now derives UUIDv4 identifiers and logical timestamps from the seed | Passing ordinary regression test |
| `QUAL-002` | High | `galaxy.analysis.node.enriched.v99` created a projected node | Reducer now gates supported v1 types and actions | Passing ordinary regression test |
| `QUAL-003` | High | Integrity reported `ok: true` when `state.last_sequence` was stale | Integrity now checks the embedded projection cursor | Passing ordinary regression test |
| `QUAL-004` | Medium | Two sanitized titles created the same ZIP member | Export names now include collision-proof stable identity | Passing ordinary regression test |
| `QUAL-005` | Medium | Failed retry deleted original quarantine history | Retry now retains the record and increments attempt history | Passing ordinary regression test |
| `QUAL-006` | High | Later seeded runs reused globally unique event IDs and remained at sequence 1 | Event identity is deterministically namespaced by run ID and seed | Passing unit and Playwright regression tests |

Before the original fixes, all five expected-failure tests failed with marker handling disabled. After all fixes, those tests and the cross-run regression pass without markers in the 24-test owned suite.

## 🔐 Existing security-test status

The broader known-family payload validation passes its `SEC-004` regression, and the security owner removed its stale expected-failure marker. The final complete Python run has no expected failures or unexpected passes.

An intermediate reducer benchmark was approximately 43% slower by median throughput than the earlier baseline. Profiling identified per-event construction of the supported-action registry in `_parse_type`; hoisting it to module scope restored throughput to within roughly 6% of the original median while retaining the strict registry behavior.

## 🌐 Recommended, not executed

- SSE disconnect/reconnect across multiple real browser engines
- Keyboard, screen-reader, reduced-motion, high-contrast, and text-scaling review
- Multi-process concurrent producer tests against PostgreSQL
- Process termination during event/snapshot transactions
- Projection rebuild and snapshot restoration latency at 100,000 durable events
- Browser performance against the 6,000-object and 20,000-edge renderer fixture
- Long-running resource-leak and SSE connection-limit tests
- Artifact preview fuzzing for supported binary and tabular formats

These items are coverage gaps. They are not inferred passes from unit or in-memory tests.

## 📌 Release recommendation

The practical local-profile release gate passes from locked clean installs. This is not certification for internet-facing, multi-user, PostgreSQL, 6k/20k browser-scale, crash-injection, or long-soak operation; those remaining boundaries are explicit in the gap matrix.
