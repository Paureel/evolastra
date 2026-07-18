# Replay guide

The bottom slider requests semantic state at an exact durable event sequence. Replay uses the nearest stored snapshot and reduces only subsequent events. **Return live** restores the current projection. Incoming events continue while viewing history.

Refresh restoration reads the latest projection from SQLite. SSE reconnects with a sequence cursor and native `Last-Event-ID` support. Replaying an ordered event log is covered by deterministic reducer and snapshot-equivalence tests.
