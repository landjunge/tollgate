# Lizenzstand und Historie

Geprüft am 27.10.2026 anhand der Repositoryfassung
`7a6c4429cd3db6c230d8012c4e67bcc981a37ba1`.
Diese Seite dokumentiert bestehende Hinweise. Sie ersetzt diese nicht, gewährt
keine zusätzlichen Rechte, widerruft keine historischen Nutzungserlaubnisse
und bestätigt keine Rechteinhaberschaft.

## Gegenwärtiger Stand

| Material | Bestehender Lizenzstand |
|---|---|
| Erstmals unter dem aktuellen Rechtevorbehalt veröffentlichtes Material | [Proprietärer Rechtevorbehalt](../LICENSE); öffentliche Einsehbarkeit ist keine allgemeine Erlaubnis zum Betrieb, zur Bearbeitung, Verbreitung, Unterlizenzierung oder zum Verkauf |
| Historisch MIT-lizenziertes Material, das in späteren Fassungen erhalten bleibt | Bestehende MIT-Rechte bleiben erhalten; der ursprüngliche Copyright-, Erlaubnis- und Haftungstext ist in der [LICENSE](../LICENSE) wiedergegeben |
| Vorhandener Quellcode von `n8n-nodes-tollgate` | Seit Einführung MIT in Paketmetadaten und README; historischer Originaltext unverändert in der [Connector-LICENSE](../n8n-nodes-tollgate/LICENSE) erhalten |
| Fremde Abhängigkeiten, Plattformen und Dienste | Eigene Bedingungen; siehe [Fremdkomponenten und erforderliche Hinweise](THIRD_PARTY_NOTICES.md) |

Der proprietäre Rechtevorbehalt bleibt bestehen. Er hebt bereits eingeräumte
MIT-Rechte nicht auf. Der bestehende n8n-Connector wird weiterhin als MIT
geführt; diese Angabe wird nicht als bloßer Metadatenfehler umgedeutet.
Öffentliche Einsehbarkeit und technische Installationsanleitungen ersetzen keine
erforderliche Nutzungserlaubnis für später hinzugekommenes geschütztes Material.

## Sprache und offene Textfreigabe

Die aktuelle Root-LICENSE liegt weiterhin im englischen Original vor.
Eine neue vollständige deutsche Fassung des eigenen Rechtevorbehalts mit
ausdrücklichem deutschem Sprachvorrang ist als konkreter Freigabeentwurf
vorbereitet. Sie wird erst nach ausdrücklicher Freigabe dieses genauen Textes
übernommen. Die Entscheidung für Deutsch ist getroffen; offen ist die
rechtserhebliche Textfreigabe. Bis dahin ersetzen die deutschen Hinweise und
Zusammenfassungen den bestehenden englischen Lizenztext nicht.

Der frühere Vorschlag eines englischen Sprachvorrangs ist verworfen und wird
nicht umgesetzt. Eine solche neue Vorrangklausel wurde nicht eingeführt.
Der historische MIT-Text und die eigenständige MIT-Lizenz des Connectors bleiben
in ihren ursprünglichen englischen Fassungen unverändert. Auch fremde
Lizenzoriginale werden weder übersetzt noch einer neuen deutschen Vorrangregel
unterstellt. Diese Dokumentationsänderung widerruft keine historischen Rechte
und schafft keine eigenständigen Lizenzbedingungen.

## Nachgewiesene historische Grenze

