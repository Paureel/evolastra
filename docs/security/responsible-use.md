# Responsible use and limitations

Evolastra is experimental research software. It visualizes and dispatches
agentic analysis; it does not make generated conclusions, code, or actions safe
or correct by itself.

## Operator responsibilities

- Run the companion only on loopback and use Tailscale federation only with
  people you trust. Never expose the ordinary companion API or use Funnel.
- Keep credentials, private keys, environment files, patient-level data, and
  unrelated confidential material outside the repository workspace.
- Treat imported analyses, repository content, model output, and published
  multiplayer summaries as untrusted until reviewed.
- Review every Codex mission before launch, inspect every resulting task and
  diff, and run `npm run verify` before deployment or reuse.
- Obtain authorization before analyzing systems, repositories, or data that you
  do not own. Follow applicable laws, licenses, data-use agreements, and
  professional obligations.
- Do not rely on the software or its generated hypotheses as medical, clinical,
  legal, safety-critical, financial, or security advice.

## Prompt injection and agent autonomy

Evolastra uses defense in depth: explicit pairing and launch, protocol-level
developer instructions, untrusted-context labeling, workspace-only writes,
network-disabled commands, disabled web search, filtered environment variables,
and no permission escalation. These controls reduce likelihood and blast radius;
they cannot prove that a language model will never misunderstand or follow an
adversarial instruction. Human review remains mandatory.

## Warranty and liability

The repository is licensed under the [MIT License](../../LICENSE). The Software
is provided **as is**, without warranty, and the authors or copyright holders are
not liable for claims, damages, or other liability arising from the Software or
its use. This page explains expected safe operation; it does not add a use
restriction, change the license, or provide legal advice.
