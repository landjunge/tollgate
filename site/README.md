# Tollgate product website

Static marketing + docs hub for GitHub Pages.

| File | Role |
|------|------|
| `index.html` | English landing |
| `de.html` | German landing |
| `docs.html` | Doc index (filterable) |
| `styles.css` / `site.js` | Design + small UX |
| `404.html` | Admission-denied joke page |

**Live:** https://landjunge.github.io/tollgate/

**Local preview:**

```bash
cd site && python3 -m http.server 8080
# open http://127.0.0.1:8080
```

Deploy: push to `main` → workflow `Pages` (`.github/workflows/pages.yml`).  
First time: repo **Settings → Pages → Source: GitHub Actions**.
