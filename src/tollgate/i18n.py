"""Zweisprachigkeit DE/EN.

Alle NetzwerkPunkt-Werkzeuge sind zweisprachig. Nachruesten ist teuer, also
gehoert jeder sichtbare Text von Anfang an in diesen Katalog und nie direkt
in den Code.

Regeln:
- Schluessel sind stabil, Texte nicht. Ein Schluessel fehlt lieber laut, als
  dass eine Sprache still auf die andere zurueckfaellt.
- Eigennamen und Fachbegriffe werden nicht uebersetzt: Tollgate, Protect,
  Route, Prove, Provider, Consumer, Envelope, Chaos, MCP, JSON.
- Befehle, Flags, Pfade und URLs sind sprachneutral und bleiben gleich.
- Der Test tests/test_i18n.py haelt fest, dass beide Sprachen vollstaendig
  sind und dass kein sichtbarer Text am Katalog vorbeigeht.
"""

from __future__ import annotations

import os

LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "en"

LANGUAGE_NAMES = {"de": "Deutsch", "en": "English"}

# Reihenfolge fuer die Kommandozeile: unsere eigene Variable schlaegt die
# Locale des Systems. "C" und "POSIX" heissen "keine Vorliebe" und werden
# uebersprungen, sonst wuerde jede Server-Shell stumm auf eine Sprache fallen,
# die der Betreiber nie gewaehlt hat.
ENVIRONMENT_VARIABLES = ("TOLLGATE_LANG", "LC_ALL", "LC_MESSAGES", "LANG")
NEUTRAL_LOCALES = {"c", "posix", ""}

