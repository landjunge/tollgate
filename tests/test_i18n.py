"""Zweisprachigkeit DE/EN — und der Wächter dagegen, sie zu vergessen.

Alle NetzwerkPunkt-Werkzeuge sind zweisprachig. Nachrüsten ist teuer, also
hält dieser Test fest, dass kein sichtbarer Text an der Übersetzung vorbei
in die Kommandozeile rutscht.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tollgate import cli, dashboard_html, help_text, i18n

CLI_SOURCE = Path(cli.__file__)
DASHBOARD_SOURCE = Path(dashboard_html.__file__)
# {{schluessel}} ist die Marke im Dashboard-Template.
MARKER = re.compile(r"\{\{([\w.]+)\}\}")

# Eigennamen, Fachbegriffe und Zeichen, die in beiden Sprachen gleich stehen.
SAME_IN_BOTH = {
    "tollgate", "protect", "route", "prove", "provider", "consumer", "chaos",
    "mcp", "json", "md", "http", "https", "uvicorn", "openai", "docker",
    "id", "secret", "status", "start", "stop", "test", "list", "reset", "info",
    "export", "import", "on", "off", "unfreeze", "freeze", "events", "de", "en",
    "l3", "scope", "envelope", "op", "intent", "key", "usd", "high_risk",
    "keys_app", "audit", "usage", "admit_deny", "free_llm", "search", "chat",
    "opencode_zen", "azure_openai", "n8n", "gnom", "support", "agent",
    "customer", "ai", "resilience", "score", "concept", "module", "doc", "cli",
    "config", "script", "map", "dashboard",
    # Die Themennamen tippt der Nutzer ein (tollgate help troubleshoot) und
    # duerfen deshalb in keiner Sprache uebersetzt werden.
    "ui", "api", "ops", "env", "faq", "troubleshoot", "commands",
    # Produktbegriffe und Woerter, die im Deutschen genauso stehen.
    "control", "room", "github", "help", "report", "detail",
    "requests", "req", "tools", "tokens",
}
# Satzzeichen, Symbole und reine Platzhalter tragen keine Sprache.
SYMBOLS = re.compile(r"^[\s·—–\-−→←+×÷/|,.:;!?()\[\]{}<>«»#*&%@0-9…\"'`~^=°$§]*$")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
# Befehle, Flags, Pfade, URLs und Variablennamen sind sprachneutral.
NEUTRAL = re.compile(
    r"^(?:tollgate|python3|export|curl|docker|open|\./|--|-[a-z]|/|\$|https?://)"
    r"|^[A-Z][A-Z0-9_]{3,}$|^[\w./~-]+\.[a-z]{1,4}$|^[\w./~-]+/[\w./~-]*$")

# Ein Literal gilt als Fliesstext, wenn es ein Wort aus drei Buchstaben
# enthaelt UND entweder ein Leerzeichen oder einen Umlaut hat.
WORD = re.compile(r"[A-Za-zÄÖÜäöüß]{3,}")
UMLAUT = re.compile(r"[ÄÖÜäöüß]")
# Texte, die argparse selbst erzeugt, liegen ausserhalb des Katalogs.
CLI_ALLOWED = {
    "status | start | stop | test",
    "list | reset | status",
    "test | events",
    "export | import | info",
    "on (default) | off/unfreeze | status",
    "start|protect|route|prove|ui|api|ops|troubleshoot|commands|env|config|faq",
    "md (default) or json",
}


# Ganze Wortgruppen, die Produktnamen sind und deshalb in beiden Sprachen
# gleich stehen. Bewusst die Wortgruppe, nicht das einzelne Wort: "Reliability"
# allein wird sehr wohl uebersetzt (ui.reliability -> Verlässlichkeit).
PRODUCT_NAMES = {
    "AI Reliability Report",
    "Control Room",
}


def _unexpected(texts: list[str]) -> list[str]:
    out = []
    for text in texts:
        if text in PRODUCT_NAMES:
            continue
        bare = PLACEHOLDER.sub(" ", text)
        words = [w for w in re.split(r"[\s·—–/|,.:;!?()\[\]]+", bare) if w]
        if all(w.lower().strip("-_") in SAME_IN_BOTH or SYMBOLS.match(w)
               or NEUTRAL.match(w) for w in words):
            continue
        out.append(text)
    return out


# Nicht jede Zeichenkette ist Bedienungstext. Diese drei Stellen tragen
# Daten, keine Anzeige — und muessen stabil bleiben:
#   "error" in json.dumps(...)  wird von Skripten ausgewertet
#   default=...                 ist der Inhalt eines Werts, nicht seine Beschriftung
#   reason=...                  landet als Datensatz im Audit-Protokoll
DATA_KEYS = {"error"}
DATA_KEYWORDS = {"default", "reason"}


def _data_literals(tree: ast.AST) -> set[int]:
    """Zeichenketten, die Daten sind statt Anzeige."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value in DATA_KEYS):
                    for part in ast.walk(value):
                        if isinstance(part, ast.Constant):
                            found.add(id(part))
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in DATA_KEYWORDS:
                    for part in ast.walk(kw.value):
                        if isinstance(part, ast.Constant):
                            found.add(id(part))
    return found


