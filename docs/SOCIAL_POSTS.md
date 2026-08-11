# Ready-to-post announcements (Tollgate + Gnom-Hub)

Copy/paste. Links are live.

| Project | Site | Repo |
|---------|------|------|
| **Tollgate** | https://landjunge.github.io/tollgate/ | https://github.com/landjunge/tollgate |
| **Gnom-Hub** | https://landjunge.github.io/gnom-hub-v1/ | https://github.com/landjunge/gnom-hub-v1 |

---

## X / Twitter (short)

### Tollgate only

```
Tollgate — safety layer for AI agents in production.

Protect: hard-stop runaway tool loops & budgets
Route: failover when a provider dies
Prove: chaos test + reliability certificate

Not another LLM catalog.

https://landjunge.github.io/tollgate/
https://github.com/landjunge/tollgate
```

### Gnom-Hub only

```
Gnom-Hub — local multi-agent desk.

Brainstorm freely.
Workers run only when you press Execute.

No Docker. Visible agents. Safe computer-use.

https://landjunge.github.io/gnom-hub-v1/
https://github.com/landjunge/gnom-hub-v1
```

### Both (combo)

```
Two tools I built for production AI agents:

1) Gnom-Hub — local multi-agent desk
   Brainstorm first. Execute on purpose.
   https://landjunge.github.io/gnom-hub-v1/

2) Tollgate — safety layer in front of LLMs/tools
   Protect · Route · Prove (budgets, loops, chaos DR)
   https://landjunge.github.io/tollgate/

Open source · local-first
```

---

## Reddit / HN-style (English)

**Title options:**
- Show HN: Tollgate – safety layer for AI agents (Protect · Route · Prove)
- Show HN: Gnom-Hub – local multi-agent desk (brainstorm free, execute on purpose)
- Two open tools: multi-agent desk + agent safety gate

**Body (both):**

```text
I built two pieces that fit together for desktop / agent work:

**Gnom-Hub** — local multi-agent control hub
- Chat = brainstorm only
- Workers start when you press Execute (cost / files / tools)
- No Docker, Python FastAPI, visible agent cards
- Site: https://landjunge.github.io/gnom-hub-v1/
- Repo: https://github.com/landjunge/gnom-hub-v1

**Tollgate** — safety layer between agents and the internet
- Protect: budgets, tool-loop hard deny, freeze
- Route: health-aware failover + circuits
- Prove: chaos test + reliability certificate
- OpenAI drop-in base_url, MCP, n8n
- Site: https://landjunge.github.io/tollgate/
- Repo: https://github.com/landjunge/tollgate

Cold path for Tollgate (no keys needed for the Protect demo):

    git clone https://github.com/landjunge/tollgate.git && cd tollgate
    python3 -m venv .venv && .venv/bin/pip install -e .
    ./scripts/ten-minute.sh

Feedback welcome — especially the 10-minute cold path.
```

**r/LocalLLaMA / r/MachineLearning / r/selfhosted tags:** local, agents, tooling  
**Show HN:** keep title short; link one primary project, mention the other in the body.

---

## LinkedIn (longer)

```text
Two open tools for people running AI agents beyond the chat window:

1) Gnom-Hub — a local multi-agent desk
You brainstorm freely. Workers that spend money or touch the filesystem only start when you press Execute. Visible cards, tools, no Docker.

→ https://landjunge.github.io/gnom-hub-v1/

2) Tollgate — a safety layer in front of models and tools
Protect (budgets, tool-loop stops, freeze), Route (failover), Prove (chaos + certificate). Point your OpenAI SDK / n8n / MCP at it.

→ https://landjunge.github.io/tollgate/

If you ship agents in production, the hard part is not “call another model” — it is keeping them in line and knowing failover works.

Happy to take feedback.
```

---

## Deutsch (X / Mastodon)

```
Zwei Tools für AI-Agents:

1) Gnom-Hub — lokaler Multi-Agenten-Desk
   Brainstormen frei. Execute nur bewusst.
   https://landjunge.github.io/gnom-hub-v1/

2) Tollgate — Sicherheits-Schicht vor LLMs/Tools
   Protect · Route · Prove
   https://landjunge.github.io/tollgate/

Open Source · local-first
```

---

## Post via CLI (when X is authed)

```bash
# one-time
xurl auth   # complete OAuth

xurl post "Tollgate — safety layer for AI agents…

Protect · Route · Prove
https://landjunge.github.io/tollgate/
https://github.com/landjunge/tollgate"

xurl post "Gnom-Hub — local multi-agent desk…

Brainstorm freely. Execute on purpose.
https://landjunge.github.io/gnom-hub-v1/
https://github.com/landjunge/gnom-hub-v1"
```


---

## Already published (do not re-spam)

| Channel | URL |
|---------|-----|
| GitHub Gist | https://gist.github.com/landjunge/ce4190deb6536cc6134c767f500c4dc9 |
| Tollgate Discussions | https://github.com/landjunge/tollgate/discussions/10 |
| Gnom-Hub Discussions | https://github.com/landjunge/gnom-hub-v1/discussions/46 |
| Tollgate release | https://github.com/landjunge/tollgate/releases/tag/announce-public |
| Gnom-Hub release | https://github.com/landjunge/gnom-hub-v1/releases/tag/announce-public |
| Awesome AI Agents PR | https://github.com/aloth/awesome-ai-agents/pull/38 |
| Awesome LLMOps PR | https://github.com/tensorchord/Awesome-LLMOps/pull/735 |
| Awesome AI Tools PR | https://github.com/mahseema/awesome-ai-tools/pull/1955 |
| Awesome Selfhosted-data PR | https://github.com/awesome-selfhosted/awesome-selfhosted-data/pulls?q=is%3Apr+author%3Alandjunge |
| Awesome MCP Servers PR | https://github.com/punkpeye/awesome-mcp-servers/pull/11967 |
| Profile README | https://github.com/landjunge |
| Profile README | https://github.com/landjunge |
