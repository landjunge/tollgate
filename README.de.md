[English](README.md) · **Deutsch**

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/design/icons/dark/TollGate-dark-256.png">
    <img src="assets/design/icons/light/TollGate-light-256.png" alt="TollGate" width="256" height="256">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/landjunge/threaddesk/blob/docs/product-family-readme-20261031/README.de.md" title="ThreadDesk"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/ThreadDesk-dark-128.png">
    <img src="assets/readme/ThreadDesk-light-128.png" alt="ThreadDesk" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/KiraBridge/blob/docs/product-family-readme-20261031/README.de.md" title="KiraBridge"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/KiraBridge-dark-128.png">
    <img src="assets/readme/KiraBridge-light-128.png" alt="KiraBridge" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/4AllPass/blob/docs/product-family-readme-20261031/README.de.md" title="4AllPass"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/4AllPass-dark-128.png">
    <img src="assets/readme/4AllPass-light-128.png" alt="4AllPass" width="48" height="48">
  </picture></a>
  &nbsp;
  <a href="https://github.com/landjunge/agent-authority-lab/blob/docs/product-family-readme-20261031/README.de.md" title="Agent Authority"><picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme/Agent-Authority-dark-128.png">
    <img src="assets/readme/Agent-Authority-light-128.png" alt="Agent Authority" width="48" height="48">
  </picture></a>
</p>

<h1 align="center">TollGate</h1>

<p align="center"><strong>Eine Sicherheitsschranke für KI-Agenten.</strong></p>

TollGate prüft angeschlossene Modell- und Werkzeugaufrufe, bevor sie ausgeführt werden. Es hilft, wiederholte Aufrufe zu stoppen, Verbrauch zu begrenzen und Entscheidungen nachzuvollziehen.

**Quellstand: 1.0.12 · In Entwicklung · Python 3.11 oder neuer**

[Schnellstart aus dem Quellcode](docs/QUICKSTART.md) · [Quellcode ansehen](https://github.com/landjunge/tollgate/tree/main)

Es gibt keinen veröffentlichten Desktop-Installer. Das [Ankündigungsrelease](https://github.com/landjunge/tollgate/releases/tag/announce-public) enthält keine fertigen Pakete. Die Nutzung benötigt eine Erlaubnis gemäß [Lizenz](LICENSE).

## Was heute vorhanden ist

- **Protect:** Verbrauchsgrenzen, Schleifenschutz, Regeln für erlaubte Zugriffe und eine Sperre für neue Aufrufe.
- **Route:** zustandsabhängige Weiterleitung und Ausweichen auf konfigurierte Anbieter.
- **Prove:** Ausfall- und Wiederanlauf-Simulationen mit Berichten über das geprüfte Setup.
- **Anbindung:** OpenAI-kompatibles Gateway, MCP und n8n; deutsch- und englischsprachige Bedienung.

Der lokale Auftragskontrollkern ergänzt dauerhafte Reservierungen und Stopps für ausdrücklich angeschlossene Adapter. Die Abnahme mit synthetischen Adaptern ist kein fertig eingerichteter KiraBridge-/4AllPass-Produktionsbetrieb. Kostenschätzungen sind keine Anbieterrechnungen und garantieren kein Kostenlimit für beliebige Terminalagenten.

**Grenze:** „Freeze“ blockiert neue angeschlossene Aufrufe. Es beendet keine beliebigen Prozesse und macht bereits ausgelöste Wirkungen nicht rückgängig. [Auftragskontrolle](docs/WORKFLOW-CONTROL.md) · [Prozessstopps](docs/WORKFLOW-PROCESS-STOP.md).

## Loslegen

Mit Nutzungserlaubnis und Python 3.11 oder neuer:

```sh
git clone https://github.com/landjunge/tollgate.git
cd tollgate
python3 -m venv .venv
.venv/bin/pip install -e .
./scripts/ten-minute.sh
```

Die Protect-Demo braucht keine Anbieter-Schlüssel. Prüfe anschließend im lokalen Dashboard, warum ein Aufruf erlaubt oder blockiert wurde. Für echte Modellaufrufe und Weiterleitung brauchst du eigene Anbieterzugänge. [Schnellstart](docs/QUICKSTART.md).

## Geplante Zusammenarbeit

Die fünf Produkte bleiben eigenständig. Geplant ist ein gemeinsamer Ablauf mit **KiraBridge als Kommunikationszentrale**:

| Produkt | Aufgabe im gemeinsamen Ablauf |
| --- | --- |
| [ThreadDesk](https://github.com/landjunge/threaddesk/blob/docs/product-family-readme-20261031/README.de.md) | Bewahrt Projektstand, Wissen und Ergebnisse. |
| [KiraBridge](https://github.com/landjunge/KiraBridge/blob/docs/product-family-readme-20261031/README.de.md) | Vermittelt Aufträge, Rückfragen und Antworten zwischen Chat, lokalen Agenten und Werkzeugen. |
| [4AllPass](https://github.com/landjunge/4AllPass/blob/docs/product-family-readme-20261031/README.de.md) | Verwaltet Zugangsdaten; soll gezielt erlaubte Zugriffe ermöglichen. |
| [TollGate](https://github.com/landjunge/tollgate/blob/docs/product-family-readme-20261031/README.de.md) | Prüft angeschlossene Aufrufe und setzt Verbrauchsgrenzen und Stopps durch. |
| [Agent Authority](https://github.com/landjunge/agent-authority-lab/blob/docs/product-family-readme-20261031/README.de.md) | Zeigt Beobachtungen, Widersprüche und fehlende Belege; erteilt keine Freigaben. |

Einzelne Schnittstellen sind vorhanden. Ein vollständig eingerichteter und geprüfter Ablauf aller fünf Produkte ist noch geplant. Freigaben bleiben beim zuständigen Werkzeug und beim Menschen. KiraBridge und Agent Authority benötigen Zugriff auf ihre privaten Repositorys.

[Hilfe auf Deutsch](docs/HILFE.md) · [Dokumentation](docs/README.md) · [Entwicklerdetails](docs/DEVELOPERS.md) · [Produktseite](https://tollgate.netzwerkpunkt.de/)

## Lizenz und Mitwirkung

[Source-available, alle Rechte vorbehalten](LICENSE). Sichtbarer Quellcode erteilt keine allgemeine Nutzungs- oder Weiterverteilungserlaubnis. Historische MIT-Lizenzrechte bleiben erhalten.

Produktidee und Architektur: **Daniel Filipek (landjunge)**. KI unterstützt Implementierung und Dokumentation. Die dokumentierten Prüfungen ersetzen kein unabhängiges Sicherheitsaudit; nachvollziehbare Reviews sind willkommen.
