# n8n-nodes-tollgate

Erweiterung für **[TollGate](https://github.com/landjunge/tollgate)** in n8n: lokale Zugangskontrolle für API-Aufrufe mehrerer Verbraucher.

n8n speichert keine DeepSeek-, Brave- oder Google-Schlüssel. Verwendet wird nur eine **Verbraucherkennung** im offenen Modus oder `id:secret`.

## Installation

### Lokale und eigene Erweiterungen

```bash
# from tollgate repo
cd n8n-nodes-tollgate
npm pack   # optional

# link into n8n custom folder
mkdir -p ~/.n8n/custom
cd ~/.n8n/custom
npm init -y
npm install /path/to/tollgate/n8n-nodes-tollgate
# restart n8n
```

Umgebungsvariable zum Laden eigener n8n-Erweiterungen:

```bash
export N8N_CUSTOM_EXTENSIONS=~/.n8n/custom
# or install into n8n's node_modules as community node when published
```

### n8n im Container

Das Paket in das Erweiterungsverzeichnis des Containers einbinden oder dort mit
npm installieren. Als Basisadresse verwenden:

`http://host.docker.internal:8787`

## Zugangsdaten

| Feld in n8n | Beispiel |
|-------|---------|
| `Base URL` | `http://127.0.0.1:8787` |
| `Consumer Key` | `n8n` im offenen Modus oder `n8n:<secret>` |

```bash
tollgate consumer-add n8n
tollgate consumer-budget n8n --max-usd-day 0.5 --max-calls-day 200
```

## Vorgänge

| Vorgang in n8n | Endpunkt |
|----|----------|
| `Chat` | `POST /v1/chat/completions`; das Feld `text` erleichtert die Weiterverarbeitung |
| `Route` | `POST /v1/route` |
| `Budget` | `GET /v1/budget` |
| `Invoke` | `POST /v1/invoke` |
| `Search` | Aufruf von `brave` / `search` |
| `Health` | `GET /v1/health` |

## Nutzung ohne diese Erweiterung

Die HTTP-Abläufe aus `../configs/` importieren:

- `n8n-openai-chat.workflow.json`
- `n8n-budget-gate.workflow.json`
- `n8n-search.workflow.json`
- `n8n-route-invoke.workflow.json`

Weitere Hinweise: [n8n-Anbindung](../docs/N8N.md).

## Lizenz

MIT; der unveränderte historische Originaltext steht in der [LICENSE](LICENSE).
Er bleibt Englisch und wird nicht einer neuen Sprachvorrangregel unterstellt.

Der Connectorquellcode der Repositoryfassung `7a6c4429cd3db6c230d8012c4e67bcc981a37ba1`
ist gegenüber der letzten Fassung vor dem Wechsel des Rootrechtevorbehalts
unverändert. Seine bestehenden MIT-Rechte bleiben erhalten; der Rootvorbehalt
widerruft sie nicht. Die aktuelle Root-LICENSE liegt bis zur Freigabe ihres
neuen deutschen Volltextes weiterhin im englischen Original vor. Diese
deutschen Erläuterungen ersetzen weder die MIT-Lizenz noch den Roottext.
Siehe [Komponenten- und Lizenzhistorie](https://github.com/landjunge/tollgate/blob/main/docs/LICENSING.md).
n8n selbst unterliegt eigenen Bedingungen.
