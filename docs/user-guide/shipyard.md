# Shipyard and Codex missions

_Build persistent agent vessels and launch explicit work from the command star_

---

The shipyard turns Evolastra into a two-way observatory. A paired user can build
a vessel inside the active analysis and dispatch a written mission into a new
task owned by the same signed-in Codex installation. Codex app-server is the
documented local interface for rich clients that need thread creation,
conversation history, approvals, and streamed events.[^1]

## 🚀 Open the drydock

1. Open the starting system in **System View**.
2. Click the central command star, or select it and press `Enter`.
3. Choose a blueprint and select **Build**.
4. Select the commissioned vessel, write one mission order, and choose
   **Launch mission**.

The new vessel is a durable Evolastra agent. It appears in the System View and
Galaxy Map, retains its Codex thread identity, and changes from `created` to
`running`, then `completed` or `failed` as the Codex turn progresses.

## 🛠️ Core hulls

| Hull | Codex operating prompt | Best use |
| --- | --- | --- |
| **Frigate** | Executes one bounded task directly and verifies it | Focused implementation, diagnosis, or review |
| **Mothership** | May spawn bounded Codex subagents and must synthesize them | Parallel investigation and cross-cutting work |
| **Colony ship** | Searches for underexplored, testable directions without overclaiming | Novel hypotheses and research expansion |

The shipyard does not select a model. Every task inherits the user's configured
Codex default.

## 🔬 Research hulls

Every completed tech-tree node unlocks a specialist blueprint named for that
problem. For example, completing **Contract friction** unlocks a Contract
friction specialist whose mission prompt includes that node's analytical
objective. Select **Build specialist ship** beneath a completed research node to
open the drydock with its hull preselected.

Researching, available, and locked nodes do not provide vessels. Replaying an
older event horizon does not rewrite the live unlock state.

## 🔐 Mission boundary

The browser sends build and launch requests only to the paired loopback
companion. The companion starts `codex app-server` over private stdio—never a
network listener—and fixes the Codex working directory to the Evolastra Git
checkout.

- Sandbox: `workspace-write`
- Approval policy: `never`
- Command network access: disabled
- Web search: disabled
- Child-process environment: allowlisted; ambient credentials are removed
- Model: configured Codex default
- Permission escalation: unavailable
- Prompt capture in Evolastra events: disabled by default

Trusted safety and hull instructions travel in the app-server's developer
instruction field. Direct mission text and imported analysis context stay at
user authority; imported titles and objectives are explicitly marked as
untrusted data rather than instructions. Developer instructions forbid external
apps, connectors, and MCP tools; separate protocol settings disable web search,
command network access, and permission escalation.

The mission text is necessarily present in the Codex task the user launches. In
Evolastra's semantic event log, the `prompt` field passes through the existing
default-deny content redaction and is stored as `[CONTENT_CAPTURE_DISABLED]`.
Codex authentication remains inside the local Codex installation and is never
returned to the viewer.

If a mission requires access beyond the repository sandbox, the ship reports the
block instead of silently escalating. Open the resulting task in Codex to review
its work or continue the conversation.

These controls reduce prompt-injection likelihood and blast radius; they cannot
prove that a language model will never follow an adversarial instruction.
Repository files and direct mission text may themselves be hostile. Keep secrets
outside the checkout, review the task and every resulting diff, and run
`npm run verify` before accepting or deploying the work. See
[Responsible use and limitations](../security/responsible-use.md).

## ⚠️ Availability

Dispatch requires all of the following:

- The installed Local Private companion is running
- The browser is paired
- Codex CLI is installed and signed in
- The configured checkout still exists and is a Git repository

The demo development server can build and render ships, but deliberately keeps
Codex dispatch offline. This prevents an unauthenticated development origin from
starting local tasks.

## 🔗 References

[^1]: OpenAI. (2026). "Codex App Server." https://learn.chatgpt.com/docs/app-server.md
