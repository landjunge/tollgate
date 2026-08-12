# Product tiers — Core vs Organization

**Stand:** 2026-08-12  
**Entscheidung:** Kein „Enterprise als Feature-Paywall“.  
**Name:** Tollgate bleibt. Open Source first.

---

## Leitprinzip

| | |
|--|--|
| **Tollgate Core** | Vollständiges Tollgate für **einen Betreiber** (Dev, Desk, kleines Team) |
| **Tollgate Organization** | Betriebsebene **über** Core für **eine Organisation** |

**Nicht:**

> Community = 50 % der Funktionen · Enterprise = 100 %

**Sondern:**

> Core = mächtiges, fertiges Safety-Produkt.  
> Organization = Skalierung, Governance, Multi-Team — **Operating Model**, kein künstliches Lock.

Wenn Monetarisierung nicht im Vordergrund steht, kann man sogar sagen:

> *Tollgate is free. Organization is how you run it at company scale — not a paywall.*

Sprache nach außen: **Core** / **Organization** — nicht prominent „Enterprise“ (vermeidet die Erwartung „Features absichtlich gesperrt“).

---

## Architecture sketch

```text
                 ORGANIZATION  (optional layer)
                          │
               ┌──────────┴──────────┐
               │                     │
             TEAM A               TEAM B
               │                     │
           Agents                 Agents
               │                     │
               └──────────┬──────────┘
                          ↓
                   TOLLGATE CORE
              Protect · Route · Prove
                          │
           ┌──────────────┼──────────────┐
           ↓              ↓              ↓
        OpenAI        Anthropic       Other
```

Core läuft **ohne** Organization.  
Organization **benötigt** Core — sie ersetzt ihn nicht.

---

## 🟢 Tollgate Core (heute + nah)

Ein einzelner Betreiber kann:

| Fähigkeit | Status (v1) |
|-----------|-------------|
| Install + cold path | ✅ |
| Provider anschließen | ✅ |
| Agent-/Consumer-Lanes + Budgets | ✅ |
| Tool-loop / rate hard stops | ✅ |
| Scopes (provider/intent/op) | ✅ |
| Routing + health-aware failover | ✅ |
| Circuits + freeze kill switch | ✅ |
| Prove: chaos + certificate + doctor | ✅ |
| Audit + report + Control Room | ✅ |
| OpenAI/Anthropic drop-in, MCP, n8n | ✅ |
| Snapshot export/import | ✅ |
| Webhook alerts | ✅ |

**Zielgefühl:**  
*Connect your agent. Tollgate protects it automatically.*  
Policy später verschärfen — nicht zuerst Config-Friedhof.

**Out of scope for Core:** SSO, multi-tenant orgs, central multi-team RBAC, multi-region fleet.

---

## 🔵 Tollgate Organization (später — nur echte Org-Probleme)

Alles hier muss die Frage bestehen:

> *Ist das ein Organisations-/Betriebsproblem, oder nur „noch ein technisches Feature“?*

### Organization structure
- mehrere Teams / Projekte / Environments  
- globale Policies über Teams  
- zentrale Provider-Katalog-Verwaltung (org-weit)

### Governance
- RBAC (wer darf freeze / chaos / config)  
- zentrale Agent-Policies + Allow/Deny (Models, Providers)  
- Team-Budgets + globale Budgets  
- Approval-Regeln (z. B. God-Mode / freeze off)

### Operations
- zentrale Health über **mehrere** Tollgate-Instanzen  
- org-weite Audit-Historie + Retention  
- Incident history  
- zentrale Alerts / on-call hooks  
- DR-/Chaos-**Pläne** (nicht nur einmaliger CLI-Test)  
- Resilience reports für Stakeholder

### Security
- SSO / OIDC (SAML optional)  
- Secret management integration  
- Netzwerk-Policies / private deploy patterns  
- getrennte Environments (prod/stage) mit Policy-Vererbung

### Reliability at scale
- multi-instance / multi-region fleet  
- automatische DR-Prüfungen im Kalender  
- Recovery **evidence** packs (über `certificate` hinaus)

### Explizit **nicht** Organization (→ Core oder streichen)

| Idee | Warum nicht Org |
|------|-----------------|
| „Mehr Provider im Katalog“ | Core Route |
| „Schönere Charts“ | Core UI polish |
| „Noch ein Chaos-Flag“ | Core Prove |
| „Agent chat memory“ | **Non-goal** (ops only) |
| Features nur sperren um zu verkaufen | verboten in diesem Modell |

---

## Kritischer Test für jeden „Enterprise“-Eintrag im Repo

Vor dem Bauen fragen:

1. Braucht das **mehr als einen Betreiber / ein Desk**?  
2. Braucht das **Identität & Rechte über Personen**?  
3. Braucht das **mehrere Instanzen / Environments**?  
4. Löst das ein **Compliance-/Audit-/Budget-Org**-Problem?

Wenn 4× nein → gehört es in **Core** (oder gar nicht).

---

## Mapping alter Sprache

| Alt (vermeiden) | Neu |
|-----------------|-----|
| Community = abgespeckt | **Core = vollständig** |
| Pro = Analytics-Paywall | History/multi-desk nur wenn klar Core- oder Org-Problem |
| Enterprise = Feature-Sack | **Organization = Operating model** |
| „Enterprise-Tarif“ | optional später; Architektur unabhängig davon |

---

## Was wir **jetzt** tun (Core)

Siehe [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md):

1. Conversion: install → first protected request  
2. Control Room first-success (weitgehend gelandet)  
3. Cold path + open-mode safety  
4. **Ein realer Nutzer**  
5. **Kein** Org-Layer bauen, bis Core-Retention bewiesen ist  

Organization-Design-Dokumente dürfen existieren — **Implementierung wartet**.

---

## See also

- [PRODUCT.md](PRODUCT.md) — product story  
- [VISION.md](VISION.md) — roadmap  
- [PRODUCT_NORTH_STAR.md](PRODUCT_NORTH_STAR.md) — current phase  