Der MIT-Roottext wurde mit
[`073e5d3eed6a2a9e5d08e435e4866ec298550378`](https://github.com/landjunge/tollgate/commit/073e5d3eed6a2a9e5d08e435e4866ec298550378)
eingeführt. Der proprietäre Rootvorbehalt wurde mit
[`a0044a4881c356b24595394cd8ec1e33bf2e5fd7`](https://github.com/landjunge/tollgate/commit/a0044a4881c356b24595394cd8ec1e33bf2e5fd7)
am 07.10.2026 um 14:57:03 UTC eingeführt. Dessen unmittelbarer Vorgänger,
[`d07c3ffb7513473a3de1c87bd01e9a1c9ea39c85`](https://github.com/landjunge/tollgate/blob/d07c3ffb7513473a3de1c87bd01e9a1c9ea39c85/LICENSE),
enthält noch den historischen MIT-Text. Der aktuelle Rootvorbehalt erhält
bereits eingeräumte Rechte an historischen Fassungen ausdrücklich. Die
Commitgrenze bedeutet nicht, dass jede Datei in einer späteren Fassung neu
entstanden oder ausschließlich lizenzierbar geworden wäre.

Die Python-Metadaten wechselten mit
[`eca8104d9e997614f6ba6a8e888d7befcdea3caf`](https://github.com/landjunge/tollgate/commit/eca8104d9e997614f6ba6a8e888d7befcdea3caf)
von MIT zu `Proprietary`. Die Versionsnummer blieb `1.0.12`. Sie allein bestimmt
somit keine Lizenzgrenze; maßgebliche Nachweise sind Quellcommit und Artefakthash.

## Nachgewiesene Historie des n8n-Connectors

| Connectorversion | Quellcommit | Bestehende Angaben |
|---|---|---|
| 0.1.0 | `340dfbf39007cbb4e1d16226caeb91b3414778f0`, 11.08.2026 | Paketmetadaten MIT; README MIT; Root MIT |
| 0.2.0 | `23a92cbbbc66e31a140aa5e006458a9e5b6c3c2f`, 11.08.2026 | Paketmetadaten MIT; unveränderte MIT-Angabe in README; Root MIT |
| 0.2.1 | `cb5f06936d0566cb4ee2251f85f7a3f9d36b3b38`, 11.08.2026 | Paketmetadaten MIT; unveränderte MIT-Angabe in README; Root MIT |

Am geprüften Quellstand hat der vollständige Connectorverzeichnisbaum die
Gitkennung `cbe169ea13f319eb175bdf4b36ee70a2a87d0d41`. Sie stimmt mit dem
letzten Vorgänger vor dem Rootwechsel, `d07c3ff...`, überein. Zwischen diesen
beiden Quellständen wurde keine Connectordatei geändert. Der vorhandene
Connector ist damit nachweislich historisches MIT-Material. Seine
MIT-Angabe durch proprietäre Angaben zu ersetzen würde bestehende Rechte verdecken.

Die Connector-LICENSE ist eine unveränderte Kopie des historischen MIT-Textes
einschließlich `Copyright (c) 2026 landjunge`. Sie ergänzt den im eigenständig
packbaren Paket zuvor fehlenden vollständigen Hinweis, verändert aber weder
den aktuellen Rootvorbehalt noch die Lizenz späterer Rootergänzungen.
Künftige Connectoränderungen erfordern vor ihrer Verteilung eine eigene
dokumentierte Lizenzentscheidung.

Die öffentliche npm-Registry lieferte am 27.10.2026 HTTP 404 für das Paket,
für die Versionen 0.1.0, 0.2.0 und 0.2.1 sowie deren übliche Tarball-Adressen.
Deshalb konnte keine tatsächliche npm-Verteilung geprüft werden. Daraus folgt
nicht, dass das Paket nie veröffentlicht, entfernt, lokal gepackt, privat
verteilt oder von GitHub kopiert wurde. Die tatsächlichen früheren Empfänger
und deren Kopien bleiben zu ermitteln.

## Veröffentlichungen und frühere Darstellungen

Die beobachteten Remotetags `v0.3.7`, `v1.0.0`, `v1.0.11`, `v1.0.12` und
`announce-public` verweisen auf Fassungen mit historischer MIT-Rootlizenz.
`v1.0.12` verweist auf `cb5f069...`, `announce-public` auf `ad7d951...`.
Die öffentliche GitHub-Startveröffentlichung erschien am 11.08.2026; die
API-Antwort vom 27.10.2026 enthielt keine angehängten Dateien. Veränderliche
Tags und der heutige Veröffentlichungseintrag beweisen allein nicht die
ursprünglichen Bytes jedes ausgelieferten Artefakts.

Frühere Veröffentlichungsbeiträge, Presse-, Artikel- und Social-Media-Texte
sowie Planungsdokumente können weiterhin das historische MIT-/Open-Source-Modell
beschreiben. Sie bleiben historische Belege und bestimmen keine neuen Rechte
an späterem geschütztem Material. Ihr Fortbestand entzieht früheren Empfängern
keine tatsächlich eingeräumten Rechte. Die aktuelle Root-LICENSE und diese
Komponentenhistorie dokumentieren die heutige Abgrenzung. Historische
Veröffentlichungseinträge wurden nicht umgeschrieben.

Der öffentliche PyPI-Name `tollgate` verweist derzeit auf das andere Repository
`ravi-labs/tollgate`. Dessen Veröffentlichungen sind keine Belege für dieses
Projekt. Distributionsname und mögliche Kennzeichenfragen sind gesondert zu klären.

## Verkauf und Lizenzierung

Ein Verkauf kann nur tatsächlich vorhandene und übertragbare Rechte umfassen.
Git-Autorenangaben, ein Copyright-Hinweis oder Repository-Zugriff belegen keine
vollständige Rechtekette. Verträge mit Mitwirkenden, Beschäftigungsbezug,
frühere Kundenlizenzen, Bearbeitungsrechte, Übertragung und Unterlizenzierung
müssen gesondert geprüft werden. MIT-Altrechte und Fremdlizenzen dürfen nicht
als ausschließliche eigene Rechte angeboten werden.