CATALOG: dict[str, dict[str, str]] = {
    # --- Programm ---
    "cli.description": {
        "de": "Tollgate — Sicherheitsschicht für AI-Agenten (Protect · Route · Prove). "
              "Probier: tollgate help",
        "en": "Tollgate — safety layer for AI agents (Protect · Route · Prove). "
              "Try: tollgate help",
    },
    "cli.lang": {
        "de": "Ausgabesprache: de oder en",
        "en": "Output language: de or en",
    },
    # --- Befehle ---
    "cmd.help": {
        "de": "Hilfe — Themen und Handbuch-Verweise",
        "en": "User help — topics and handbook links",
    },
    "cmd.help.topic": {
        "de": "start|protect|route|prove|ui|api|ops|troubleshoot|commands|env|config|faq",
        "en": "start|protect|route|prove|ui|api|ops|troubleshoot|commands|env|config|faq",
    },
    "cmd.serve": {
        "de": "HTTP-Server starten (uvicorn)",
        "en": "Run HTTP server (uvicorn)",
    },
    "cmd.mcp": {
        "de": "MCP-Server auf stdin/stdout starten",
        "en": "Run MCP stdio server",
    },
    "cmd.health": {
        "de": "Lokalen Zustand als JSON ausgeben (Pfade + Anmeldeart)",
        "en": "Print local health JSON (paths + auth mode)",
    },
    "cmd.control": {
        "de": "Lagebild (Provider-Zustand + Verbrauch je Consumer + Schlagzeile)",
        "en": "Control plane snapshot (provider health + consumer burn + headline)",
    },
    "cmd.resilience": {
        "de": "AI Resilience Score (0–100) + Warnungen",
        "en": "AI Resilience Score (0–100) + warnings",
    },
    "cmd.chaos": {
        "de": "Chaos / Notfall: Provider-Ausfall erzeugen oder Umschalttest fahren",
        "en": "Chaos / DR: inject provider outage or run failover test",
    },
    "cmd.chaos.action": {
        "de": "status | start | stop | test",
        "en": "status | start | stop | test",
    },
    "cmd.chaos.provider": {
        "de": "Provider-Kennung (z. B. opencode_zen)",
        "en": "provider id (e.g. opencode_zen)",
    },
    "cmd.chaos.duration": {
        "de": "Dauer des Ausfalls: 30s, 5m, 1h (Vorgabe 5m)",
        "en": "inject duration: 30s, 5m, 1h (default 5m)",
    },
    "cmd.chaos.probes": {
        "de": "Stichproben für den Chaos-Test",
        "en": "probes for chaos test",
    },
    "cmd.chaos.intent": {
        "de": "Route-Intent für den Test",
        "en": "route intent for test",
    },
    "cmd.chaos.chat": {
        "de": "zusätzlich kleine Chats senden (kostet)",
        "en": "also send tiny chats (costs)",
    },
    "cmd.chaos.all": {
        "de": "alle Ausfälle beenden",
        "en": "stop all injects",
    },
    "cmd.paths": {
        "de": "Übertragbare Pfadübersicht ausgeben",
        "en": "Print portable path snapshot",
    },
    "cmd.consumer_add": {
        "de": "HTTP-Consumer anlegen (id:secret)",
        "en": "Add HTTP consumer (id:secret)",
    },
    "cmd.consumer_add.id": {
        "de": "Consumer-Kennung (z. B. n8n, gnom)",
        "en": "consumer id (e.g. n8n, gnom)",
    },
    "cmd.consumer_add.config": {
        "de": "/v1/config erlauben",
        "en": "allow /v1/config",
    },
    "cmd.consumer_add.secret": {
        "de": "festes Secret (optional)",
        "en": "optional fixed secret",
    },
    "cmd.consumer_add.label": {
        "de": "Anzeigename",
        "en": "display label",
    },
    "cmd.envelope": {
        "de": "Tages-Envelopes und Agentenschutz setzen oder auflisten "
              "(consumer_envelopes)",
        "en": "Set / list day envelopes + agent protection (consumer_envelopes)",
    },
    "cmd.envelope.id": {
        "de": "Consumer-Kennung (bei --list weglassen)",
        "en": "consumer id (omit with --list)",
    },
    "cmd.envelope.list": {
        "de": "alle Envelopes und ihren Verbrauch auflisten",
        "en": "list all envelopes + usage",
    },
    "cmd.envelope.allow_provider": {
        "de": "L3-Scope: Provider erlauben (mehrfach möglich); ersetzt die Liste "
              "allowed_providers",
        "en": "L3 scope: allow provider (repeatable); replaces allowed_providers list",
    },
    "cmd.envelope.block_provider": {
        "de": "L3-Scope: Provider sperren (mehrfach möglich)",
        "en": "L3 scope: block provider (repeatable)",
    },
    "cmd.envelope.allow_intent": {
        "de": "L3-Scope: Intent erlauben, z. B. free_llm,search (mehrfach möglich)",
        "en": "L3 scope: allow intent e.g. free_llm,search (repeatable)",
    },
    "cmd.envelope.block_intent": {
        "de": "L3-Scope: Intent sperren (mehrfach möglich)",
        "en": "L3 scope: block intent (repeatable)",
    },
    "cmd.envelope.allow_op": {
        "de": "L3-Scope: Operation erlauben, z. B. chat,search (mehrfach möglich)",
        "en": "L3 scope: allow op e.g. chat,search (repeatable)",
    },
    "cmd.envelope.block_op": {
        "de": "L3-Scope: Operation sperren (mehrfach möglich)",
        "en": "L3 scope: block op (repeatable)",
    },
    "cmd.envelope.clear_scopes": {
        "de": "alle allowed_*/blocked_*-Listen dieses Consumers entfernen",
        "en": "remove all allowed_*/blocked_* lists for this consumer",
    },
    "cmd.envelope.remove": {
        "de": "Envelope dieses Consumers entfernen (fällt auf _default zurück)",
        "en": "remove envelope for this consumer (fall back to _default)",
    },
    "cmd.distill": {
        "de": "Distill-JSON für einen neuen Provider anlegen",
        "en": "Scaffold distill JSON for a new provider",
    },
    "cmd.distill.provider": {
        "de": "Provider-Kennung (z. B. azure_openai)",
        "en": "provider id (e.g. azure_openai)",
    },
    "cmd.distill.title": {
        "de": "Anzeigetitel",
        "en": "display title",
    },
    "cmd.distill.env": {
        "de": "z. B. AZURE_OPENAI_API_KEY",
        "en": "e.g. AZURE_OPENAI_API_KEY",
    },
    "cmd.distill.high_risk": {
        "de": "als high_risk kennzeichnen (muss ausdrücklich freigegeben werden, "
              "mit engen $-Grenzen)",
        "en": "mark high_risk (must enable explicitly + tight $ caps)",
    },
    "cmd.high_risk": {
        "de": "high_risk_providers in keys_app.json auflisten oder setzen",
        "en": "List / set high_risk_providers in keys_app.json",
    },
    "cmd.doctor": {
        "de": "Installation und Konfiguration prüfen (erster Schritt nach der "
              "Einrichtung)",
        "en": "Self-diagnose install/config (first step after setup)",
    },
    "cmd.doctor.providers": {
        "de": "Provider zusätzlich live prüfen",
        "en": "include live provider diagnose",
    },
    "cmd.json": {
        "de": "maschinenlesbare Ausgabe",
        "en": "machine-readable output",
    },
    "cmd.advise": {
        "de": "Vorschläge für Routing und Budget aus dem Ledger (wird nie "
              "automatisch angewandt)",
        "en": "Propose routing/budget tweaks from ledger (never auto-applies)",
    },
    "cmd.desk": {
        "de": "Kurzer Lagebericht (Freeze · Resilience · Ausgaben · Auffälliges)",
        "en": "Compact desk status (freeze · resilience · spend · attention)",
    },
    "cmd.desk.json": {
        "de": "maschinenlesbares JSON (Vorgabe ist lesbarer Text)",
        "en": "machine-readable JSON (default is human text)",
    },
    "cmd.report_card": {
        "de": "AI Reliability Report — Zeugnis (PASS/FAIL für Protect · Route · Prove)",
        "en": "AI Reliability Report scorecard (PASS/FAIL for Protect·Route·Prove)",
    },
    "cmd.report_card.label": {
        "de": "Bezeichnung, z. B. Customer Support Agent",
        "en": "label e.g. Customer Support Agent",
    },
    "cmd.report_card.json": {
        "de": "JSON statt Textkarte",
        "en": "JSON instead of text card",
    },
    "cmd.demo": {
        "de": "Vorführung: Tool-Schleife eines Agenten blocken, optional mit "
              "Chaos-Nachweis",
        "en": "Killer demo: agent tool-loop block + optional chaos DR proof",
    },
    "cmd.demo.protect_only": {
        "de": "nur den Protect-Teil (kein Chaos-Test)",
        "en": "only Protect Aha (no chaos test)",
    },
    "cmd.demo.consumer": {
        "de": "Agenten-Spur (Vorgabe support-agent)",
        "en": "agent lane id (default support-agent)",
    },
    "cmd.demo.provider": {
        "de": "Provider für Chaos- und Aufrufversuch (Vorgabe opencode_zen)",
        "en": "provider for chaos / invoke attempt (default opencode_zen)",
    },
    "cmd.freeze": {
        "de": "Not-Aus — jede kostenpflichtige Zulassung verweigern",
        "en": "Emergency kill switch — deny all billable admission",
    },
    "cmd.freeze.state": {
        "de": "on (Vorgabe) | off/unfreeze | status",
        "en": "on (default) | off/unfreeze | status",
    },
    "cmd.freeze.reason": {
        "de": "Grund für den Freeze (Audit + Webhook)",
        "en": "why freeze (audit + webhook)",
    },
    "cmd.unfreeze": {
        "de": "Kurzform für: freeze off",
        "en": "Alias for: freeze off",
    },
    "cmd.circuit": {
        "de": "Schutzschalter auflisten oder zurücksetzen",
        "en": "List or reset circuit breakers",
    },
    "cmd.circuit.action": {
        "de": "list | reset | status",
        "en": "list | reset | status",
    },
    "cmd.circuit.provider": {
        "de": "Provider-Kennung zum Zurücksetzen (bei --all weglassen)",
        "en": "provider id for reset (omit with --all)",
    },
    "cmd.circuit.all": {
        "de": "jeden Schutzschalter zurücksetzen",
        "en": "reset every circuit",
    },
    "cmd.alerts": {
        "de": "Webhook-Meldungen: Zustellung testen oder Ereignisliste zeigen",
        "en": "Webhook alerts: test delivery or list event catalog",
    },
    "cmd.alerts.action": {
        "de": "test | events",
        "en": "test | events",
    },
    "cmd.alerts.message": {
        "de": "Text für die Testmeldung",
        "en": "message for alert test",
    },
    "cmd.snapshot": {
        "de": "Betriebszustand aus- und einlesen (tragbarer USB-Umzug)",
        "en": "Export/import desk ops state (portable USB migration)",
    },
    "cmd.snapshot.action": {
        "de": "export | import | info",
        "en": "export | import | info",
    },
    "cmd.snapshot.path": {
        "de": "Archivpfad (.tgz)",
        "en": "archive path (.tgz)",
    },
    "cmd.snapshot.out": {
        "de": "Ziel des Exports (Vorgabe: tollgate-snapshot-<tag>.tgz)",
        "en": "export destination (default: tollgate-snapshot-<day>.tgz)",
    },
    "cmd.snapshot.secrets": {
        "de": "Key.txt / .env mitnehmen (heikel — standardmäßig aus)",
        "en": "export Key.txt / .env (sensitive — off by default)",
    },
    "cmd.snapshot.no_audit": {
        "de": "audit.jsonl vom Export ausnehmen",
        "en": "omit audit.jsonl from export",
    },
    "cmd.snapshot.force": {
        "de": "Import: vorhandene Dateien überschreiben (Vorgabe führt nur "
              "keys_app zusammen)",
        "en": "import: overwrite existing files (default merges keys_app only)",
    },
    "cmd.snapshot.dry_run": {
        "de": "Import: Plan zeigen, ohne zu schreiben",
        "en": "import: show plan without writing",
    },
    "cmd.report": {
        "de": "Täglicher Betriebsbericht — Nachweise für Protect · Route · Prove",
        "en": "Daily operator report — Protect · Route · Prove evidence",
    },
    "cmd.report.format": {
        "de": "md (Vorgabe) oder json",
        "en": "md (default) or json",
    },
    "cmd.report.out": {
        "de": "in Datei schreiben (optional)",
        "en": "write to file (optional)",
    },
    "cmd.audit": {
        "de": "Audit-Spur abfragen — wer wurde abgewiesen und warum (nur Betrieb)",
        "en": "Query audit trail — who was denied and why (ops only)",
    },
    "cmd.audit.event": {
        "de": "nach Ereignis filtern (admit_deny, usage, …)",
        "en": "filter event (admit_deny, usage, …)",
    },
    "cmd.audit.consumer": {
        "de": "nach Consumer- oder Agenten-Kennung filtern",
        "en": "filter consumer/agent id",
    },
    "cmd.audit.provider": {
        "de": "nach Provider-Kennung filtern",
        "en": "filter provider id",
    },
    "cmd.audit.limit": {
        "de": "höchste Zeilenzahl (Vorgabe 30)",
        "en": "max rows (default 30)",
    },
    "cmd.audit.summary": {
        "de": "Zusammenfassung: häufigste Ablehnungsgründe, nach Ereignis und "
              "Consumer",
        "en": "aggregates: top deny reasons + by event/consumer",
    },
    "cmd.audit.json": {
        "de": "maschinenlesbar (Vorgabe)",
        "en": "machine-readable (default)",
    },
    "cmd.search": {
        "de": "Module, Dokumente, HTTP und CLI durchsuchen (Code finden, ohne "
              "Pfade zu raten)",
        "en": "Search repo modules / docs / HTTP / CLI (find code without guessing paths)",
    },
    "cmd.search.query": {
        "de": "Suchbegriffe (z. B. circuit breaker); bei --map weglassen",
        "en": "search terms (e.g. circuit breaker); omit with --map",
    },
    "cmd.search.kind": {
        "de": "Filter: concept module doc http cli config script (mehrfach möglich)",
        "en": "filter: concept module doc http cli config script (repeatable)",
    },
    "cmd.search.limit": {
        "de": "höchste Trefferzahl (Vorgabe 15)",
        "en": "max hits (default 15)",
    },
    "cmd.search.map": {
        "de": "die ganze Repo-Karte als Markdown ausgeben (Inhalt von docs/MAP.md)",
        "en": "print full repo map markdown (docs/MAP.md body)",
    },
    # --- Ausgaben ---
    "out.search_usage": {
        "de": "Aufruf: tollgate search <suche> [--kind module] [--json]\n"
              "        tollgate search --map\n"
              "Beispiele: tollgate search circuit breaker\n"
              "           tollgate search budget --kind concept\n"
              "Karte: docs/MAP.md",
        "en": "usage: tollgate search <query> [--kind module] [--json]\n"
              "       tollgate search --map\n"
              "examples: tollgate search circuit breaker\n"
              "          tollgate search budget --kind concept\n"
              "map: docs/MAP.md",
    },
    "out.wrote": {
        "de": "geschrieben {path}",
        "en": "wrote {path}",
    },
    "out.demo_missing": {
        "de": "Vorführskript nicht gefunden — aus dem Repo-Verzeichnis starten:\n"
              "  ./scripts/demo-agent-safety.sh\n"
              "oder: docs/DEMO.md",
        "en": "demo script not found — run from repo checkout:\n"
              "  ./scripts/demo-agent-safety.sh\n"
              "or: docs/DEMO.md",
    },
    "out.use_header": {
        "de": "\nKopfzeile verwenden: X-Consumer-Key: {key}",
        "en": "\nUse header: X-Consumer-Key: {key}",
    },
    "out.config": {
        "de": "[tollgate] Konfiguration: {path}",
        "en": "[tollgate] config: {path}",
    },
    "out.error": {
        "de": "[tollgate] FEHLER: {message}",
        "en": "[tollgate] ERROR: {message}",
    },
    "out.open_mode": {
        "de": "[tollgate] offener Modus (lokaler Schreibtisch) · Dashboard "
              "http://{host}:{port}/dashboard",
        "en": "[tollgate] open mode (local desk) · dashboard "
              "http://{host}:{port}/dashboard",
    },
    "out.auth_mode": {
        "de": "[tollgate] Anmeldemodus · http://{host}:{port}/dashboard",
        "en": "[tollgate] auth mode · http://{host}:{port}/dashboard",
    },
}


