# TG-C01–04 / TG-D01 / TG-R01 — bounded delivery

Auftrag `seven-tools-build-20261018-1833`; Bearbeiter Codex-Worker `tollgate_control`.
Basis main `114cdaee1d3fa39aeaf744c67d2ac1352959fa5e`; erster Core-Commit
`025b2476b0cba7d5fe1f86a0a117c3a8f86eac8b`; Folgecommit/PR siehe Git-Historie.
Die fremde lokale Root-Branch, unversionierte AGENTS.md und andere Sitzungen
wurden nicht verändert. Keine Bereitstellung, API-Kosten oder echten Geheimnisse.

| Paket | Tatsächlicher Stand | Grenze |
|---|---|---|
| TG-C01 | Lokaler Pythonvertrag, feste registrierte Quote, bestehende Admission; synthetisch geprüft | Keine Remote-Authentisierung, keine beliebigen CLI-Kinder; KB-C02/FP-Anschluss separat |
| TG-C02 | Dauerhafte Sperre und Send unter gleicher Workflow-Serialisierung; Stopprennen geprüft | PENDING ist keine wirksame Sperre; kein Prozessabbruch/Zurückholen versandter Wirkung |
| TG-C03 | Ganze USD-Microbeträge, atomar je Auftrag/KI, getrennte Töpfe; kein Tages-/Neustartreset; bestehende Tagesaufrufreservierung am tatsächlichen Dispatch | Keine Garantie für unbeschränkte Providerpreise/Abonnement-CLI; produktiver Preisnachweis offen |
| TG-C04 | Private Inhaltsbindung, sekretfreie Zustands-/Kostenprojektion, bestehendes Audit | Observer-/ThreadDesk-Transport noch nicht live abgenommen |
| TG-D01 | Vorhandene lokale np-Basis, vier Schriftrollen, Fokus/reduced-motion, DE/EN-Kontrollumfanghinweis | Chromeprüfung gerenderten HTMLs; keine neue vollständige Live-Dashboardabnahme |
| TG-R01 | README+vollständige DE/EN-Fachbedienung/Beispiel und ehrliche Grenzen | Kein erfundener Installations-/Releaseassetstand |

## Tatsächliche gezielte Prüfungen

- Erster Core: 15 Tests grün.
- Einmalige passende bestehende Prüfgruppe: `test_workflow_control.py`,
  `test_i18n.py`, `test_control_plane.py`, `test_freeze_circuits.py`,
  `test_concurrent_budget.py`: **90 bestanden** (4,20 s), eine bestehende
  Starlette/httpx-Deprecationwarnung. Keine unveränderte Vollsuite lokal wiederholt.
- Danach neu hinzugekommene Fehlerpfade gezielt: Core **20 bestanden** (1,11 s),
  inklusive echter Multiprocess-Reservierung, Tages-Aufrufreservierung,
  Stop-before-send, Stop-during-send PENDING→EFFECTIVE, fremder Workflow,
  Hash-/Settlementkonflikt, Crashmarker, unbekannter Kostenstand, echte
  Admission-Freeze, Betragsvalidierung, Limitabsenkung/Incident, beschädigtes
  Journal und doppelte JSON-Felder. Anschließend nur drei neue Consumer-/Nullkosten-
  Fälle geprüft: **3 bestanden**. Die Summen sind historische Prüfgruppen und
  werden nicht als Anzahl unterschiedlicher Produktfunktionen addiert.
- `examples/workflow_control_dummy.py`: einmalige synthetische Wirkung trotz
  doppeltem Dispatch; synthetischer Abrechnungsbeleg, dauerhafte Stoppsperre und
  danach Denial; Ergebnis `dummy-result.json`. Temporäre Datenablage verworfen.
- Bestehende Dokumentprüfung: Driftcheck grün; Migration 48 grün / 3 vorhandene
  gelbe Planungsdokumente / 0 rot. `git diff --check` grün.
- Sichtprüfung mit eigenem headless Chrome 155: beide Sprachen, vier Schriftrollen,
  sichtbarer Tastaturfokus, reduzierte Bewegung, Hinweis bei 200% Zoom ohne
  Textabschneiden. Netzwerk bewusst gesperrt, gerendertes HTML statt Live-Daten;
  die sichtbare Ladefehlermeldung in Screenshots gehört zu dieser Isolation.
  `browser-design.json`, `dashboard-de.png`, `dashboard-en.png`.
  Erste Probe fand eine CSS-Kaskade, die reduzierte Bewegung überschrieb; korrigiert
  und nur diese Browserprobe erneut ausgeführt. Ein lokaler Aufruf über System-
  Python 3.8 scheiterte beim Import; korrigiert auf die bestehende Projektvenv
  Python 3.11, wie von `requires-python >=3.11` vorgeschrieben.

## Rückweg und nächste Abnahme

Kein laufender Dienst wurde umgestellt. Revert der beiden eigenen Commits nimmt
Code/Designänderung zurück; keine Daten zurücksetzen. Soll später ein realer
Adapter Daten erzeugen, Journale/Reservierungen/Tombstones bei einem Rollback
bewahren und kontrollierten Versand bis zur kompatiblen Wiederaufnahme sperren.
Kein altes Backup als frischen Budgetstand ausgeben.

Nächster überprüfbarer Schritt: FP führt den echten importierten Core am
synthetischen geschützten festen API-Ziel aus; KB-C02 liefert authentisierte
Auftragsbindung. Provider-/Firmenbetrieb benötigt zusätzlich tatsächliche
Adapter-Preisobergrenze, Identitäts-/Grantgrenze, Isolation und gezielte
Stopp-/Abnahmebelege. Implementiert/geprüft ist keine Nutzerabnahme.
