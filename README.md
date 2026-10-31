**English** · [Deutsch](README.de.md)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/design/icons/dark/TollGate-dark-256.png">
    <img src="assets/design/icons/light/TollGate-light-256.png" alt="TollGate" width="256" height="256">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/landjunge/threaddesk/blob/docs/product-family-readme-20261031/README.md" title="ThreadDesk"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/ThreadDesk-dark-128.png">
    <img src="assets/readme/ThreadDesk-light-128.png" alt="ThreadDesk" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/KiraBridge/blob/docs/product-family-readme-20261031/README.md" title="KiraBridge"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/KiraBridge-dark-128.png">
    <img src="assets/readme/KiraBridge-light-128.png" alt="KiraBridge" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/4AllPass/blob/docs/product-family-readme-20261031/README.md" title="4AllPass"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/4AllPass-dark-128.png">
    <img src="assets/readme/4AllPass-light-128.png" alt="4AllPass" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/agent-authority-lab/blob/docs/product-family-readme-20261031/README.md" title="Agent Authority"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/Agent-Authority-dark-128.png">
    <img src="assets/readme/Agent-Authority-light-128.png" alt="Agent Authority" width="48" height="48">
  </picture></a>
</p>

<h1 align="center">TollGate</h1>

<p align="center"><strong>A safety gate for AI agents.</strong></p>

TollGate checks connected model and tool calls before they execute. It helps stop repeated calls, limit usage and explain decisions.

**Source version: 1.0.12 · In development · Python 3.11 or newer**

[Quick start from source](docs/QUICKSTART.md) · [View source](https://github.com/landjunge/tollgate/tree/main)

There is no published desktop installer. The [announcement release](https://github.com/landjunge/tollgate/releases/tag/announce-public) has no packaged downloads. Use requires permission under the [license](LICENSE).

## What is available today

- **Protect:** usage limits, loop protection, rules for permitted access and a freeze for new calls.
- **Route:** health-aware routing and failover to configured providers.
- **Prove:** outage and recovery simulations with reports about the tested setup.
- **Connections:** an OpenAI-compatible gateway, MCP and n8n; English and German controls.

The local workflow-control core adds durable reservations and stops for explicitly connected adapters. Acceptance with synthetic adapters is separate from configured production use with KiraBridge or 4AllPass. Cost estimates are not provider invoices and do not guarantee a spending cap for arbitrary terminal agents.

**Boundary:** Freeze blocks new connected calls. It does not terminate arbitrary processes or undo effects already sent. [Workflow control](docs/WORKFLOW-CONTROL.md) · [Process stops](docs/WORKFLOW-PROCESS-STOP.md).

## Get started

With permission to use the software and Python 3.11 or newer:

```sh
git clone https://github.com/landjunge/tollgate.git
cd tollgate
python3 -m venv .venv
.venv/bin/pip install -e .
./scripts/ten-minute.sh
```

The Protect demo needs no provider keys. Then check the local dashboard to see why a call was allowed or blocked. Real model calls and routing require your own provider accounts. [Quick start](docs/QUICKSTART.md).

## Planned collaboration

The five products remain independent. The goal is a shared workflow with **KiraBridge as the communication hub**:

| Product | Role in the shared workflow |
| --- | --- |
| [ThreadDesk](https://github.com/landjunge/threaddesk/blob/docs/product-family-readme-20261031/README.md) | Keeps project context, knowledge and results. |
| [KiraBridge](https://github.com/landjunge/KiraBridge/blob/docs/product-family-readme-20261031/README.md) | Relays tasks, questions and replies between chat, local agents and tools. |
| [4AllPass](https://github.com/landjunge/4AllPass/blob/docs/product-family-readme-20261031/README.md) | Manages credentials; is intended to enable specifically approved access. |
| [TollGate](https://github.com/landjunge/tollgate/blob/docs/product-family-readme-20261031/README.md) | Checks connected calls and enforces usage limits and stops. |
| [Agent Authority](https://github.com/landjunge/agent-authority-lab/blob/docs/product-family-readme-20261031/README.md) | Shows observations, contradictions and missing evidence; does not approve actions. |

Some interfaces already exist. A fully configured and verified workflow across all five products is still planned. Approvals stay with the responsible tool and the human. KiraBridge and Agent Authority require access to their private repositories.

[User guide](docs/USER_GUIDE.md) · [Documentation](docs/README.md) · [Developer details](docs/DEVELOPERS.md) · [Product website](https://tollgate.netzwerkpunkt.de/)

## License and contributions

[Source-available, all rights reserved](LICENSE). Visible source does not grant general permission to use or redistribute it. Historical MIT license rights remain intact.

Product concept and architecture: **Daniel Filipek (landjunge)**. AI assists with implementation and documentation. The documented checks do not replace an independent security audit; verifiable reviews are welcome.
