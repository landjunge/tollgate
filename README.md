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

**Website:** [landjunge.github.io/tollgate](https://landjunge.github.io/tollgate/) · [DE](https://landjunge.github.io/tollgate/de.html) · [Docs](https://landjunge.github.io/tollgate/docs.html) · [Launch](https://landjunge.github.io/tollgate/blog/launch.html) · [Safety checklist](https://landjunge.github.io/tollgate/blog/checklist.html) · [Press](https://landjunge.github.io/tollgate/press/) · [llms.txt](https://landjunge.github.io/tollgate/llms.txt)

**Pairs with:** [Gnom-Hub](https://github.com/landjunge/gnom-hub-v1) — local multi-agent desk (brainstorm free, Execute on purpose) · [site](https://landjunge.github.io/gnom-hub-v1/)

**Protects AI agents in production** — not an API gateway, not a model catalog.

```text
Control cost.  Survive provider failures.  Prove it works.
        Protect  ·  Route  ·  Prove
```

---

## 10 minutes (cold start)

**Only path a stranger needs:**

```bash
git clone https://github.com/landjunge/tollgate.git && cd tollgate
python3 -m venv .venv && .venv/bin/pip install -e .
./scripts/ten-minute.sh
```

You should experience:

| Step | What happens |
|------|----------------|
| **Protect** | Agent tool-loop → `🛑 REQUEST BLOCKED` (no $ required) |
| **Prove** | Chaos / failover simulation → survived or clear next step |
| **Result** | `tollgate certificate` scorecard + [dashboard](http://127.0.0.1:8787/dashboard) |

```bash
# Docker variant (compose from repo)
docker compose up -d --build
docker compose exec tollgate tollgate demo --skip-chaos
docker compose exec tollgate tollgate certificate

# Or pull prebuilt image from GHCR
docker pull ghcr.io/landjunge/tollgate:latest
docker run --rm -p 8787:8787 -v "$PWD/data:/data" ghcr.io/landjunge/tollgate:latest
```

> **Note:** First GHCR publish is private by default. Package settings → *Change visibility* → **Public**  
> (one-time, irreversible): https://github.com/users/landjunge/packages/container/tollgate/settings

**Stranger test:** [docs/TEN_MINUTE.md](docs/TEN_MINUTE.md)  
**Full help:** [docs/HILFE.md](docs/HILFE.md) (DE) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md) (EN) · [docs/FAQ.md](docs/FAQ.md)  
**Demo:** [docs/DEMO.md](docs/DEMO.md) · `tollgate help` · `tollgate help env`

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
