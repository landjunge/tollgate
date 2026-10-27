# Fremdkomponenten und erforderliche Hinweise

Statische Prüfung der Quellfassung `7a6c4429cd3db6c230d8012c4e67bcc981a37ba1`
vom 27.10.2026. Diese Liste dokumentiert deklarierte Abhängigkeiten und
Vorbereitungsbedarf. Sie ersetzt weder eine aufgelöste Stückliste noch ein
vollständiges Paket erforderlicher Hinweise für einen bestimmten ausgelieferten
Build. Der proprietäre TollGate-Vorbehalt ersetzt keine Fremdlizenzen.

| Deklarierte Komponente | Aufgabe | Geprüfte Lizenzmetadaten der Originalquelle | Vor Verteilung zu prüfende Pflicht |
|---|---|---|---|
| `fastapi>=0.110` | Laufzeit | [PyPI](https://pypi.org/pypi/fastapi/json): MIT | Geltende Copyright-, Erlaubnis- und Haftungshinweise erhalten |
| `uvicorn[standard]>=0.27` | Laufzeit mit optionalen Standardabhängigkeiten | [PyPI](https://pypi.org/pypi/uvicorn/json): BSD-3-Clause | Copyright, Bedingungen und Haftungsausschluss erhalten; keine Werbung mit fremder Befürwortung ohne Zustimmung |
| `pydantic>=2.0` | Laufzeit | [PyPI](https://pypi.org/pypi/pydantic/json): MIT | Geltende MIT-Hinweise erhalten; native und transitive Teile gesondert prüfen |
| `pytest>=8.0` | Entwicklung | [PyPI](https://pypi.org/pypi/pytest/json): MIT | Hinweise mitliefern, falls diese Komponente ausgeliefert wird |
| `httpx>=0.27` | Entwicklung | [PyPI](https://pypi.org/pypi/httpx/json): BSD-3-Clause | BSD-Bedingungen und Haftungsausschluss bei Auslieferung mitliefern |
| `setuptools>=68`, `wheel` | Paketerstellung | [setuptools](https://pypi.org/pypi/setuptools/json), [wheel](https://pypi.org/pypi/wheel/json): MIT | Tatsächliche Bauwerkzeuge und etwaige mitgelieferte eingebettete Fremdteile prüfen |
| `n8n-workflow: *` | Vom Connector erwartetes Zusatzpaket | Version und ausgewählte Paketlizenz sind nicht festgeschrieben | Tatsächliches Zusatzpaket und etwaig mitgelieferte n8n-Laufzeit prüfen |
| `python:3.12-slim` | Containergrundlage | Bewegliches Image; Python- und Betriebssystemteile haben eigene Lizenzen | Imagedigest, Betriebssystempakete sowie Copyright- und Lizenzdateien des ausgelieferten Images festhalten |
| IBM Plex Mono / Sans über Google Fonts in `site/styles.css` | Extern geladene Webschriften | [IBM-Originalbedingungen](https://github.com/IBM/plex/blob/master/LICENSE.txt): SIL Open Font License 1.1 | Bei Mitlieferung oder Bearbeitung Copyright- und OFL-Text erhalten und reservierte Schriftnamen prüfen; keine Fontbinärdateien im geprüften Quellbaum gefunden |

Diese Metadaten beschreiben die am Prüftag eingesehenen Originalprojekte.
Sie legen weder die künftig vom Paketauflöser gewählten Versionen fest noch
beweisen sie die Bedingungen jeder älteren zulässigen Fassung. Für diese
Prüfung wurden keine Abhängigkeiten installiert oder geändert. Optionale Teile
von `uvicorn[standard]`, transitive Abhängigkeiten und native Bibliotheken
bleiben anhand eines konkreten Veröffentlichungsbuilds zu erfassen.

Vor Auslieferung eines Installers, Wheels, Quellarchivs oder Containers sind
alle tatsächlichen Versionen, Hashes und Lizenztexte zu erfassen. Die von jeder
Komponente mitgelieferten Hinweise sowie gegebenenfalls erforderliche
NOTICE-Dateien sind zu erhalten. Die aufgelösten Copyrightangaben gehören in
das Hinweispaket der Veröffentlichung; sie dürfen nicht durch das
TollGate-Copyright ersetzt werden. Die Python-Metadaten bezeichnen dieses
Projekt als proprietär, nicht dessen fremde Abhängigkeiten.

Der historische TollGate-MIT-Text bleibt unverändert in der Root-[LICENSE](../LICENSE)
und der [Connector-LICENSE](../n8n-nodes-tollgate/LICENSE) erhalten. Beide
MIT-Originaltexte bleiben Englisch. Das Container-Rezept kopiert bereits die
Root-LICENSE und nimmt damit diesen historischen Hinweis mit, ohne dass der
Build geändert wird. Dies bestätigt keine vollständige Erfüllung sämtlicher
Hinweispflichten für den Container.

n8n selbst ist vom MIT-Connector zu unterscheiden. Einbettung, Betrieb unter
eigener Marke, Hosting und das Konfigurieren von Abläufen durch externe Kunden
erfordern eine Prüfung der konkreten n8n-Version und des Geschäftsmodells
anhand der geltenden n8n-Bedingungen. Die MIT-Angabe des Connectors gewährt
keine Rechte an n8n. Siehe [offizielle n8n-Lizenzhinweise](https://support.n8n.io/article/can-i-use-your-license-for-my-use-case).

Auch externe Anbieterdienste, API-Vereinbarungen, Logos und Marken werden
nicht durch diese Liste lizenziert. Die Website verweist außerdem auf externe
`netzwerkpunkt.de`-Styles und Favicon-Dateien. Ihre Erreichbarkeit belegt nicht,
dass ihre Rechte von einem Verkauf dieses Repositories umfasst wären.
Die tatsächlichen Dateien und Rechtebelege sind gesondert zu beschaffen.

Eine vollständige Freiheit von GPL-/AGPL-Pflichten wird mangels festgeschriebenem
Build- und Zusatzpaketgraphen nicht bestätigt. Bei jeder kommerziellen
Übertragung sind eigene Projektrechte, MIT-Altrechte, Fremdlizenzen sowie
getrennte Dienst- und Markenrechte zu unterscheiden. Diese Dokumentation
schafft keine neuen Lizenzbedingungen oder Sprachvorrangregelungen. Die noch
nicht freigegebene deutsche Root-LICENSE wird durch diese Erläuterungen
nicht ersetzt; bis zur Textfreigabe bleibt der bestehende englische Originaltext
unverändert.
