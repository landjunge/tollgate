# Production checklist — before real traffic

Use this **after** [QUICKSTART.md](QUICKSTART.md) works locally.

Tollgate has **no** formal `PRODUCTION` mode flag yet. This checklist is the practical gate.

---

## Security

- [ ] Bind is **localhost** or behind a reverse proxy with auth  
  - Default: `HOST=127.0.0.1`  
  - `HOST=0.0.0.0` + open mode is **refused** unless `TOLLGATE_ALLOW_OPEN_PUBLIC=1`  
  - Shared/public: `tollgate consumer-add` (auth mode)  
- [ ] Prefer **auth mode** (`consumers.json` or `TOLLGATE_REQUIRE_AUTH=1`) for shared hosts  
- [ ] Provider secrets only in `User/Key.txt` / env — never in agent prompts  
- [ ] Metrics not public (`TOLLGATE_METRICS_PUBLIC` off unless intentional)  
- [ ] Dashboard not exposed unauthenticated on the public internet  

## Protect

- [ ] Named policies for real agents (not only `_default`)  
- [ ] Daily budget + `max_tool_calls` set for each lane  
- [ ] Freeze procedure known: `tollgate freeze` / unfreeze  
- [ ] Loop test felt once: Dashboard → *See protection in action*  

## Route

- [ ] ≥2 providers in the free_llm / critical chain  
- [ ] Keys present for fallbacks  
- [ ] Chaos / failover test run at least once  

## Prove

- [ ] `tollgate certificate` overall understood (PASS / FAIL / Prove pending)  
- [ ] Audit readable: `tollgate audit --event admit_deny`  
- [ ] Snapshot backup known: `tollgate snapshot export`  

## Ops

- [ ] `tollgate doctor` clean enough for your desk  
- [ ] Restart recovery: config under `$TOLLGATE_HOME` survives process restart  
- [ ] Alerts/webhooks only if you need them (optional)  

---

## Commands

```bash
tollgate doctor                   # includes production_readiness %
tollgate certificate
tollgate chaos test <provider>    # when ready
tollgate snapshot export -o desk.tgz
tollgate freeze --reason "incident"
```

`tollgate doctor` prints **Production readiness · N%** from bind/auth, policies, secrets, failover test, freeze state.

---

## If something fails

Human-readable denials prefer:

> *Agent «x» was blocked: daily budget exceeded.*

not only `HTTP 402`.

Failover success may show:

> *OpenAI was unavailable. Tollgate switched this request to …*  
(`X-Tollgate-Human` / failover headers)

---

## See also

- [HOW_IT_WORKS.md](HOW_IT_WORKS.md)  
- [QUICKSTART.md](QUICKSTART.md)  
- [STABILITY.md](STABILITY.md) · [GAP_ANALYSIS_14.md](GAP_ANALYSIS_14.md)  
