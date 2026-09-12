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

from tollgate import cli, help_text, i18n

CLI_SOURCE = Path(cli.__file__)

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
}
# Satzzeichen, Symbole und reine Platzhalter tragen keine Sprache.
SYMBOLS = re.compile(r"^[\s·—–\-−→←+×÷/|,.:;!?()\[\]{}<>#*&%@0-9…\"'`~^=°$§]*$")
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


def _unexpected(texts: list[str]) -> list[str]:
    out = []
    for text in texts:
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


def test_every_catalog_key_is_used() -> None:
    """Kein toter Schlüssel — sonst wächst der Katalog ins Nichts."""
    used = {text for _, text in _cli_string_literals()
            if text.startswith(("cmd.", "cli.", "out."))}
    declared = set(i18n.CATALOG)
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
