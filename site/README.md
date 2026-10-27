# TollGate-Produktwebsite

Statische Produktseite im Stil eines Leitstands für GitHub Pages.

**Veröffentlicht:** https://landjunge.github.io/tollgate/

## Suchmaschinen und Google-Indexierung

| Angabe | Ort |
|------|----------|
| Titel, Beschreibung und Suchbegriffe | `index.html`, `de.html`, `docs.html` |
| robots `index,follow` und große Vorschaubilder | Metadaten im Kopfbereich |
| Kanonische Adresse und Sprachverweise EN/DE | Verweise im Kopfbereich |
| Open Graph + Twitter Card | Metadaten im Kopfbereich · Bild `assets/og.png` (1200×630) |
| JSON-LD `SoftwareApplication` | index |
| JSON-LD `FAQPage` | index + de |
| JSON-LD `WebSite` / `CollectionPage` | index / docs |
| `robots.txt` + `sitemap.xml` (hreflang + images) | Website-Hauptverzeichnis |
| Semantisches HTML | main, section, article, nav |

### Google Search Console

1. Eigenschaft: `https://landjunge.github.io/tollgate/`
2. Sitemap einreichen: `https://landjunge.github.io/tollgate/sitemap.xml`
3. Indexierung für `/` und `/de.html` beantragen

## Lokale Vorschau

```bash
cd site && python3 -m http.server 8080
```

## Veröffentlichung

Ein Push auf `main` löst den vorhandenen Pages-Ablauf aus (`.github/workflows/pages.yml`).

Aktuelle Lizenzangaben folgen dem [Lizenzindex](../docs/LICENSING.md). Historische
Veröffentlichungsbeiträge bleiben unverändert; sie ersetzen nicht den aktuellen
Rechtevorbehalt. Bis zur Freigabe des deutschen Volltextes liegt dieser noch
im englischen Original in der Root-LICENSE vor.
