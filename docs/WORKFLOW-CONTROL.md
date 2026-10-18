# Auftragskontrolle / Workflow control — local adapter v1

Stand: 18.10.2026 · Auftrag `seven-tools-build-20261018-1833` · TG-C01–04.
Ausgangsquelle `114cdaee1d3fa39aeaf744c67d2ac1352959fa5e` (1.0.12).

## Deutsch

Die eigenständigen Gateway-, Tagesgrenzen-, Freeze-, MCP- und n8n-Wege bleiben
bestehen. `tollgate.workflow_control` ergänzt einen **lokalen, explizit
angeschlossenen Adaptervertrag**. Er kontrolliert keinen beliebigen Agenten,
CLI-Prozess, Browser oder fremden Schlüssel. Ein Abonnement hat dadurch keine
technisch garantierte Dollarobergrenze. Der aktuelle Nachweis ist synthetisch;
ein produktiver KiraBridge-/4AllPass-Anbieterweg ist damit nicht abgenommen.

### Vertrauensgrenze und Identität

`WorkflowScope(project_id, workflow_id)` bezeichnet den Gesamtauftrag.
`AttemptIdentity(scope, task_id, actor_id, consumer_id, attempt_id, request_hash,
parent_task_id='', subtask_id='')` bindet einen einzelnen Versuch. Auftrag,
Versuch und Quell-/Handoff-Revision sind verschiedene Dinge. Revisionsbindung
gehört in den vom aufrufenden Adapter geprüften `request_hash`; keine automatische
Deutung einer Revision als andere Revision. Der Adapter friert alle tatsächlichen
Parameter ein und bildet den Hash vor Reservierung. Eine Hashbindung beweist
weder Identität noch Berechtigung.

Die authentisierte lokale Gegenstelle muss Projekt/Workflow/Akteur und Rechte
vor jedem Aufruf prüfen. Diese Python-Bibliothek ist **kein Remote-Authserver**;
Methoden nicht ungeprüft als Agenten-/HTTP-Werkzeuge exportieren. Es gibt keinen
neuen unauthentisierten Konfigurations-, Erhöhungs- oder Send-Endpunkt.
`configure_budget(scope, actor_id, consumer_id, limit_microusd)` ist ausschließlich
Betreiberkonfiguration. Bestehende Akteur→Consumer-Bindung ist unveränderlich;
Erhöhung benötigt `authorize_increase=True` aus einer echten Betreiberentscheidung.
Ein Agentenpayload darf dieses Argument niemals bestimmen. Consumerkennungen
werden gegen die vorhandene 64-Zeichen-Consumerregel geprüft; kein stilles
Zusammenfallen ungültiger Kennungen zur anonymen Tages-Sparte. Die Grenze kann
verringert werden, ohne frühere Kosten oder Reservierungen zu löschen. Ein
vorher reservierter Versand wird bei inzwischen überschrittenem Limit gesperrt.

### Quote und tatsächlicher Dispatch

`Quote(adapter_id, provider, operation, target_id, max_cost_microusd, price_basis)`
kommt ausschließlich aus der festen Registry des vertrauten Adapters:
`WorkflowControl(registered_quotes={quote.adapter_id: quote})`. Ohne exakten
Registrytreffer wird dauerhaft `UNBOUNDED_COST` vermerkt. Freie Modelltexte,
Clientpreise und grobe Tageskostenschätzungen sind keine harte Quote. Die Registry
allein beweist noch keine Anbieterpreisgrenze: der tatsächliche Adapter muss
Ziel, Menge, Preis, Zeit und Transport technisch begrenzen. Keine freien URLs,
Redirects, automatische Transport-Retries oder Schlüssel-/Topfwechsel.

Die öffentliche Python-Fachfolge:

1. `reserve(identity, quote)` reserviert atomar das Maximum in der bestehenden
   `User/`-Datenablage. Bestehendes `gateway.admit` gilt zusätzlich, insbesondere
   Freeze, Scopes/Provider- und Verbrauchsgrenzen. Eine zusätzliche injizierte
   Admission-Funktion ist nur für isolierte Tests vorgesehen.
2. `dispatch(identity, send)` prüft Registry, aktuelle Admission, Vorbehalte und
   Auftragssperre nochmals unter dem Workflow-Lock. Vor `send()` wird
   `DISPATCH_ATTEMPTED` dauerhaft und mit `fsync` geschrieben. Erst dann darf
   dieser eine synchrone, begrenzte Callback die Wirkung auslösen. `send` darf
   keine nachgelagerte Queue, Scheduler/Future oder späteren Send-Token erzeugen.
   Callback-Ziel und eingefrorene Parameter müssen genau zur Quote/Hashbindung
   gehören. Geheimnisse bleiben gegebenenfalls allein im geschützten Executor;
   TollGate benötigt sie nicht. Rückgabewerte und Ausnahmeinhalte des Callbacks
   werden weder gespeichert noch an den Aufrufer ausgegeben.