def normalise(language: str | None) -> str:
    """Gibt immer eine unterstuetzte Sprache zurueck."""
    if not language:
        return DEFAULT_LANGUAGE
    code = language.strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def from_environment(env: dict[str, str] | None = None) -> str:
    """Liest die Sprache aus den ueblichen Locale-Variablen."""
    source = os.environ if env is None else env
    for name in ENVIRONMENT_VARIABLES:
        raw = (source.get(name) or "").strip()
        code = raw.split(".", 1)[0].split("@", 1)[0]
        if code.lower() in NEUTRAL_LOCALES:
            continue
        return normalise(code)
    return DEFAULT_LANGUAGE


def from_accept_header(header: str | None) -> str:
    """Liest die erste unterstuetzte Sprache aus einem Accept-Language-Kopf."""
    if not header:
        return DEFAULT_LANGUAGE
    for chunk in header.split(","):
        code = chunk.split(";", 1)[0].strip().lower().replace("_", "-")
        base = code.split("-", 1)[0]
        if base in LANGUAGES:
            return base
    return DEFAULT_LANGUAGE


def translate(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    """Uebersetzt einen Schluessel.

    Ein unbekannter Schluessel gibt den Schluessel selbst zurueck, damit die
    Oberflaeche nicht zerbricht — der Test faengt ihn vorher ab.
    """
    entry = CATALOG.get(key)
    if entry is None:
        return key
    text = entry.get(normalise(language)) or entry[DEFAULT_LANGUAGE]
    return text.format(**values) if values else text


def catalog_for(language: str) -> dict[str, str]:
    """Der ganze Katalog in einer Sprache."""
    code = normalise(language)
    return {key: entry.get(code) or entry[DEFAULT_LANGUAGE]
            for key, entry in CATALOG.items()}
