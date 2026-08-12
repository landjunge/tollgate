# Product north star — Tollgate (landjunge)

**Stand:** 2026-08-12  
**Phase:** Stop growth of surface area. Prove one real retention loop.

---

## What we already have (enough)

| Layer | Status |
|-------|--------|
| Core safety (Protect · Route · Prove) | Real code + tests |
| Control Room WebUI | Real product UI — polish, don’t rebuild |
| Cold path `ten-minute.sh` | Exists — keep improving until stranger-proof |
| Marketing surface | Site, SEO, press, lists, GHCR — **pause further content** |
| Night-shift / Control Room look | **Keep** — not “AI productivity SaaS” |

---

## Explicit STOP

Do **not** prioritize:

- More SEO / IndexNow / GSC / blog / press / awesome lists  
- More landing pages  
- More product pillars or **Organization/Enterprise surface** (see PRODUCT_TIERS.md)  
- Feature thrash while cold path is soft  
- Artificial paywalls that hobble Core

Marketing infrastructure is **done enough** until conversion is proven.

---

## The only number that matters

```text
Visitor → Get started → Install → First protected request
```

Optional stretch after that:

```text
… → Connect provider → Prove once → Leave it running
```

**Not:** pageviews, impressions, stars, likes.

### Funnel target (sanity check)

| Step | Rough goal |
|------|------------|
| Visitors | 100 |
| Get started click | ~20 |
| Install | ~10 |
| Protect first agent / first hard deny felt | ~5–7 |
| Prove once | ~3 |

If **3/100** complete protect + prove voluntarily, we have a product candidate.

---

## Product promise (sales language)

**Wrong:** “Configure your AI gateway.”

**Right:** “Connect your agent. Tollgate protects it automatically.”  
Then: “Want more control? Configure policies.”

Free-first · guided init · auto agent registration (direction already in recent work) — **continue that**, not more marketing.

---

## Next engineering (ordered)

1. ~~**Control Room first success**~~ — landed  
2. ~~**Cold path friction**~~ — `ten-minute.sh` prints protection summary + opens dashboard; clearer NEXT steps  
3. ~~**Open-mode safety**~~ — `HOST` default 127.0.0.1; serve warns on public bind; `/v1/health.security` + dashboard banner  
4. **One real user** — **gnom-hub-v1 as the real app** (not a toy agent)  
   - Protocol: [E2E_GNOM_HUB.md](E2E_GNOM_HUB.md)  
   - Smoke: `./scripts/e2e-gnom-hub.sh` (HTTP pipe)  
   - Manual: run gnom with `TOLLGATE_URL=http://127.0.0.1:8787` and observe the desk

### Name (entschieden 2026-08-12)

**Tollgate bleibt.** Kein Rename, kein `landjunge-tollgate`-Prefix als Marke.

- Repo: `landjunge/tollgate`
- Produkt: Tollgate — safety layer, Protect · Route · Prove
- Disambiguation bleibt in Site/FAQ: **nicht** OpenTollGate, **nicht** Straßenmaut
- SEO/Copy: weiter mit „Tollgate AI agent safety“ / landjunge qualifizieren, wo nötig

---

## Stop rule (README + here)

> If the first 10 minutes are confusing, **stop shipping features** — fix the path.

---

## See also

- **[GAP_ANALYSIS_14.md](GAP_ANALYSIS_14.md)** — 14-point reviewer scorecard (done/missing)  
- **[PRODUCT_TIERS.md](PRODUCT_TIERS.md)** — Core (full) vs Organization (ops layer)  
- **[TEN_MINUTE.md](TEN_MINUTE.md)** · **[PRODUCT.md](PRODUCT.md)** · **[VISION.md](VISION.md)**

*Aligned with external product read: high concept/tech, not yet “proven by users.”*
