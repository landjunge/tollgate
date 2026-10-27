<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/design/icons/dark/TollGate-dark-128.png">
  <img src="assets/design/icons/light/TollGate-light-128.png" alt="TollGate" width="96" height="96">
</picture>
<p align="center"><img src="brand/wordmark.svg" width="520" alt="TollGate"></p>

<p align="center"><strong>Eine Sicherheitsschranke für KI-Agenten.</strong></p>

TollGate prüft eine Handlung, bevor ein Agent sie ausführt. Es kann Schleifen stoppen, Budgets begrenzen und Ausfälle sichtbar machen.

### 👤 [Für Nutzer – TollGate ausprobieren](#für-nutzer)

### 🛠️ [Für Entwickler – Code und technische Dokumentation](#für-entwickler)

---

## Aktueller Funktionsstand

TollGate prüft angeschlossene Modell- und Werkzeugaufrufe vor der Ausführung. Das Gateway bietet Verbrauchsgrenzen, Schleifenschutz, Scopes, Freeze und kontrollierte Weiterleitung. Der lokale Auftragskontrollkern ergänzt dauerhafte Reservierungen und Stopps für ausdrücklich angeschlossene Adapter. Freeze blockiert neue Aufrufe; es beendet keine beliebigen Prozesse und macht bereits ausgelöste Wirkungen nicht rückgängig. Kostenschätzungen sind keine Anbieterabrechnung.

Python 3.11+; Paketstand: 1.0.12. [Schnellstart](docs/QUICKSTART.md) · [Auftragskontrolle und Grenzen](docs/WORKFLOW-CONTROL.md).

## Für Nutzer

### Einfach erklärt

Ein KI-Agent kann Werkzeuge benutzen, Internetdienste aufrufen und dabei Kosten verursachen. Wenn etwas schiefläuft, kann er denselben Aufruf immer wieder ausführen.

TollGate sitzt davor. Es beantwortet eine Frage:

> **Darf ich handeln?**

### Was du davon hast

- Endlosschleifen werden gestoppt.
- Kosten können begrenzt werden.
- Zugriffe erhalten klare Regeln.
- Bei einem ausgefallenen Anbieter kann kontrolliert gewechselt werden.
- Entscheidungen werden für eine spätere Prüfung festgehalten.

### In drei Schritten

1. **Installieren** – TollGate lokal einrichten.
2. **Testen** – eine ungefährliche Agentenschleife ausführen.
3. **Prüfen** – sehen, warum TollGate den Aufruf erlaubt oder blockiert hat.

### Was TollGate nicht ist

TollGate ist kein KI-Modell, kein Agent und kein Passwort-Tresor. Es ersetzt auch nicht die Entscheidung des Menschen. Es ist eine eigene Kontrollschicht vor einer Handlung.

### Heutiger Stand – ehrlich

| Bereich | Aktueller Stand |
|---|---|
| Protect | Budgets, Schleifenstopps, Scopes und Freeze |
| Route | Zustandsabhängige Weiterleitung und Ausweichanbieter |
| Prove | Chaos- und Wiederanlauf-Tests mit Nachweisen |
| Schnittstellen | OpenAI-kompatibel, MCP und n8n |
| Technik | Python und FastAPI |
| Reife | In Entwicklung; vor Produktion selbst prüfen |

### Kontrollumfang

Freeze sperrt neue angeschlossene Aufrufe; es beendet keine beliebigen Prozesse
und macht bereits versandte Wirkung nicht rückgängig. Tagesgrenzen und grobe
USD-Schätzungen sind keine bestätigte Anbieterrechnung. Der lokale
[Auftragskontrollkern](docs/WORKFLOW-CONTROL.md) reserviert ganzzahlige
USD-Microbeträge je KI/Gesamtauftrag dauerhaft und koppelt Stopps an den
**tatsächlichen angeschlossenen Versand**. Neustart, Tageswechsel und Zeitüberschreitung
geben unklare Reservierungen nicht frei. Die Abnahme nutzt synthetische Adapter;
KiraBridge/4AllPass-Livebetrieb und beliebige CLI-Kosten sind damit nicht freigegeben.

