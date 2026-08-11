# Tollgate — Hilfe & Handbuch

**Version:** 1.0.x · **Repo:** https://github.com/landjunge/tollgate  

> **Tollgate ist die Sicherheits-Schicht zwischen deinen AI-Agents und dem Internet.**  
> Nicht „API-Gateway“, nicht „Multi-LLM-Katalog“.

**Killer-Use-Case:** *„Mein AI-Agent darf niemals außer Kontrolle geraten.“*

| Schnell | |
|---------|--|
| 10 Minuten (kalt) | [TEN_MINUTE.md](TEN_MINUTE.md) · `./scripts/ten-minute.sh` |
| Demo (Protect + Prove) | [DEMO.md](DEMO.md) · `tollgate demo` |
| Control Room | http://127.0.0.1:8787/dashboard |
| CLI-Hilfe | `tollgate help` · `tollgate help agents` |
| English guide | [USER_GUIDE.md](USER_GUIDE.md) |

---

## 1. Was ist Tollgate?

Tollgate sitzt **vor** LLM-Providern und Tools:

```text
Agent / n8n / MCP-Client / OpenAI-SDK
              │
              ▼
           TOLLGATE
     Protect · Route · Prove
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  OpenAI  Anthropic  Zen/DeepSeek/…
```

### Drei Säulen

| Säule | Bedeutung | Typische Frage |
|-------|-----------|----------------|
| **Protect** | Budgets, Tool-Loop-Stops, Scopes, Freeze, Audit | Wird mein Agent teuer oder endlos? |
| **Route** | Health-aware Routing, Failover, Circuits | Was passiert, wenn OpenAI down ist? |
| **Prove** | Chaos-Test, Resilience-Score, Certificate | Kann ich das **beweisen**? |

### Was Tollgate **nicht** ist

- Kein Agent-Framework (kein LangGraph-Ersatz)
- Kein Speicher für Chat-Verläufe (nur Ops: Ledger, Audit, Circuits)
- Kein SaaS-Multi-Tenant-Katalog mit 100 Providern

---

## 2. Installation

### Voraussetzungen

- **Python ≥ 3.11**
- Optional: Docker
- Optional: API-Keys (für echte LLM-Calls; **Protect-Demo braucht keine Keys**)

### Lokal

```bash
git clone https://github.com/landjunge/tollgate.git
cd tollgate
python3 -m venv .venv
.venv/bin/pip install -e .

export TOLLGATE_HOME=$HOME/.tollgate   # oder fester Datenordner
mkdir -p "$TOLLGATE_HOME/User"

# Server starten
tollgate serve
# → http://127.0.0.1:8787
```

Oder Desk-Bootstrap:

```bash
./scripts/desk-ready.sh
```

### Docker

```bash
docker compose up -d --build
docker compose exec tollgate tollgate certificate
# Dashboard: http://127.0.0.1:8787/dashboard
```

### Erster Erfolg (ohne Feature-Tour)

```bash
./scripts/ten-minute.sh
# oder
tollgate demo
tollgate certificate
```

---

## 3. Daten & Secrets

### Datenverzeichnis

| Variable | Bedeutung |
|----------|-----------|
| `TOLLGATE_HOME` | Datenwurzel (enthält `User/`) |
| Default Desk | oft `~/.tollgate` oder Workspace-Pfad |

Unter `$TOLLGATE_HOME/User/`:

| Datei | Inhalt |
|-------|--------|
| `Key.txt` | API-Keys (nie committen) |
| `keys_app.json` | Limits, Routing, Envelopes, Freeze |
| `keys_usage.json` | Tages-Ledger (Calls, Tokens, $) |
| `consumers.json` | gehashte Consumer-Secrets (Auth-Modus) |
| `circuits.json` | Circuit-Breaker-Zustand |
| `audit.jsonl` | Append-only Audit |
| `chaos.json` | Chaos/DR-Status |

Vorlage Keys: `Key.txt.example` → nach `User/Key.txt` kopieren.

```bash
# Beispiel Key.txt
OPENCODE_API_KEY=…
DEEPSEEK_API_KEY=…
BRAVE_API_KEY=…
```

```bash
tollgate doctor          # prüft Pfade, Keys, Caps
tollgate paths           # zeigt data_home
```

