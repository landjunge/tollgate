# TollGate-Dokumentation

**Repository:** https://github.com/landjunge/tollgate
**Website:** https://landjunge.github.io/tollgate/ (statische Seiten in `site/`)
**Paketpfad der Anbieterspezifikationen:** `src/tollgate/distill/*.json`

| Dokument | Thema |
|-----|--------|
| **[HILFE.md](HILFE.md)** | **Deutsche Hilfe & Handbuch** |
| **[USER_GUIDE.md](USER_GUIDE.md)** | **Bisheriges englisches Nutzerhandbuch** |
| **[FAQ.md](FAQ.md)** | **Häufige Fragen auf Deutsch und Englisch** |
| [TEN_MINUTE.md](TEN_MINUTE.md) | **Die ersten zehn Minuten ohne Vorkenntnisse** |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Einzelheiten zur Einrichtung |
| [DEMO.md](DEMO.md) | **Vorführung: Agentenschleife und Wiederanlaufnachweis** |
| [MAP.md](MAP.md) | **Codeübersicht: Module, HTTP, CLI und Begriffe** |
| [VISION.md](VISION.md) | Produktfestlegung und mehrere Verbraucher |
| [PRODUCT.md](PRODUCT.md) | Sicherheitskontrolle für KI-Agenten · Protect · Route · Prove |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Sieben Schichten, Schutzschalter und Einordnung |
| [COST_LIMITS.md](COST_LIMITS.md) | Google deaktiviert, Budgets, `/v1/config` |
| [MCP.md](MCP.md) | stdio MCP + HTTP `/v1/*` |
| [N8N.md](N8N.md) | n8n als Verbraucher |
| [KEYS_MODULE.md](KEYS_MODULE.md) | Ältere Modulübersicht; MAP.md bevorzugen |
| [PORTABLE.md](PORTABLE.md) | USB-Stick ohne feste Hostpfade |
| [OPENAI.md](OPENAI.md) | OpenAI-Anbindung über base_url |
| [STABILITY.md](STABILITY.md) | Skalierung, mehrere Worker, Schemaversion und Ablösung |
| [OPERATIONS.md](OPERATIONS.md) | doctor, Bereitstellung und Grenzen automatischer Wartung |

Aktueller Lizenzstand und offene Textfreigabe: [Lizenzhistorie](LICENSING.md).

## Hilfe in der Kommandozeile

```bash
tollgate help
tollgate help protect
tollgate help env
tollgate help config
tollgate help faq
tollgate help troubleshoot
```

## Repository durchsuchen

```bash
tollgate search circuit breaker
tollgate search budget --kind concept
tollgate search --map
```

Für Agenten außerdem: [`llms.txt`](../llms.txt) im Hauptverzeichnis.

## Regeln für gezielte Änderungen

| Tun | Vermeiden |
|----|--------|
| Bei API-Änderungen die Spezifikations-JSON-Datei anpassen | Endpunkte in beliebigen `.py`-Dateien erfinden |
| Für neue MCP-Funktionen `ops[]` ergänzen | Grenzen in mehrere Module kopieren |
| `distilled_at` aktualisieren | Router und Dienst bei jeder Dokumentationsänderung umbauen |

## Anbieter

| Kennung | Spezifikationsdatei |
|----|----------------|
| deepseek | `src/tollgate/distill/deepseek.json` |
| worker | `src/tollgate/distill/worker.json` |
| brave | `src/tollgate/distill/brave.json` |
| elevenlabs | `src/tollgate/distill/elevenlabs.json` |
| openrouter | `src/tollgate/distill/openrouter.json` |
| nvidia | `src/tollgate/distill/nvidia.json` |
| minimax | `src/tollgate/distill/minimax.json` |
| opencode_zen | `src/tollgate/distill/opencode_zen.json` |
| google | `src/tollgate/distill/google.json` (`high_risk`, standardmäßig deaktiviert) |
| telegram | `src/tollgate/distill/telegram.json` |

```python
from tollgate.distill.loader import load_distill, research_view, ops_for

spec = load_distill("brave")
for op in ops_for("brave"):
    print(op["name"], "→", op["maps_to"])
```
| [DESK.md](DESK.md) | Betriebsanleitung für Gnom und n8n |