[Produktseite](https://tollgate.netzwerkpunkt.de/) · [Schnellstart](docs/QUICKSTART.md)

---

## Für Entwickler

TollGate ist eine vorgeschaltete Zugangskontrolle für Werkzeug- und Modellaufrufe. Es entscheidet vor der Anfrage und hält den Grund der Entscheidung fest.

## Wie dieses Projekt entsteht

**Systemgestaltung und Produktarchitektur** — Daniel Filipek (landjunge)

Ich arbeite anders: Ich entwickle Systeme und Produkte mit KI als technischem Partner.

Meine Stärke liegt darin, Probleme zu erkennen, Systeme in eigenständige Werkzeuge zu zerlegen und klare Grenzen und Schnittstellen zu definieren. Produktvision, Prioritäten und Architekturentscheidungen kommen von mir. KI ist der technische Partner für Implementierung, Tests und Dokumentation.

Ich bin kein klassischer Softwareentwickler und kein Security-Spezialist. Die technische Umsetzung entsteht gemeinsam mit KI und muss – besonders bei sicherheitskritischen Projekten – überprüfbar sein.

Was ich einbringe: Idee, Systemdenken, Anforderungen, gewünschtes Verhalten, klare Grenzen.
Was überprüfbar sein muss: der Code, die Spezifikationen, die Tests. Prüfungen sind willkommen.

Der Quelltext ist öffentlich einsehbar. Für neu unter dem Rechtevorbehalt veröffentlichtes Material gilt die [LICENSE](LICENSE); bestehende MIT-Altrechte bleiben erhalten. Kritik, Tests und Beiträge sind willkommen.

TollGate beantwortet **„Darf ich handeln?“** — ein eigenes Produkt, kein Plugin der anderen.

```text
AI Agent
   │
   ├── tool call #1
   ├── tool call #2
   ├── tool call #3
   ├── tool call #4
   └── tool call #5

TollGate

🛑 TOOL LOOP LIMIT EXCEEDED

Agent blocked.
Budget remaining: $1.72
Evidence recorded.
```

---

## In zehn Minuten ausprobieren

**Vorgesehener Weg: direkt mit Python.** Die Protect-Demo benötigt keine Anbieterschlüssel.

```bash
git clone https://github.com/landjunge/tollgate.git && cd tollgate
python3 -m venv .venv && .venv/bin/pip install -e .
./scripts/ten-minute.sh
# 60-second Protect story (optional, server on :8787):
./scripts/demo-agent-safety.sh
```

**USB-Stick und tragbare Installation** mit Python-Umgebung und Daten auf dem Datenträger:

```bash
./scripts/portable-setup.sh
./scripts/run.sh
# details: docs/PORTABLE.md
```

Das solltest du sehen:

| Schritt | Was passiert |
|------|----------------|
| **Protect** | Werkzeugschleife des Agenten → `🛑 REQUEST BLOCKED` ohne kostenpflichtigen Aufruf |
| **Prove** | Simulation eines Ausfalls und Anbieterwechsels → überstanden oder klarer nächster Schritt |
| **Ergebnis** | Nachweisübersicht mit `tollgate certificate` und [Leitstand](http://127.0.0.1:8787/dashboard) |

**Hier beginnen:**
[Schnellstart](docs/QUICKSTART.md) · [Tragbare Installation und USB](docs/PORTABLE.md) · [Funktionsweise](docs/HOW_IT_WORKS.md) · [Produktionscheckliste](docs/PRODUCTION_CHECKLIST.md)

**Weitere Hilfe:** [Sicherheit](docs/SECURITY.md) · [OpenAI-Anbindung](docs/OPENAI.md) · [Handbuch](docs/HILFE.md) · [Häufige Fragen](docs/FAQ.md) · `tollgate help` · `tollgate doctor`

Ist dieser Weg unklar, muss zuerst der Einstieg verbessert werden, bevor weitere Funktionen hinzukommen.

---

## Für wen es gedacht ist

| Zielgruppe | Aufgabe |
|--|--|
| Teams, die Agenten produktiv betreiben | Kosten, Schleifen, Ausfälle, Prüfprotokoll und Sperre |
| Agenten-Frameworks wie LangGraph oder CrewAI | Kontrolle vor Werkzeugen und Sprachmodellen |
| n8n und Automatisierung | Agentenschleifen eines Ablaufs vor dem Aufruf stoppen |

LiteLLM verbindet Modelle. Helicone zeigt den Verkehr. **TollGate hält die Handlungen der Agenten unter Kontrolle.**

---

## Das Produkt im Überblick

| Säule | Aufgabe |
|--------|-----|
| **Protect** | Budgets, harte Stopps für Werkzeugschleifen, Berechtigungsbereiche, Sperre und Prüfprotokoll |
| **Route** | Zustandsabhängiger Anbieterwechsel und Schutzschalter |
| **Prove** | Chaos- und Wiederanlauftests, Belastbarkeitsbewertung und Nachweisübersicht |

Weitere Details: [Produktbeschreibung](docs/PRODUCT.md) · [Architektur](docs/ARCHITECTURE.md)

---

## Alltägliche Befehle

```bash
tollgate status
tollgate certificate --application "Customer Support Agent"
tollgate consumer-budget support-agent --max-usd-day 2 --max-tool-calls 20
tollgate chaos test opencode_zen --requests 10
tollgate freeze --reason "panic"    # blocks new controlled calls; not process termination
tollgate report                     # day brief
```

Agenten oder das OpenAI-SDK anbinden:

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=support-agent   # open mode label, or id:secret
```

## Sprache der Anwendung

Die Anwendung unterstützt Englisch und Deutsch. Englisch bleibt der technische
Standardwert, damit bestehende Skripte, die CLI-Ausgaben auswerten, weiter funktionieren.
Die deutsche Dokumentation ändert dieses Programmverhalten nicht.

| Auswahl | Beispiel |
|---|---|
| Einmalig | `tollgate --lang de help` |
| Dauerhaft | `export TOLLGATE_LANG=de` |
| Automatisch | aus `LC_ALL`, `LC_MESSAGES` oder `LANG` |

`LANG=C` und `LANG=POSIX` bedeuten „keine Präferenz“ und werden übersprungen.
So wird für eine Servershell keine unbeabsichtigte Sprache gewählt.

Von `argparse` selbst erzeugte Abschnittsnamen wie `usage:` und `options:`
stammen aus Python und bleiben Englisch.

Der Leitstand unter `/dashboard` folgt derselben Auswahl: `?lang=de` wählt eine
Sprache, die ein Jahr lang in einem Cookie gespeichert wird. Andernfalls entscheidet
die Browsersprache. Der Schalter sitzt im Kopfbereich und im Einrichtungsassistenten
und ist damit auch beim ersten Besuch erreichbar.

### Klartext oder Fachsprache

Unabhängig von Deutsch oder Englisch gibt es zwei Sprachebenen. **Klartext ist
der Standard; Fachsprache wird ausdrücklich eingeschaltet.** Wer die Begriffe
kennt, kann sie auswählen; alle anderen erhalten verständliche Formulierungen.

| Auswahl | Beispiel |
|---|---|
| Einmalig | `tollgate --mode expert control` |
| Dauerhaft | `export TOLLGATE_MODE=expert` |
| Leitstand | Schalter neben DE/EN; für ein Jahr im Cookie gespeichert |

| Klartext | Fachsprache |
|---|---|
| Leitstand · Nachweis · Protokoll · Anbieter | Control Room · Prove · Audit · Provider |
| TollGate starten, damit Agenten es erreichen können | HTTP-Server mit uvicorn starten |
| Antwortzeit · Sicherheitsschalter · Zustand | Latenz · Circuit · Health |

Die Sprachebene wird nicht aus Browser oder Umgebung abgeleitet. Klartext gilt,
bis jemand ausdrücklich anders entscheidet. Beide Schalter erhalten die jeweils
andere Auswahl in ihren Verweisen; der Wechsel zu Englisch setzt die Sprachebene
also nicht zurück.

Für die zwölf Handbuchthemen hinter `tollgate help <topic>` gibt es bislang keine
Fachsprachfassungen. Der Schalter ist über `<topic>#expert` vorbereitet; ohne
zweite Fassung bleibt der Klartext bestehen.

Noch nicht übersetzt sind Texte aus der API, etwa Überschrift und Empfehlungen
von `/v1/control`. Dafür müsste die API Kennungen statt englischer Sätze liefern.
Diese Änderung des JSON-Vertrags wird gesondert behandelt.

---

## Gemeinsame Regeln der NetzwerkPunkt-Werkzeuge

TollGate, ThreadDesk und 4AllPass teilen ihre Gestaltungs- und Sprachregeln.
Neue Werkzeuge übernehmen dieselben nachprüfbaren Vorgaben. **4AllPass ist die Referenz.**

**Farben**

| Variable | Wert | Zweck |
|---|---|---|
| `--bg` | `#121316` | Grundfläche |
| `--bg-panel` | `#1a1b1f` | Fläche |
| `--bg-card` | `#1e1f24` | Karte |
| `--fg` | `#e2e4e9` | Text |
| `--fg-muted` | `#8b909a` | nachrangiger Text |
| `--border` | `#2e3138` | dekorative Trennung zwischen Flächen |
| `--border-strong` | `#5f646f` | Kante von Bedienelementen |
| `--accent` | `#8f98a8` | Hervorhebung |
| `--ok` / `--warn` / `--err` | `#3d9b6a` / `#c9a227` / `#dc7070` | Zustände |

In TollGate heißen dieselben Variablen `--line`, `--line2`, `--muted`, `--acc`
und `--bad`; die Werte sind gleich, die Namen älter.

**Form und Größe**

- Überall `border-radius: 0`. Runde Formen nur mit Bedeutung, etwa Kartensymbole,
  Fortschrittsring und Statuspunkt, und mit Begründung im Code.
- Genau vier Schriftgrößen: **13 / 16 / 20 / 25 px**. 16 px als Grundgröße für
  Fließtext im Web; die Stufen folgen dem Verhältnis 1,25, einer großen Terz.
  Andere Größenvariablen werden entfernt und nicht nur vermieden.
- Abstände auf einem 8-px-Raster: 4 / 8 / 12 / 16 / 24 / 32.
- **Genau zwei Größen für Bedienelemente:** `--control: 40px` für den Normalfall
  mit Schaltfläche, Eingabe und Auswahl; `--control-sm: 32px` für dichte Zeilen
  und Reiter. Beide liegen im 8-px-Raster; die Elemente haben dieselbe Höhe.
- Unter `@media (pointer: coarse)` werden alle Ziele **44 px** groß
  (`--control-touch`). Das ist dieselbe Oberfläche für ein anderes Eingabegerät,
  keine dritte reguläre Größe. Die Vorgabe stammt aus Apple- und Material-Regeln.
  Entscheidend ist die Zeigerart, nicht die Fensterbreite. WCAG 2.2, 2.5.8 nennt
  24 px als Minimum; alle drei Werte liegen darüber.
- Kontrast: **4,5:1** für Text und **3:1** für andere bedeutungstragende Elemente
  nach WCAG 2.2, 1.4.3 und 1.4.11.
- Auswahlfelder setzen `appearance: none` und zeichnen einen eigenen Pfeil.
  Sonst zeichnet das Betriebssystem das Menü, unter Windows mit 3D-Effekt.
- Die Anwendung verwendet die Systemschrift und lädt dafür keine externe Schrift.

**Sprache**

- Jedes Werkzeug unterstützt von Beginn an Englisch und Deutsch. Nachrüstung ist
  aufwendig. Sichtbare Texte gehören in einen Katalog statt in die Vorlage.
- Immer nur eine Sprache zugleich, keine parallelen Sprachfassungen nebeneinander.
- Auflösung: `?lang=` → Cookie → `Accept-Language` → Standardwert.
- Dazu zwei Sprachebenen: **Klartext als Standard, Fachsprache nach Auswahl**.
  Eine Fachsprachfassung hängt mit `#expert` am selben Schlüssel. Ein Punkt würde
  `register.expert` zur Fachsprachfassung von `register` machen.
  Ohne Fachsprachfassung bleibt der Klartext erhalten.
- Jede Beschriftung sagt, was geschieht; jedes Feld erklärt seinen Zweck.
  Abkürzungen werden ausgeschrieben. Fehlermeldungen nennen den nächsten Schritt.
- Eigennamen bleiben unverändert: TollGate, ThreadDesk, 4AllPass, Gnom-Hub-V1,
  Grok, Codex und MCP.

**Technischer Hinweis:** `argparse` erzeugt Hilfetexte beim Erstellen des Parsers,
nicht erst bei der Auswertung. `--lang` und `--mode` müssen deshalb vorher aus
`argv` gelesen werden; sonst erscheint `tollgate --mode expert --help` wieder
im Klartext.

---

## Vergleich mit Gateways

| Aufgabe | TollGate | LiteLLM | Helicone |
|--|--------------|---------|----------|
| Kernaufgabe | Agentensicherheit und Wiederanlaufnachweis | Proxy für mehrere Modellanbieter | Beobachtbarkeit |
| Harte Sperre vor dem Aufruf | Vorhanden | Optional | Überwiegend nachträglich |
| Chaos- und Wiederanlaufprüfung | Bestandteil des Produkts | Selbst zu ergänzen | Nicht angegeben |

---

## Dokumentationsverzeichnis

| Dokument | Zweck |
|-----|------|
| [HILFE.md](docs/HILFE.md) | Deutsches Handbuch |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Bisheriges englisches Handbuch |
| [FAQ.md](docs/FAQ.md) | Häufige Fragen |
| [TEN_MINUTE.md](docs/TEN_MINUTE.md) | Die ersten zehn Minuten |
| [DEMO.md](docs/DEMO.md) | Vorführung und Bildschirmpräsentation |
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | Einzelheiten zur Einrichtung |
| [MAP.md](docs/MAP.md) · `tollgate search` | Code finden |
| [N8N.md](docs/N8N.md) · [OPENAI.md](docs/OPENAI.md) | Anbindungen |
| [CHANGELOG.md](CHANGELOG.md) | Veröffentlichungen ab v1.0.0 |
| [LICENSING.md](docs/LICENSING.md) | Lizenzstand, Altrechte und offene Textfreigabe |

**Lizenz:** [Proprietärer Rechtevorbehalt](LICENSE). Die geltende Root-LICENSE liegt bis zur ausdrücklichen Freigabe des neuen deutschen Volltextes weiterhin im englischen Original vor. Die deutschen Hinweise sind Erläuterungen und ersetzen diesen Text nicht. Bestehende MIT-Altrechte einschließlich der MIT-Rechte am vorhandenen [n8n-Connector](n8n-nodes-tollgate/LICENSE) bleiben erhalten. Fremdkomponenten behalten ihre eigenen Lizenzen. [Lizenzhistorie und Fremdrechte](docs/LICENSING.md).

**Python:** ≥ 3.11 · **Repository:** [landjunge/tollgate](https://github.com/landjunge/tollgate)

### Auftragseigener CLI-Stopp

Optionale vertrauenswürdige Prozessadapter können die dauerhafte Auftragssperre
mitnutzen. CLI-Kosten bleiben unbekannt; es wird weder eine harte Dollargrenze
noch eine erfundene Nullkostenschätzung zugesagt. [Technische Vereinbarung](docs/WORKFLOW-PROCESS-STOP.md).
