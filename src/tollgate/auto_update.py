"""
Background auto-update of provider status / model caches.

Daemon-light: start/stop on hub; interval from keys_app.json.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

_LOCK = threading.RLock()
_STATE: dict[str, Any] = {
    "running": False,
    "thread": None,
    "last_run": None,
    "last_ok": None,
    "last_error": None,
    "cycles": 0,
    "snapshot": None,
}


def status() -> dict[str, Any]:
    with _LOCK:
        return {
            "running": bool(_STATE["running"]),
            "last_run": _STATE["last_run"],
            "last_ok": _STATE["last_ok"],
            "last_error": _STATE["last_error"],
            "cycles": _STATE["cycles"],
            "snapshot": _STATE.get("snapshot"),
        }


def _cycle(get_service: Callable[[], Any]) -> dict[str, Any]:
    from tollgate.app_config import load_config

    cfg = load_config()
    au = cfg.get("auto_update") or {}
    live = bool(au.get("live_probes"))
    refresh_models = bool(au.get("refresh_models", True))

    ks = get_service()
    inv = ks.inventory(live=live, use_cache=False)
    models: dict[str, Any] = {}
    if refresh_models:
        for pid, op in (
            ("deepseek", "models"),
            ("opencode_zen", "models"),
            ("nvidia", "models"),
            ("openrouter", "models"),
        ):
            try:
                # skip if disabled
                from tollgate.app_config import is_provider_enabled

                if not is_provider_enabled(pid):
                    continue
                r = ks.call(pid, op)
                if r.get("ok"):
                    models[pid] = {
                        "count": r.get("count") or r.get("total") or len(r.get("models") or []),
                        "sample": (r.get("sample") or r.get("free_models") or r.get("models") or [])[
                            :5
                        ],
                    }
            except Exception as e:  # noqa: BLE001
                models[pid] = {"error": str(e)}

    snap = {
        "ts": time.time(),
        "live": live,
        "grades": inv.get("grades"),
        "ready": inv.get("ready"),
        "models": models,
    }
    return snap


def start(get_service: Callable[[], Any], *, interval_s: float | None = None) -> dict[str, Any]:
    """Start background updater if not already running."""
    from tollgate.app_config import load_config

    cfg = load_config()
    au = cfg.get("auto_update") or {}
    if not bool(au.get("enabled", True)):
        return {"ok": False, "error": "auto_update.disabled in keys_app.json"}

    iv = float(interval_s if interval_s is not None else au.get("interval_s") or 300)
    iv = max(60.0, iv)  # never faster than 1/min

    with _LOCK:
        if _STATE["running"]:
            return {"ok": True, "already": True, "interval_s": iv, **status()}

        stop_flag = threading.Event()

        def loop() -> None:
            while not stop_flag.is_set():
                try:
                    snap = _cycle(get_service)
                    with _LOCK:
                        _STATE["last_run"] = time.time()
                        _STATE["last_ok"] = True
                        _STATE["last_error"] = None
                        _STATE["cycles"] = int(_STATE["cycles"] or 0) + 1
                        _STATE["snapshot"] = snap
                except Exception as e:  # noqa: BLE001
                    with _LOCK:
                        _STATE["last_run"] = time.time()
                        _STATE["last_ok"] = False
                        _STATE["last_error"] = str(e)
                stop_flag.wait(iv)

        t = threading.Thread(target=loop, name="keys-auto-update", daemon=True)
        _STATE["running"] = True
        _STATE["thread"] = t
        _STATE["stop"] = stop_flag
        t.start()
        return {"ok": True, "started": True, "interval_s": iv}


def stop() -> dict[str, Any]:
    with _LOCK:
        stop_flag = _STATE.get("stop")
        if stop_flag is not None:
            stop_flag.set()
        _STATE["running"] = False
        _STATE["thread"] = None
        return {"ok": True, "stopped": True}


def run_once(get_service: Callable[[], Any]) -> dict[str, Any]:
    try:
        snap = _cycle(get_service)
        with _LOCK:
            _STATE["last_run"] = time.time()
            _STATE["last_ok"] = True
            _STATE["last_error"] = None
            _STATE["cycles"] = int(_STATE["cycles"] or 0) + 1
            _STATE["snapshot"] = snap
        return {"ok": True, "snapshot": snap}
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            _STATE["last_error"] = str(e)
            _STATE["last_ok"] = False
        return {"ok": False, "error": str(e)}