3. Wiederholte `reserve/dispatch/get_attempt` desselben Versuchs lesen vorhandenen
   Zustand; geänderte Identität, Parameterhash oder Quote erzeugen einen Konflikt.
   Ein Crash nach Versandmarke bleibt `OUTCOME_UNKNOWN`, auch wenn tatsächlich
   noch kein Byte gesendet wurde. Keine automatische Wiederholung.
4. `settle(identity, actual_microusd, settlement_id, evidence_ref)` benötigt eine
   **abschließende belastbare Abrechnung** vom vertrauenswürdigen Adapter.
   HTTP 200, Modelltext und Durchgangsende genügen nicht. Gleiche Abrechnung wird
   einmal verbucht; geänderte Abrechnung ist ein Konflikt. Betrag über Quote wird
   vollständig als Incident gebucht; betroffene KI-Sparte bleibt gesperrt.

Geld ist strikt ganzzahlig: `USD_MICRO`, 1 USD = 1 000 000 Einheiten; keine Floats,
Strings, bools oder Währungsumrechnung. Einzelbeträge/Limit höchstens 10^15.
Je Akteur/KI separater Topf über den **gesamten Auftrag**, einschließlich explizit
zugeordneter Unteraufträge und Wiederholungen. Kein Tages-, Geräte- oder
Neustartreset. `spent`, `reserved`, `available` sind getrennt. Unbekannte Kosten
halten das ganze Maximum ohne TTL; nur bestätigte Nichtversand-Abbrüche vor
Dispatch lösen es oder belegte finale Abrechnung gleicht es ab. Tagesverbrauch
bleibt separat und kann geschätzt sein; er wird nicht als Anbieterrechnung
umetikettiert. Der direkte Dispatch verwendet zusätzlich die vorhandene atomare
`try_reserve_day_call`-Reservierung und meldet `day_call_reserved`. Angeschlossene
Adapter müssen bestehende Token-/Kosten-Tagesabrechnung weiter bedienen und
bei bereits reserviertem Aufruf `record_usage(..., count_call=False)` verwenden;
keine doppelte Aufrufzählung oder zweite Gateway-Aufrufreservierung.
Gesamtauftragsabrechnung schreibt keinen doppelten Tages-Usage-Eintrag. Keine parallele Aufgabenwarteschlange.

### Stopp und Wiederanlauf

`stop(scope, stop_id)` schreibt eine dauerhafte Barriere und storniert noch nicht
versandte Reservierungen. Erst `EFFECTIVE` / `further_dispatch_blocked=true`
bestätigt die Sperre. Der gleiche Workflow-Lock ordnet Wirkung und Sperre; andere
Workflows besitzen unabhängige Locks. Kein Warten in der normalen Taskqueue.

Solange ein begrenzter Send den Lock hält, liefert Stopp nach begrenztem
Lock-Warten `PENDING`; dieser Rückgabewert ist **keine bestätigte dauerhafte
Sperre**. Der Kontrolladapter muss dieselbe Stopp-ID weiter abgleichen, nicht
neue Wirkungsversuche erzeugen. Kein garantierter Latenzwert für fremde Dienste.
Die Python-Bibliothek kann einen beliebigen Callback nicht sicher beenden;
sein transportseitiger Timeout ist Adapterpflicht. Nach Barriere kein neuer
Versand. Bereits transportierte Wirkung wird nicht rückgängig behauptet.
`abort_confirmed=false` bleibt ehrlich: ein späterer Bridge-/Gnom-/Browseradapter
muss Prozess-/Kontextabbruch und verbleibende Wirkung gesondert belegen.

Journal liegt unter `User/workflow_control/<scope-hash>.json` (0600), verwendet
bestehendes `FileLock`, atomaren Austausch, dauerhafte Sequenz und bestehendes
`audit.jsonl`. Kein zweites Protokoll/Queue. Fehlerhafte, doppelte JSON-Felder
oder übergroße Journale sperren statt Reset. Grenzen: 10 000 Versuche / 8 MB je
Auftrag; Kapazitätsende benötigt bewusste Archivierung mit Tombstone-Erhalt,
kein automatisches Löschen. Stopps, Denials, abgeschlossene und unbekannte
Versuche werden nicht per TTL gelöscht. Betreiber darf Journal/Backup nicht
zurücksetzen, um Kosten erneut freizugeben. Externer manipulationssicherer
Checkpoint, Geräteaufnahme, DPoP, Firmenidentität und Full-B0 sind **nicht**
implementiert; kein Schutz gegen den lokalen Administrator behauptet.

