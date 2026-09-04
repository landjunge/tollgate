"""Consumer ids are client-asserted and must not reach the dashboard DOM as markup.

The chain this guards:

    X-Consumer-Key header
      -> limits.check_consumer_limits / usage_ledger.record_usage  (ledger key)
      -> GET /v1/control  ("consumers": [{"consumer": ...}])
      -> dashboard_html.py  `innerHTML = ... ${c.consumer} ...`

The dashboard shares an origin with /v1/config, and in open mode every caller is
admin. Markup rendered there runs with full control-plane authority: it can raise
budgets, lift a freeze, or add a provider whose base_url points at an attacker,
which turns the key vault into an exfiltration path.

Both layers are tested on purpose. Charset validation alone breaks the moment a
new field is rendered; escaping alone breaks the moment a value reaches a
non-escaping sink. Neither is allowed to be the only defence.
"""

from __future__ import annotations

import json

import pytest

from tollgate.consumers import ANONYMOUS, consumer_id_is_valid, normalize_consumer_id

HOSTILE = [
    "<img src=x onerror=alert(1)>",
    '"><script>fetch("//evil")</script>',
    "</div><svg onload=alert(1)>",
    "a' onmouseover='alert(1)",
    "lane\nX-Injected: 1",
]

LEGITIMATE = ["n8n", "gnom", "desk", "support-agent", "lane.2", "a_b-c", "n8n:prod"]


# ── layer 1: the edge normalizer ────────────────────────────────────────────


@pytest.mark.parametrize("value", HOSTILE)
def test_hostile_labels_collapse_to_anonymous(value):
    assert normalize_consumer_id(value) == ANONYMOUS
    assert not consumer_id_is_valid(value)


@pytest.mark.parametrize("value", LEGITIMATE)
def test_ordinary_lane_names_survive_untouched(value):
    # A silently *stripped* label would split one lane's budget across two
    # ledger keys, so legitimate names must pass through byte-identical.
    assert normalize_consumer_id(value) == value
    assert consumer_id_is_valid(value)


def test_header_parsing_normalizes_the_claimed_id():
    from tollgate.consumers import parse_consumer_header

    cid, secret = parse_consumer_header(f"{HOSTILE[0]}:s3cret")
    assert cid == ANONYMOUS
    # The secret half must still be forwarded for verification.
    assert secret == "s3cret"


# ── layer 2: nothing hostile survives into the control plane ────────────────


def test_ledger_key_cannot_carry_markup(tmp_path, monkeypatch):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True, exist_ok=True)

    from tollgate import usage_ledger

    usage_ledger.record_usage(
        "opencode_zen", consumer=HOSTILE[0], usd=0.05, tokens_in=10, tokens_out=10
    )
    data = usage_ledger.load_usage()
    keys = list((data.get("consumers") or {}).keys())
    assert HOSTILE[0] not in keys
    assert keys == [ANONYMOUS]


def test_control_endpoint_never_emits_markup_in_consumer_names(tmp_path, monkeypatch):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True, exist_ok=True)

    from fastapi.testclient import TestClient

    from tollgate import usage_ledger
    from tollgate.server_v1 import app

    for hostile in HOSTILE:
        usage_ledger.record_usage("opencode_zen", consumer=hostile, usd=0.01)

    with TestClient(app) as client:
        body = client.get("/v1/control").text

    for hostile in HOSTILE:
        assert hostile not in body, f"hostile consumer label reached /v1/control: {hostile!r}"

    names = [c.get("consumer") for c in json.loads(body).get("consumers", [])]
    assert all(consumer_id_is_valid(n) or n == ANONYMOUS for n in names), names


# ── layer 3: the renderer escapes regardless of what reaches it ─────────────


def test_dashboard_defines_an_escape_helper():
    from tollgate.dashboard_html import DASHBOARD_HTML

    assert "function esc(" in DASHBOARD_HTML
    for entity in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert entity in DASHBOARD_HTML, f"esc() does not encode {entity}"


def test_free_text_fields_are_escaped_before_innerHTML():
    """Defence in depth: even a value that slipped past layer 1 must not render.

    Pinned by field name so that re-introducing a raw `${c.consumer}` in a new
    template literal fails here rather than in production.
    """
    from tollgate.dashboard_html import DASHBOARD_HTML

    raw_sinks = [
        "${c.consumer}",
        "${p.provider}",
        "${r.text}",
        "${OB.name}",
        "${last.chaos_provider}",
        "${ch.label}",
    ]
    for sink in raw_sinks:
        assert sink not in DASHBOARD_HTML, f"unescaped interpolation still present: {sink}"
        assert sink.replace("${", "${esc(").replace("}", ")}") in DASHBOARD_HTML
    for needle in (
        "${esc(e.consumer",
        "${esc(e.provider",
        "${esc(ev)}",
        "${esc(last.message",
        "${esc(ch.detail)}",
        "${esc(a.message",
        "${esc(a.code",
    ):
        assert needle in DASHBOARD_HTML, f"missing escaped sink: {needle}"