**Regel:** Secrets nur in Tollgate — nie in Agent-Prompts oder n8n-Env mit echten Provider-Keys.

---

## 4. Kernkonzept: Consumer (Agent-Lane)

Ein **Consumer** ist eine logische Lane, z. B.:

- `support-agent`
- `coding-agent`
- `n8n`

Jeder Request trägt eine Identität:

```http
X-Consumer-Key: support-agent
# oder Auth-Modus:
X-Consumer-Key: support-agent:geheimes-token
Authorization: Bearer support-agent:geheimes-token
```

### Open Mode vs Auth Mode

| | Open Mode | Auth Mode |
|--|-----------|-----------|
| Wann | keine `consumers.json` / leer | Einträge vorhanden oder `TOLLGATE_REQUIRE_AUTH=1` |
| Key | beliebiges Label (z. B. `desk`) | `id:secret` |
| Desk | lokal ok | Pflicht bei Multi-Host / n8n remote |

```bash
tollgate consumer-add n8n
tollgate consumer-add desk --admin
# Secret wird EINMAL angezeigt
```

---

## 5. Protect — Agent schützen

### Budget & Loop-Limits setzen

```bash
tollgate consumer-budget support-agent \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-usd-hour 1 \
  --max-requests-minute 50 \
  --max-tool-calls 20 \
  --max-tokens-request 50000

tollgate consumer-budget --list
```

| Feld | Wirkung |
|------|---------|
| `max_usd_day` | Tagesbudget $ |
| `max_usd_request` | Hartes Limit pro Request (Schätzung) |
| `max_usd_hour` | Stundenfenster |
| `max_requests_minute` | RPM |
| `max_tool_calls` | **Tool-Loop-Tiefe** pro Turn |
| `max_tokens_request` | Token-Schätzung pro Request |

`0` / weglassen = unbeschränkt **auf dieser Dimension** (andere Dimensionen können greifen).

### Scopes (wer darf was)

```bash
tollgate consumer-budget support-agent \
  --allow-provider opencode_zen --allow-provider deepseek \
  --block-provider google \
  --allow-intent free_llm --allow-intent llm \
  --allow-op chat --allow-op search

tollgate consumer-budget support-agent --clear-scopes
```

### Tool-Loop demonstrieren (Aha #1)

Clients senden die **geschätzte Loop-Tiefe**:

```bash
curl -s http://127.0.0.1:8787/v1/invoke \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{
    "provider": "opencode_zen",
    "op": "chat",
    "tool_calls_est": 99,
    "arguments": {"message": "hi"},
    "agent_id": "support-agent"
  }'
```

Antwort enthält u. a.:

```json
"blocked": {
  "headline": "REQUEST BLOCKED",
  "reason": "max_tool_calls",
  "tool_calls": { "est": 99, "max": 20 },
  "message": "🛑 REQUEST BLOCKED\n…"
}
```

Im **Dashboard**: Overview → „Test tool-loop block“ oder Agents → „Test loop“.

### Globaler Kill-Switch (Freeze)

```bash
tollgate freeze --reason "runaway agents"
tollgate freeze status
tollgate unfreeze
# Env: TOLLGATE_FROZEN=1
```

Billable Traffic wird verweigert. System-Probes können weiterlaufen (`allow_system_when_frozen`).

---

## 6. Route — Failover & Health

Routing wählt Provider nach Intent (`free_llm`, `llm`, `search`, …), Limits und Health.

```bash
curl -s http://127.0.0.1:8787/v1/route \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{"intent":"free_llm","tokens_est":1000}'
```

Antwort kann `explain` enthalten: **warum** dieser Provider.

Circuits:

```bash
tollgate circuits list
tollgate circuits reset deepseek
tollgate circuits reset --all
```

---

## 7. Prove — Resilienz beweisen

```bash
# Provider-Ausfall simulieren + Failover messen
tollgate chaos test opencode_zen --requests 10
tollgate resilience
tollgate certificate --application "Customer Support Agent"
```

Dashboard → **Prove** → „Run test“.

Certificate-Scorecard:

```text
Budget Protection       PASS
Agent Loop Protection   PASS
Provider Failover       PASS / NOT_RUN
…
Resilience Score        nn/100
```

---

## 8. Control Room (WebUI)

**URL:** http://127.0.0.1:8787/dashboard  

