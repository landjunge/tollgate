# Tollgate

[![Website](https://img.shields.io/badge/website-live-3dd68c?style=flat-square)](https://landjunge.github.io/tollgate/)
[![GitHub release](https://img.shields.io/github/v/release/landjunge/tollgate?style=flat-square)](https://github.com/landjunge/tollgate/releases)
[![GHCR](https://img.shields.io/badge/ghcr.io-landjunge%2Ftollgate-blue?style=flat-square&logo=docker&logoColor=white)](https://github.com/landjunge/tollgate/pkgs/container/tollgate)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Discussions](https://img.shields.io/badge/discussions-open-6c8cff?style=flat-square)](https://github.com/landjunge/tollgate/discussions)
[![Launch](https://img.shields.io/badge/launch_post-2026--08-e8a317?style=flat-square)](https://landjunge.github.io/tollgate/blog/launch.html)
[![Checklist](https://img.shields.io/badge/safety_checklist-read-5dff9a?style=flat-square)](https://landjunge.github.io/tollgate/blog/checklist.html)

**v1.0.12** · *Pay the toll — or don't call.*

# “My AI agent must never go out of control.”

> **Tollgate is the safety layer between your AI agents and the internet.**

**Protect · Route · Prove** — stop runaway tool loops, enforce budgets, control outbound access, survive provider failures, produce evidence.

| | |
|--|--|
| **What** | Hard admission gate in front of tools / LLMs. Not a model catalog. |
| **Who** | People running n8n, LangGraph, CrewAI, or any OpenAI-compatible agent in production. |
| **Problem** | Agents loop, spend, and keep calling after the provider dies. |
| **Try** | 10 minutes, no Docker, no API key for the Protect demo. |

**Name note:** **landjunge/tollgate** (AI agent safety). Not [OpenTollGate](https://github.com/OpenTollGate) (network payments). Not a road toll. Not [4AllPass](https://github.com/landjunge/4AllPass) (credentials / “May I access?”). Tollgate answers **“May I act?”** — separate product.

**Website:** [landjunge.github.io/tollgate](https://landjunge.github.io/tollgate/) · [DE](https://landjunge.github.io/tollgate/de.html) · [Docs](https://landjunge.github.io/tollgate/docs.html) · [Launch](https://landjunge.github.io/tollgate/blog/launch.html) · [Safety checklist](https://landjunge.github.io/tollgate/blog/checklist.html)

**Sibling (execution desk):** [Gnom-Hub-V1](https://github.com/landjunge/gnom-hub-v1) — brainstorm freely, Execute on purpose. Not a Tollgate dependency.

## How this is built / Wie dieses Projekt entsteht

**System Designer & Product Architect** — Daniel Filipek (landjunge)

Ich arbeite anders: Ich entwickle Systeme und Produkte mit KI als technischem Partner.

Meine Stärke liegt darin, Probleme zu erkennen, Systeme in eigenständige Werkzeuge zu zerlegen und klare Grenzen und Schnittstellen zu definieren. Produktvision, Prioritäten und Architekturentscheidungen kommen von mir. KI ist der technische Partner für Implementierung, Tests und Dokumentation.

Ich bin kein klassischer Softwareentwickler und kein Security-Spezialist. Die technische Umsetzung entsteht gemeinsam mit KI und muss – besonders bei sicherheitskritischen Projekten – überprüfbar sein.

Was ich einbringe: Idee, Systemdenken, Anforderungen, gewünschtes Verhalten, klare Grenzen.  
Was überprüfbar sein muss: der Code, die Specs, die Tests. Reviews sind willkommen.

Open Source und öffentlich entwickelt. Kritik, Tests und Beiträge sind willkommen.

Tollgate beantwortet **„Darf ich handeln?“** — ein eigenes Produkt, kein Plugin der anderen.

```text
AI Agent
   │
   ├── tool call #1
   ├── tool call #2
   ├── tool call #3
   ├── tool call #4
   └── tool call #5

Tollgate

🛑 TOOL LOOP LIMIT EXCEEDED

Agent blocked.
Budget remaining: $1.72
Evidence recorded.
```

---

## 10 minutes (cold start)

**Primary path: native Python — no Docker.** Protect demo needs no provider keys.

```bash
git clone https://github.com/landjunge/tollgate.git && cd tollgate
python3 -m venv .venv && .venv/bin/pip install -e .
./scripts/ten-minute.sh
# 60-second Protect story (optional, server on :8787):
./scripts/demo-agent-safety.sh
```

**USB stick / portable desk** (venv + data on the volume):

```bash
./scripts/portable-setup.sh
./scripts/run.sh
# details: docs/PORTABLE.md
```

You should experience:

| Step | What happens |
|------|----------------|
| **Protect** | Agent tool-loop → `🛑 REQUEST BLOCKED` (no $ required) |
| **Prove** | Chaos / failover simulation → survived or clear next step |
| **Result** | `tollgate certificate` scorecard + [dashboard](http://127.0.0.1:8787/dashboard) |

**Start here (3 docs):**  
[Quickstart](docs/QUICKSTART.md) · [Portable / USB](docs/PORTABLE.md) · [How it works](docs/HOW_IT_WORKS.md) · [Production checklist](docs/PRODUCTION_CHECKLIST.md)

**More:** [SECURITY.md](docs/SECURITY.md) · [OPENAI.md](docs/OPENAI.md) · [HILFE.md](docs/HILFE.md) (DE) · [FAQ.md](docs/FAQ.md) · `tollgate help` · `tollgate doctor`

If that path is confusing, **stop shipping features** — fix the path.

---

## Who it’s for

| | |
|--|--|
| Teams running agents in production | cost · loops · outages · audit · freeze |
| Agent frameworks (LangGraph, CrewAI, …) | sit in front of tools + LLMs |
| n8n / automation | stop workflow agent-loops at the gate |

**Wedge:** LiteLLM connects models. Helicone shows traffic. **Tollgate keeps agents in line.**

---

## Product (short)

| Pillar | Job |
|--------|-----|
| **Protect** | Budgets, tool-loop hard stops, scopes, freeze, audit |
| **Route** | Health-aware failover, circuits |
| **Prove** | Chaos/DR tests, resilience score, certificate scorecard |

Deep dive: [docs/PRODUCT.md](docs/PRODUCT.md) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Everyday commands (after the 10 minutes)

```bash
tollgate status
tollgate certificate --application "Customer Support Agent"
tollgate consumer-budget support-agent --max-usd-day 2 --max-tool-calls 20
tollgate chaos test opencode_zen --requests 10
tollgate freeze --reason "panic"    # kill switch
tollgate report                     # day brief
```

Point an agent / OpenAI SDK:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=support-agent   # open mode label, or id:secret
```

---

## vs gateways (optional reading)

| | **Tollgate** | LiteLLM | Helicone |
|--|--------------|---------|----------|
| Core job | **Agent safety + DR proof** | Multi-provider proxy | Observability |
| Pre-admission hard deny | ✅ | optional | mostly post-hoc |
| Chaos / prove | ✅ first-class | DIY | — |

---

## Docs index

| Doc | When |
|-----|------|
| [HILFE.md](docs/HILFE.md) | **Hilfe (Deutsch)** |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | **User guide (English)** |
| [FAQ.md](docs/FAQ.md) | **FAQ** |
| [TEN_MINUTE.md](docs/TEN_MINUTE.md) | First 10 minutes |
| [DEMO.md](docs/DEMO.md) | Pitch / screen share |
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Setup details |
| [MAP.md](docs/MAP.md) · `tollgate search` | Find code |
| [N8N.md](docs/N8N.md) · [OPENAI.md](docs/OPENAI.md) | Integrations |
| [CHANGELOG.md](CHANGELOG.md) | Releases · **v1.0.0+** |

**License:** MIT · **Python:** ≥ 3.11 · **Repo:** [landjunge/tollgate](https://github.com/landjunge/tollgate)