Statusausgaben enthalten Zustand, Grundcode, Zeitpunkt/Sequenz, Geldeinheit,
Kostenart und Vorbehalte. Private Inhaltshashes, Providerantworten, Tokens und
Ausnahmetexte werden nicht ins Audit/Graph exportiert. Projekt-/Workflow-ID ist
nur dem bereits autorisierten lokalen Aufrufer zugänglich. Für einen zukünftigen
HTTP-Anschluss müssen Rechte und Fremdprojekt-Sichtgrenzen zusätzlich am
Endpunkt geprüft werden. Agent Authority darf diese Belege beobachten, keine
Budgets oder Rechte freigeben. Return/geliefert ist keine Nutzerabnahme.

### Kleine tatsächliche Probe

Nach normaler Entwicklerinstallation (`python -m pip install -e '.[dev]'`):

```sh
python examples/workflow_control_dummy.py
pytest -q tests/test_workflow_control.py
```

Der Demo-Lauf verwendet eine temporäre Konfiguration, einen Dummy-Dispatch und
einen ausdrücklich synthetischen Kostenbeleg; kein Schlüssel, Netzwerk oder
Nutzerdatensatz. Er beweist keinen produktiven Firmen-/Anbieterbetrieb.

## English

`workflow_control` is an explicit **trusted local adapter boundary**, not an
arbitrary CLI/browser sandbox or a remote authorization server. Existing gateway,
MCP/n8n, admission/freeze and daily usage remain independent and compatible.
Only synthetic bounded adapters have been verified. Subscription CLI usage has
no hard dollar guarantee from this module.

Use `WorkflowScope(project_id, workflow_id)` for the full workflow and
`AttemptIdentity(scope, task_id, actor_id, consumer_id, attempt_id, request_hash,
parent_task_id='', subtask_id='')` for each frozen attempt. Handoff/source
revisions remain separate and belong in the adapter-verified content binding.
Authentication/ownership is the caller's responsibility; a digest is not identity.

Trusted operators alone configure budgets. Model/agent input must never create
or increase a budget, change a consumer lane, select a key, set trusted prices or
supply an arbitrary send callback. The constructor's fixed registered quotes bind
adapter/provider/action/target, enforced upper cost and price basis. Missing or
changed registration fails closed. A registered quote is only as real as its
adapter's enforceable amount/price/transport limits; estimates are insufficient.

`reserve` atomically holds the upper bound; `dispatch` rechecks current admission,
registry, budget and stop state under the same workflow file lock, persists the
send marker and only then invokes the bounded synchronous send. No portable allow
token, deferred scheduler, implicit retry, redirect or alternate budget/key.
Callback return values and exceptions are not exported or persisted. Repeating an
attempt reads its state rather than sending again. Changed content is a conflict.
Crash/timeout/unknown billing retain the reservation; no TTL, day or restart reset.
All amounts are integer USD microdollars, never floats, bools or currency conversion.
Separate AI lanes cover the entire workflow including assigned substeps.

`settle` requires final trustworthy billing evidence and is idempotent. HTTP 200
is not billing evidence. An over-quote bill is recorded in full, freezes the
affected lane and needs explicit incident handling. Current daily usage can be
estimated and remains separate; the direct dispatch additionally uses the existing atomic daily-call reservation.
Adapters must still account token/cost usage and use `count_call=False` when
`day_call_reserved` is true, without running a second gateway-call reservation.

`stop` confirms `EFFECTIVE` only after its durable dispatch barrier. During an
already active bounded send it can return `PENDING`, which must be reconciled
using the same stop ID. Unrelated workflows do not share its lock. No promise of
arbitrary callback cancellation or fixed remote-service stop latency. A confirmed
block is not a confirmed process abort; already sent effects may remain unknown.

Storage reuses `User/`, file locks and the operational audit, with private atomic
0600 snapshots, sequence/timestamp, 10 000 attempts / 8 MB per workflow. Corruption
fails closed; terminal tombstones and unknown obligations are not auto-pruned.
No new task queue, anti-rollback authority, corporate identity/DPoP protocol or
administrator-proof guarantee. Read the scoped status through a trusted caller;
future HTTP endpoints still require explicit project authorization. Observer
reports never authorize budget/rights or claim user acceptance.

Run the disposable demo/tests above. Full KiraBridge/4AllPass/Gnom adapters,
production provider price evidence and process-cancellation acceptance are still
separate gates. Existing B0/Goldenrules from ThreadDesk PRs #64/#65 informed this
bounded implementation; their larger corporate protocol is not claimed complete.