def _cli_string_literals() -> list[tuple[int, str]]:
    """Alle sichtbaren Zeichenketten aus cli.py ohne Docstrings und Daten."""
    tree = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    skip = _data_literals(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)):
                skip.add(id(body[0].value))
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip):
            found.append((node.lineno, node.value))
    return found


# --------------------------------------------------------------- Katalog

def test_every_key_has_both_languages() -> None:
    missing = [key for key, entry in i18n.CATALOG.items()
               if set(entry) != set(i18n.LANGUAGES)
               or not all(entry.get(lang, "").strip() for lang in i18n.LANGUAGES)]
    assert not missing, f"unvollständige Schlüssel: {missing}"


def test_languages_differ_where_they_should() -> None:
    """Identische Texte sind erlaubt, aber selten — sie sollen auffallen."""
    identical = [key for key, entry in i18n.CATALOG.items()
                 if entry["de"] == entry["en"]]
    unexpected = [key for key in identical
                  if _unexpected([i18n.CATALOG[key]["de"]])]
    assert not unexpected, f"DE und EN gleich, aber kein Eigenname: {unexpected}"


def test_placeholders_match_across_languages() -> None:
    for key, entry in i18n.CATALOG.items():
        marks = {lang: sorted(PLACEHOLDER.findall(text))
                 for lang, text in entry.items()}
        assert marks["de"] == marks["en"], f"{key}: Platzhalter weichen ab: {marks}"


def test_unknown_key_returns_key() -> None:
    assert i18n.translate("gibt.es.nicht") == "gibt.es.nicht"


# ------------------------------------------------------------ Hilfe-Themen

def test_every_topic_has_both_languages() -> None:
    for name in help_text.TOPIC_NAMES:
        entry = help_text.TOPICS[name]
        assert set(entry) == set(i18n.LANGUAGES), f"{name}: Sprache fehlt"
        for lang in i18n.LANGUAGES:
            assert entry[lang].strip(), f"{name}/{lang} ist leer"


def test_topic_names_match_the_help_flag() -> None:
    """Die Liste im Hilfetext und die echten Themen dürfen nicht auseinanderlaufen."""
    advertised = i18n.CATALOG["cmd.help.topic"]["en"].split("|")
    assert sorted(advertised) == sorted(help_text.TOPIC_NAMES)


@pytest.mark.parametrize("name", help_text.TOPIC_NAMES)
def test_topic_commands_do_not_drift(name) -> None:
    """Befehle sind sprachneutral und müssen in beiden Fassungen gleich sein.

    Sonst altert eine Sprache still weg, und jemand kopiert einen Befehl, den
    es nicht mehr gibt.
    """
    entry = help_text.TOPICS[name]

    def commands(text: str) -> list[str]:
        """Nur der ausfuehrbare Teil. Der Kommentar dahinter ist Prosa und
        soll sich zwischen den Sprachen unterscheiden."""
        out = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith(("tollgate ", "python3 ", "export ", "curl ",
                                        "docker ", "./scripts/", "-H ", "-d ", "--",
                                        "GET ", "POST ")):
                continue
            out.append(stripped.split("#", 1)[0].rstrip())
        return out

    assert commands(entry["de"]) == commands(entry["en"]), (
        f"{name}: Befehlszeilen weichen zwischen DE und EN ab")


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_help_renders_in_both_languages(language) -> None:
    overview = cli._format_help("", language)
    assert overview.strip()
    for name in help_text.TOPIC_NAMES:
        assert name in overview, f"{name} fehlt in der Übersicht ({language})"
        body = cli._format_help(name, language)
        assert body.strip(), f"{name} ist leer ({language})"


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_unknown_topic_falls_back_to_overview(language) -> None:
    text = cli._format_help("gibtesnicht", language)
    assert "gibtesnicht" in text
    assert "tollgate help start" in text


