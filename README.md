# Tollgate

**v1.0.2** · *Pay the toll — or don't call.*

# “My AI agent must never go out of control.”

> **Tollgate is the safety layer between your AI agents and the internet.**

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
# Docker variant
docker compose up -d --build
docker compose exec tollgate tollgate demo --skip-chaos
docker compose exec tollgate tollgate certificate
```

**Stranger test doc:** [docs/TEN_MINUTE.md](docs/TEN_MINUTE.md)  
**Full storyboard:** [docs/DEMO.md](docs/DEMO.md)

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
| [TEN_MINUTE.md](docs/TEN_MINUTE.md) | **First visit** |
| [DEMO.md](docs/DEMO.md) | Pitch / screen share |
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Setup details |
| [MAP.md](docs/MAP.md) · `tollgate search` | Find code |
| [N8N.md](docs/N8N.md) · [OPENAI.md](docs/OPENAI.md) | Integrations |
| [CHANGELOG.md](CHANGELOG.md) | Releases · **v1.0.0** |

**License:** MIT · **Python:** ≥ 3.11 · **Repo:** [landjunge/tollgate](https://github.com/landjunge/tollgate)
