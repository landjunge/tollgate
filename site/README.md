# Tollgate product website

**Product landing page** — not a classic OSS feature dump.

Story in ~20 seconds: *agent → Tollgate → protect / route / prove*.

| File | Role |
|------|------|
| `index.html` | EN landing (hero + animated demo core) |
| `de.html` | DE landing (same structure) |
| `docs.html` | Doc hub (secondary) |
| `styles.css` / `site.js` | Control Room aesthetic + scene rotation |
| `404.html` | Admission-denied |

## Structure

1. Hero — Protect your AI agents in production  
2. **Live demo** — Protect → Route → Prove auto-rotate  
3. Why — three cards only  
4. Architecture — where Tollgate sits  
5. Control Room mock  
6. Stack + OpenAI drop-in  
7. 5-minute quickstart  
8. Prove highlight  
9. Built for developers (tech list last)

**Live:** https://landjunge.github.io/tollgate/

```bash
cd site && python3 -m http.server 8080
# http://127.0.0.1:8080
```

Deploy: push `main` → workflow Pages. First time: **Settings → Pages → GitHub Actions**.