# ------------------------------------------------------------- Wächter

def test_no_hardcoded_text_in_cli() -> None:
    """Kein sichtbarer Satz darf am Katalog vorbei in die CLI."""
    offenders = [
        f"{CLI_SOURCE.name}:{line}: {text!r}"
        for line, text in _cli_string_literals()
        if text not in CLI_ALLOWED
        and WORD.search(text)
        and (" " in text.strip() or UMLAUT.search(text))
    ]
    assert not offenders, "Text ohne Übersetzung in der CLI:\n" + "\n".join(offenders)


def test_cli_keys_exist() -> None:
    used = {text for _, text in _cli_string_literals()
            if text.startswith(("cmd.", "cli.", "out."))}
    assert used, "keine Katalog-Schlüssel gefunden — der Test greift ins Leere"
    missing = sorted(key for key in used if key not in i18n.CATALOG)
    assert not missing, f"fehlende Schlüssel: {missing}"


def _dashboard_markers() -> set[str]:
    """Marken {{schluessel}} und Schluessel, die der Renderer direkt nachschlägt."""
    source = DASHBOARD_SOURCE.read_text(encoding="utf-8")
    keys = set(MARKER.findall(source))
    keys |= set(re.findall(r'"(ui\.[\w.]+)"', source))
    return keys


def test_every_catalog_key_is_used() -> None:
    """Kein toter Schlüssel — sonst wächst der Katalog ins Nichts."""
    used = {text for _, text in _cli_string_literals()
            if text.startswith(("cmd.", "cli.", "out."))}
    used |= _dashboard_markers()
    used |= dashboard_html.COMPOSED_MARKERS
    # Eine Fachfassung wird ueber ihren Grundschluessel erreicht, nie direkt.
    # Sie steht deshalb in keiner Marke und ist trotzdem nicht tot.
    declared = {key for key in i18n.CATALOG
                if not key.endswith(i18n.EXPERT_SUFFIX)}
    assert not (declared - used), f"unbenutzte Schlüssel: {sorted(declared - used)}"


# ------------------------------------------------------------- Sprachwahl

@pytest.mark.parametrize("given,expected", [
    (None, "en"), ("", "en"), ("de", "de"), ("DE", "de"), ("de-AT", "de"),
    ("en", "en"), ("EN-gb", "en"), ("fr", "en"), ("klingon", "en"),
])
def test_language_normalisation(given, expected) -> None:
    assert i18n.normalise(given) == expected


@pytest.mark.parametrize("env,expected", [
    ({}, "en"),
    ({"LANG": "C"}, "en"),
    ({"LANG": "POSIX"}, "en"),
    ({"LANG": "de_DE.UTF-8"}, "de"),
    ({"LANG": "en_US.UTF-8"}, "en"),
    ({"LANG": "fr_FR.UTF-8"}, "en"),
    ({"LC_ALL": "de_AT", "LANG": "en_GB"}, "de"),
    ({"LC_ALL": "C", "LANG": "de_DE"}, "de"),
    ({"TOLLGATE_LANG": "de", "LANG": "en_US"}, "de"),
    ({"TOLLGATE_LANG": "en", "LC_ALL": "de_DE"}, "en"),
])
def test_language_from_environment(env, expected) -> None:
    assert i18n.from_environment(env) == expected


@pytest.fixture()
def clean_locale(monkeypatch):
    """Keine Locale von außen — sonst hängt der Test am Läufer."""
    for name in i18n.ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.parametrize("argv,expected", [
    (["help"], "en"),
    (["--lang", "de", "help"], "de"),
    (["--lang=de", "help"], "de"),
    (["--lang", "en", "help"], "en"),
    (["--lang", "klingon", "help"], "en"),
])
def test_flag_beats_environment(clean_locale, argv, expected) -> None:
    assert cli.resolve_language(argv) == expected


