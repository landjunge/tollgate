"""Consumer secrets on disk, and what a stored hash is allowed to prove.

`consumers.json` sits in the same directory as `Key.txt`. Anything that can read
one can read the other, so the stored hashes are a second line of defence, not
the first — but an unsalted single-round digest of an operator-chosen secret is
no defence at all.

Auto-generated secrets were never the problem (192 bits). `consumer-add --secret`
is: a human-picked string behind a bare SHA-256 falls to a wordlist immediately.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from tollgate import consumers as C


@pytest.fixture(autouse=True)
def isolated_consumers(tmp_path, monkeypatch):
    monkeypatch.setenv("TOLLGATE_CONSUMERS", str(tmp_path / "consumers.json"))
    C.clear_cache()
    yield
    C.clear_cache()


# ── stored format ───────────────────────────────────────────────────────────


def test_stored_hash_is_salted_and_not_a_bare_digest():
    secret = "operator-chosen-passphrase"
    stored = C.hash_consumer_secret(secret)

    assert stored.startswith("scrypt$")
    assert hashlib.sha256(secret.encode()).hexdigest() not in stored


def test_same_secret_twice_yields_different_hashes():
    """No salt means one precomputed table breaks every desk at once."""
    a = C.hash_consumer_secret("same-secret-value")
    b = C.hash_consumer_secret("same-secret-value")
    assert a != b
    assert C.verify_consumer_secret("same-secret-value", a)
    assert C.verify_consumer_secret("same-secret-value", b)


def test_verification_rejects_the_wrong_secret():
    stored = C.hash_consumer_secret("right-secret-value")
    assert not C.verify_consumer_secret("wrong-secret-value", stored)
    assert not C.verify_consumer_secret("", stored)


def test_hashing_is_deliberately_slow():
    """A digest fast enough to loop is a digest fast enough to crack."""
    start = time.perf_counter()
    C.hash_consumer_secret("timing-probe-secret")
    elapsed = time.perf_counter() - start
    assert elapsed > 0.0005, f"scrypt returned in {elapsed * 1000:.3f}ms — parameters too low"


# ── upgrade path ────────────────────────────────────────────────────────────


def test_legacy_sha256_hashes_still_verify():
    """An upgrade must not lock a desk out of its own consumers."""
    legacy = hashlib.sha256(b"pre-upgrade-secret").hexdigest()
    assert C.verify_consumer_secret("pre-upgrade-secret", legacy)
    assert not C.verify_consumer_secret("something-else", legacy)
    assert C.secret_hash_is_legacy(legacy)
    assert not C.secret_hash_is_legacy(C.hash_consumer_secret("x" * 20))


def test_malformed_stored_hash_denies_rather_than_raises():
    for broken in ("scrypt$", "scrypt$zz$zz", "scrypt$nosalt", ""):
        assert C.verify_consumer_secret("anything", broken) is False


# ── the add path ────────────────────────────────────────────────────────────


def test_weak_custom_secret_is_flagged_but_honoured():
    """The operator asked for it; say so, do not silently override them."""
    out = C.add_consumer("n8n", secret="hunter2")
    assert out["ok"] is True
    assert "warning" in out
    C.clear_cache()
    assert C.verify_consumer("n8n:hunter2")["ok"] is True


def test_generated_secret_carries_no_warning():
    out = C.add_consumer("gnom")
    assert out["ok"] is True
    assert "warning" not in out


def test_generated_secret_is_accepted_and_returned_once():
    out = C.add_consumer("n8n")
    assert out["ok"] is True
    assert len(out["secret"]) >= C.WEAK_CUSTOM_SECRET_LEN

    stored = json.loads(C.consumers_path().read_text())["consumers"][0]["secret_hash"]
    assert out["secret"] not in stored
    assert C.verify_consumer_secret(out["secret"], stored)


def test_consumer_id_charset_is_enforced_at_creation():
    out = C.add_consumer("<img src=x onerror=alert(1)>")
    assert out["ok"] is False


def test_end_to_end_verify_through_the_header(monkeypatch):
    monkeypatch.setenv("TOLLGATE_REQUIRE_AUTH", "1")
    created = C.add_consumer("n8n", admin=False)
    C.clear_cache()

    ok = C.verify_consumer(f"n8n:{created['secret']}")
    assert ok["ok"] is True and ok["consumer"] == "n8n" and ok["admin"] is False

    bad = C.verify_consumer("n8n:not-the-secret-at-all")
    assert bad["ok"] is False

    needs_admin = C.verify_consumer(f"n8n:{created['secret']}", need_admin=True)
    assert needs_admin["ok"] is False