| Bereich | Frage |
|---------|--------|
| **Overview** | Sicher? Kaputt? Zu teuer? Was tun? |
| **Agents** | Protection, Budgets, Loop-Test, Edit |
| **Providers** | Health, Latency, Kosten |
| **Prove** | Chaos-Test, Certificate |
| **Audit** | Wer wurde geblockt / warum |

Status-Badge oben: **PROTECTED** · **ATTENTION** · **FROZEN**

**Setup-Wizard** (erster Start / Button „Setup“):

1. Welcome  
2. Agent-Name  
3. Protection ($/Tag, $/Task, Tool-Calls, RPM)  
4. Speichern → optional sofort Loop-Test  

Feld **key** (oben rechts): im Open Mode beliebiges Label; im Auth Mode `id:secret`.

OpenAPI: http://127.0.0.1:8787/docs  

---

## 9. Clients anbinden

### OpenAI-kompatibel (größter Hebel)

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=support-agent   # oder id:secret
# model: tollgate/free | tollgate/auto | provider-modell
```

```bash
curl -s $OPENAI_BASE_URL/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tollgate/free",
    "messages": [{"role":"user","content":"hi"}],
    "max_tokens": 64,
    "tool_calls_est": 3
  }'
```

Extras: `tool_calls_est`, `tokens_est`, `prefer_free`, `request_class`.  
Header bei Erfolg: `X-Tollgate-Provider`, `X-Tollgate-Model`, …  
Bei Deny: `error.tollgate` + `Retry-After` / `X-Tollgate-Protection`.

Details: [OPENAI.md](OPENAI.md)

### Anthropic Messages

`POST /v1/messages` · [ANTHROPIC.md](ANTHROPIC.md)

### n8n

- Community-Node: `n8n-nodes-tollgate/`
- Oder OpenAI-Node mit `base_url` → Tollgate  
- [N8N.md](N8N.md)

### MCP (Cursor / Claude Desktop)

```bash
python -m tollgate
# oder: tollgate mcp
```

Beispiel-Config: `configs/mcp-tollgate.example.json` · [MCP.md](MCP.md)

---

## 10. CLI-Referenz

```bash
tollgate help                 # Themen-Übersicht
tollgate help protect
tollgate help prove
tollgate help ui
```

| Befehl | Zweck |
|--------|--------|
| `serve` | HTTP-Server (:8787) |
| `mcp` | MCP stdio |
| `doctor` | Diagnose (nach Install zuerst) |
| `health` / `paths` / `status` | Zustand |
| `certificate` | AI Reliability Report |
| `demo` | Live Protect+Prove Demo |
| `consumer-add` | Auth-Consumer anlegen |
| `consumer-budget` | Envelopes + Scopes |
| `chaos` | status / start / stop / test |
| `resilience` | Score 0–100 |
| `freeze` / `unfreeze` | Kill-Switch |
| `circuits` | list / reset |
| `audit` | Audit-Trail abfragen |
| `report` | Tagesbrief (md/json) |
| `alert` | Webhook test / events |
| `snapshot` | export / import Desk-State |
| `control` | Control-Plane JSON |
| `search` | Repo-Doku/Module suchen |
| `high-risk` / `provider-add` | Provider-Risiko / Scaffold |
| `suggest` | Vorschläge aus Ledger (nie auto-apply) |

### Häufige Beispiele

```bash
tollgate doctor
tollgate status
tollgate consumer-budget support-agent --max-usd-day 2 --max-tool-calls 20
tollgate chaos test opencode_zen --requests 8
tollgate certificate --application "Support Agent"
tollgate audit --event admit_deny --limit 20
tollgate freeze --reason "incident"
tollgate snapshot export -o desk.tgz
tollgate report --format md
```

---

## 11. HTTP-API (Überblick)

Basis: `http://127.0.0.1:8787`