def test_english_stays_the_default(clean_locale) -> None:
    """Tollgate war rein englisch. Die Vorgabe darf sich nicht still ändern —
    sonst bricht jedes Skript, das die Ausgabe liest."""
    assert i18n.DEFAULT_LANGUAGE == "en"
    assert cli.resolve_language([]) == "en"


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_parser_help_is_translated(language) -> None:
    """Die Hilfe steht schon beim Bau des Parsers fest — auch die zählt."""
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), pytest.raises(SystemExit):
        cli.main(["--lang", language, "--help"])
    text = buffer.getvalue()
    assert i18n.translate("cli.description", language).split("(")[0].strip() in text
    assert i18n.translate("cmd.serve", language) in text
    assert i18n.translate("cmd.freeze", language) in text


def test_cli_speaks_both_languages(capsys) -> None:
    """Derselbe Befehl, zwei Sprachen, wirklich unterschiedliche Ausgabe."""
    cli.main(["--lang", "en", "help", "faq"])
    english = capsys.readouterr().out
    cli.main(["--lang", "de", "help", "faq"])
    german = capsys.readouterr().out
    assert english != german
    assert "FAQ (short)" in english
    assert "Häufige Fragen" in german


# ------------------------------------------------------------- Dashboard

# Textknoten, die Javascript erzeugt, und Zeichen ohne Sprache.
JS_FRAGMENT = re.compile(r"[=;(){}\[\]`$]|=>|\.\w|\|\|")
DASHBOARD_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")
# Ein Element mit eigenem lang= sagt ausdruecklich, in welcher Sprache sein
# Text steht — die Knoepfe des Umschalters heissen in jeder Sprache DE und EN.
LANG_MARKED = re.compile(r'<[^<>]*\blang="[a-z]{2}"[^<>]*>[^<>]*<')
# Beispielwerte in einem Feld sind das, was man eintippt, keine Prosa.
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]*$")


def test_no_hardcoded_text_in_dashboard() -> None:
    """Kein sichtbarer Text darf am Katalog vorbei ins Control Room."""
    source = DASHBOARD_SOURCE.read_text(encoding="utf-8")
    body = source[source.index("<body") :]
    lang_marked = {m.start() for m in LANG_MARKED.finditer(body)}
    offenders = []
    for match in re.finditer(r">([^<>{}`$]{2,90})<", body):
        text = " ".join(match.group(1).split())
        if not DASHBOARD_WORD.search(text) or JS_FRAGMENT.search(text):
            continue
        if any(start <= match.start() < start + 200 for start in lang_marked):
            continue
        line = source[: source.index("<body") + match.start()].count("\n") + 1
        offenders.append(f"{DASHBOARD_SOURCE.name}:{line}: {text!r}")
    for match in re.finditer(r'(?:title|placeholder|aria-label|alt)="([^"{}]{3,})"', body):
        text = match.group(1)
        if not DASHBOARD_WORD.search(text) or JS_FRAGMENT.search(text):
            continue
        if IDENTIFIER.match(text):
            continue
        line = source[: source.index("<body") + match.start()].count("\n") + 1
        offenders.append(f"{DASHBOARD_SOURCE.name}:{line}: {text!r}")
    assert not offenders, (
        "Text ohne Übersetzung im Dashboard. Statt des Textes gehört dort "
        "eine Marke {{schluessel}} hin:\n" + "\n".join(offenders))


# Javascript baut Text auch aus Zeichenketten, nicht nur aus Knoten:
#   ['Spent today', money(s.usd)]
# Ohne diese Regel bleibt genau das unentdeckt — so war es vor dem Umbau bei
# 43 Texten, darunter alle Kennzahlen-Beschriftungen.
JS_STRING = re.compile(r"'([^'\\\n]{2,90})'|\"([^\"\\\n]{2,90})\"")
# Bezeichner, Selektoren, URLs und Ereignisnamen sind kein Text.
NOT_PROSE = re.compile(r"^[\w.#\-/?=&:]*$|^(?:#|\.|/|https?:|\?)")
# CSS-Klassen und technische Attributwerte werden vor der Suche geschwaerzt.
# Sie am Aussehen zu erkennen geht schief: "pill acc" und "Spent today" sehen
# gleich aus, nur eins davon ist Text fuer Menschen.
TECHNICAL_ATTR = re.compile(
    r'\b(?:class|className|id|style|data-[\w-]+|type|role|autocomplete|href|src)='
    r'"[^"]*"')
CLASSLIST = re.compile(r"classList\.\w+\([^)]*\)")
# CSS-Selektoren und Nutzlasten, die an eine Schnittstelle gehen.
SELECTOR = re.compile(r"querySelector(?:All)?\([^)]*\)|closest\([^)]*\)")
PAYLOAD = re.compile(r"arguments:\s*\{[^{}]*\}")


