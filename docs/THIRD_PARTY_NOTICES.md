# Third-party inventory and notice requirements

Static review of source revision `7a6c4429cd3db6c230d8012c4e67bcc981a37ba1`,
2026-10-27. This inventory records declared dependencies and preparation work.
It is not a resolved bill of materials or a complete notice bundle for a
specific distributed build. Proprietary TollGate terms do not replace these
components' licenses.

| Declared component | Role | License metadata checked at the upstream source | Distribution requirement to verify |
|---|---|---|---|
| `fastapi>=0.110` | Runtime | [PyPI](https://pypi.org/pypi/fastapi/json): MIT | Preserve applicable copyright and permission notices, including the disclaimer |
| `uvicorn[standard]>=0.27` | Runtime with optional standard dependencies | [PyPI](https://pypi.org/pypi/uvicorn/json): BSD-3-Clause | Preserve copyright, conditions and disclaimer; observe the non-endorsement condition |
| `pydantic>=2.0` | Runtime | [PyPI](https://pypi.org/pypi/pydantic/json): MIT | Preserve applicable MIT notices; inspect native/transitive components separately |
| `pytest>=8.0` | Development | [PyPI](https://pypi.org/pypi/pytest/json): MIT | Include notices if this component is delivered |
| `httpx>=0.27` | Development | [PyPI](https://pypi.org/pypi/httpx/json): BSD-3-Clause | Include BSD conditions and disclaimer if delivered |
| `setuptools>=68`, `wheel` | Build | [setuptools](https://pypi.org/pypi/setuptools/json), [wheel](https://pypi.org/pypi/wheel/json): MIT | Inspect the actual build tools and any delivered vendored components |
| `n8n-workflow: *` | Connector peer | Version and selected package license are not pinned | Inspect the actual peer package and any n8n runtime supplied with the product |
| `python:3.12-slim` | Container base | Floating image; Python and operating-system components have their own licenses | Record the image digest, OS packages, copyright and notice files of the actual shipped image |
| IBM Plex Mono / Sans via Google Fonts in `site/styles.css` | Externally loaded website fonts | [IBM Plex license](https://github.com/IBM/plex/blob/master/LICENSE.txt): SIL Open Font License 1.1 | If font files are bundled or modified, preserve copyright and OFL text and check reserved font names; no font binaries were identified in this source tree |

These upstream metadata responses describe the projects inspected on the review
date. They do not pin the versions that a future resolver will select or prove
the terms of every older allowed release. No dependencies were installed or
changed for this review. Optional packages of `uvicorn[standard]`, transitive
dependencies and native libraries remain to be inventoried from a release build.

Before distributing an installer, wheel, source archive or container, resolve
and record all actual versions, hashes and license texts. Preserve the notices
shipped by each component and any applicable upstream NOTICE files; add the
resolved copyright statements to the release's notice bundle. Do not replace
them with the TollGate copyright. Existing Python package metadata identifies
this project as proprietary; it does not classify third-party dependencies.

The historical TollGate MIT notice is preserved in the root [LICENSE](../LICENSE)
and in the existing connector's [LICENSE](../n8n-nodes-tollgate/LICENSE).
The container recipe already copies the root LICENSE, so that notice follows
that copy without changing the build recipe. This does not verify that the
complete container's third-party notice obligations have been met.

n8n itself is separate from the MIT connector. Embedding, white-labeling, hosting
or allowing external customers to configure workflows requires review of the
actual n8n version and business model under the applicable n8n terms; the
connector's MIT label does not grant rights to n8n. See [n8n's official licensing
guidance](https://support.n8n.io/article/can-i-use-your-license-for-my-use-case).
External provider services, API agreements, logos and trademarks likewise are
not licensed by this inventory.
The website also references external `netzwerkpunkt.de` styles and favicon
assets. Their availability is not proof that their rights are included in a
sale of this repository; obtain the actual asset files and rights evidence.

## Deutscher Hinweis / German summary

Diese statische Liste ersetzt keine versionsgenaue Stückliste und kein
vollständiges Notice-Paket für einen konkreten Verkaufsbuild. FastAPI,
Pydantic, pytest, setuptools und wheel wurden anhand aktueller Upstream-Metadaten
als MIT-Projekte geprüft, Uvicorn und HTTPX als BSD-3-Clause-Projekte. Das legt
die tatsächlich ausgelieferten Versionen nicht fest. MIT-Hinweise einschließlich
Copyright, Erlaubnistext und Haftungsausschluss sind zu erhalten. Bei BSD sind
Copyright, Bedingungen und Haftungsausschluss zu erhalten; ohne Zustimmung
darf nicht mit einer Befürwortung durch die genannten Rechteinhaber oder
Mitwirkenden geworben werden. Für die extern geladenen IBM-Plex-Schriften gilt
OFL 1.1; eine spätere Mitlieferung erfordert deren eigene Hinweise und die
Prüfung reservierter Schriftnamen.

Die ungebundenen Versionen, optionalen und transitiven Pakete, nativen Teile,
das `n8n-workflow`-Peerpaket und das bewegliche Python-/Betriebssystem-Image
bleiben für den konkreten Build aufzulösen und mit Hashes und Originaltexten zu
dokumentieren. n8n, Dienste, Logos und Marken behalten eigenständige Bedingungen.
Die MIT-Lizenz des Connectors lizenziert n8n nicht mit. Es wurde nichts
installiert oder an Abhängigkeiten geändert. Die historischen TollGate-MIT-Texte
bleiben in den verlinkten LICENSE-Dateien erhalten. Das Container-Rezept
kopiert bereits die Root-LICENSE; dies belegt keine vollständige Erfüllung aller
Container-Notices. Externe `netzwerkpunkt.de`-Styles und Favicon-Assets sind
gesondert mit Dateien und Rechten zu belegen. Eine vollständige Freiheit von
GPL-/AGPL-Pflichten wird mangels festem Build- und Peergraphen nicht bestätigt.
Diese deutsche Erläuterung und die englische Inventarliste sind keine neuen
Lizenzbedingungen oder Sprachvorrangregelung.

No complete GPL/AGPL-free finding is made: the build and peer graphs are not
fixed. Any commercial transfer must distinguish project rights, retained MIT
permissions, third-party licenses and separate service or brand permissions.