| Methode | Pfad | Zweck |
|---------|------|--------|
| GET | `/dashboard` | Control Room UI |
| GET | `/docs` | OpenAPI |
| GET | `/v1/health` | Liveness + Freeze + Circuits |
| GET | `/v1/control` | Control-Plane (UI-Daten) |
| GET | `/v1/status` | Kompakter Status |
| GET | `/v1/certificate` | Scorecard |
| GET | `/v1/resilience` | Resilience JSON |
| GET | `/v1/chaos` | Chaos-Status |
| POST | `/v1/chaos/test` | Failover-Test (admin) |
| GET | `/v1/audit` | Audit-Query |
| GET | `/v1/budget` | Budget der Lane |
| GET/POST | `/v1/config` | Policy lesen/patchen (admin) |
| POST | `/v1/route` | Intent → Provider |
| POST | `/v1/invoke` | Admit + Call |
| POST | `/v1/chat/completions` | OpenAI Drop-in |
| POST | `/v1/messages` | Anthropic Drop-in |
| GET/POST | `/v1/freeze` | Kill-Switch |
| GET | `/v1/circuits` | Circuits |
| POST | `/v1/circuits/reset` | Reset (admin) |
| GET | `/metrics` | Prometheus (ggf. Auth) |

Vollständige Signaturen: laufender Server → `/docs`.

---

## 12. Webhooks & Metrics

### Alerts

```bash
export TOLLGATE_ALERT_WEBHOOK=https://…
# oder keys_app.json → cost_guard.alert_webhook_url
tollgate alert events
tollgate alert test
```

Events u. a.: `agent_protection`, `hard_deny`, `soft_budget`, `chaos_*`, `admission_frozen`.

### Metrics

```bash
curl -s http://127.0.0.1:8787/metrics
# Auth-Mode: Consumer-Key oder TOLLGATE_METRICS_TOKEN
# Öffentlich erzwingen: TOLLGATE_METRICS_PUBLIC=1
```

---

## 13. Portable / Snapshot

```bash
tollgate snapshot export -o desk.tgz      # ohne Key.txt
tollgate snapshot import desk.tgz
tollgate snapshot export -o full.tgz --include-secrets   # vorsichtig!
```

USB: [PORTABLE.md](PORTABLE.md)

---

## 14. Troubleshooting

| Symptom | Prüfung |
|---------|---------|
| Server startet nicht | `tollgate doctor` · Port 8787 frei? · Python ≥ 3.11 |
| 401 Unauthorized | Auth-Mode: `id:secret`? · `tollgate consumer-add` |
| Immer blocked | Envelope zu eng? · `freeze status`? · Scope? |
| Chaos „failed“ | ≥2 Provider in Intent-Chain? · Keys gesetzt? |
| Dashboard leer / alt | Hard-Refresh · `X-Consumer-Key` oben · Server-Version `/v1/health` |
| Metrics 401 | Token/Consumer oder `TOLLGATE_METRICS_PUBLIC=1` |
| Ledger / Budgets „kaputt“ | fail-closed by design · `keys_usage.json` prüfen |
| Falsche Daten-Home | `tollgate paths` · `echo $TOLLGATE_HOME` |

Logs bei Desk-Start oft: `/tmp/tollgate-desk.log`

---

## 15. Sicherheit (Kurz)

- Keys nur in `Key.txt` / Env, nie im Agent  
- Auth-Mode für alles außer reinem Localhost  
- Metrics & Config nicht ungeschützt im Internet  
- Audit/Redaction: keine Chat-Transcripts im Ledger  
- Freeze bei Incident  

---

## 16. Dokumenten-Karte

| Doc | Inhalt |
|-----|--------|
| [TEN_MINUTE.md](TEN_MINUTE.md) | Kalter 10-Minuten-Test |
| [DEMO.md](DEMO.md) | Killer-Demo Protect + Prove |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Setup-Schritte |
| [PRODUCT.md](PRODUCT.md) | Positionierung |
| [COST_LIMITS.md](COST_LIMITS.md) | Envelopes im Detail |
| [OPENAI.md](OPENAI.md) / [ANTHROPIC.md](ANTHROPIC.md) | Drop-ins |
| [N8N.md](N8N.md) / [MCP.md](MCP.md) | Integrationen |
| [OPERATIONS.md](OPERATIONS.md) | Betrieb |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schichten |
| [MAP.md](MAP.md) | Code-Index |
| [USER_GUIDE.md](USER_GUIDE.md) | English handbook |

CLI: `tollgate search <begriff>` · `tollgate search --map`

---

## 17. Support / Mitmachen

- Issues & Code: https://github.com/landjunge/tollgate  
- Feedback zur **10-Minuten-Reibung** ist wertvoller als Feature-Wünsche.  
- Lizenz: MIT  

**Pay the toll — or don't call.**