def test_no_hardcoded_text_in_dashboard_javascript() -> None:
    """Auch Text, den Javascript zusammensetzt, gehört in den Katalog."""
    source = DASHBOARD_SOURCE.read_text(encoding="utf-8")
    script = source.index("<script>")
    # Technische Werte schwaerzen, Laenge erhalten, damit die Zeilennummer stimmt.
    body = source[script:]
    for pattern in (TECHNICAL_ATTR, CLASSLIST, SELECTOR, PAYLOAD):
        body = pattern.sub(lambda m: " " * len(m.group(0)), body)
    offenders = []
    for match in JS_STRING.finditer(body):
        text = (match.group(1) or match.group(2) or "").strip()
        if not DASHBOARD_WORD.search(text) or "{{" in text:
            continue
        if "${" in text or JS_FRAGMENT.search(text):
            continue
        # Prosa hat ein Satzzeichen, einen Umlaut oder ein Sonderzeichen —
        # ein reiner Bezeichner wie "pill acc" oder "agent-card" hat das nicht.
        if NOT_PROSE.match(text):
            continue
        line = source[: script + match.start()].count("\n") + 1
        offenders.append(f"{DASHBOARD_SOURCE.name}:{line}: {text!r}")
    assert not offenders, (
        "Text ohne Übersetzung im Javascript des Dashboards:\n" + "\n".join(offenders))


def test_dashboard_text_cannot_break_the_page() -> None:
    """Kein Dashboard-Text darf die Seite zerreissen.

    Die Marken werden in HTML UND in Javascript-Zeichenketten eingesetzt. Ein
    gerades Apostroph beendet dort die Zeichenkette: aus 'Los geht's' wird ein
    Syntaxfehler, und das gesamte Dashboard-Javascript ist tot. Genau so ist es
    beim Bau dieser Uebersetzung passiert.

    Typografische Anfuehrungszeichen (’ „ “ « ») sind erlaubt und ohnehin die
    richtige Form.
    """
    forbidden = {"'": "gerades Apostroph", '"': "gerades Anfuehrungszeichen",
                 "\\": "Backslash", "</": "schliessendes Tag"}
    offenders = []
    for key, entry in i18n.CATALOG.items():
        if not key.startswith("ui."):
            continue
        for language, text in entry.items():
            for char, name in forbidden.items():
                if char in text:
                    offenders.append(f"{key}/{language}: {name} in {text!r}")
    assert not offenders, (
        "Zeichen, die HTML oder Javascript zerreissen. Typografische Formen "
        "verwenden (’ statt '):\n" + "\n".join(offenders))


def test_dashboard_markers_exist_in_catalog() -> None:
    source = DASHBOARD_SOURCE.read_text(encoding="utf-8")
    markers = set(MARKER.findall(source))
    assert markers, "keine Marken gefunden — der Test greift ins Leere"
    rendered = dashboard_html.COMPOSED_MARKERS
    missing = sorted(key for key in markers - rendered if key not in i18n.CATALOG)
    assert not missing, f"Marken ohne Katalog-Eintrag: {missing}"


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_dashboard_renders_without_leftover_markers(language) -> None:
    page = dashboard_html.dashboard_html(language)
    assert "{{" not in page, "unersetzte Marke im ausgelieferten HTML"
    assert f'<html lang="{language}">' in page, "lang passt nicht zum Inhalt"


def test_dashboard_really_differs_between_languages() -> None:
    english = dashboard_html.dashboard_html("en")
    german = dashboard_html.dashboard_html("de")
    assert english != german
    assert i18n.translate("ui.tab.overview", "en") in english
    assert i18n.translate("ui.tab.overview", "de") in german
    # Die englische Seite darf keinen deutschen Text mehr tragen — vor dem
    # Umbau standen vier deutsche Tooltips auf englischen Beschriftungen.
    for key in ("ui.pill.day", "ui.pill.hour", "ui.pill.request", "ui.pill.tool_stop"):
        assert i18n.translate(key, "de") not in english, f"{key}: deutscher Text in EN"


def test_dashboard_language_switch_marks_the_current_one() -> None:
    german = dashboard_html.dashboard_html("de")
    assert 'lang="de" class="on"' in german
    assert 'lang="en" class=""' in german
