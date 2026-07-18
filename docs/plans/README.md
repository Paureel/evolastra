# Versioned plans

_Durable task state for cross-cutting and multi-session engineering work_

---

Plans are repository state, not chat history. Use them for work that crosses
multiple ownership boundaries, spans sessions, carries unresolved decisions, or
needs explicit validation evidence.

## 🔄 Lifecycle

1. Copy `template.md` to `active/YYYY-MM-DD-topic.md`.
2. Set `Status: active`, name the owner, and keep the date current.
3. Update decisions, progress, surprises, and validation as work proceeds.
4. When all outcomes and checks are complete, set `Status: completed` and move
   the file to `completed/` in the same commit.

Small, obvious, single-surface changes do not require a plan. Never create a plan
only to restate a ticket.

The harness verifies lifecycle metadata and a validation section for every plan.
