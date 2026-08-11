"""
Global admission freeze — emergency kill switch for all billable traffic.

  tollgate freeze --reason "runaway agents"
  tollgate unfreeze
  GET/POST /v1/freeze

Env override (wins over config): TOLLGATE_FROZEN=1|0
Config: keys_app.admission.frozen (+ reason/at/by).
System request_class may still pass when allow_system_when_frozen=true.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from tollgate.app_config import load_config, save_config


def _env_frozen() -> bool | None:
    raw = (os.environ.get("TOLLGATE_FROZEN") or os.environ.get("TOLLGATE_ADMISSION_FROZEN") or "").strip().lower()
    if raw in ("1", "true", "yes", "on", "freeze", "frozen"):
        return True
    if raw in ("0", "false", "no", "off", "unfreeze"):
        return False
    return None


def admission_block() -> dict[str, Any]:
    cfg = load_config()
    adm = cfg.get("admission") if isinstance(cfg.get("admission"), dict) else {}
    return dict(adm or {})


def is_frozen() -> bool:
    env = _env_frozen()
    if env is not None:
        return env
    adm = admission_block()
    return bool(adm.get("frozen"))


def allow_system_when_frozen() -> bool:
    adm = admission_block()
    return bool(adm.get("allow_system_when_frozen", True))


def freeze_status() -> dict[str, Any]:
    adm = admission_block()
    env = _env_frozen()
    frozen = is_frozen()
    return {
        "ok": True,
        "frozen": frozen,
        "source": "env" if env is not None else "config",
        "env_override": env,
        "reason": str(adm.get("frozen_reason") or "") if env is None else "TOLLGATE_FROZEN env",
        "frozen_at": adm.get("frozen_at"),
        "frozen_by": str(adm.get("frozen_by") or ""),
        "allow_system_when_frozen": allow_system_when_frozen(),
        "message": (
            "ADMISSION FROZEN — all billable traffic denied"
            if frozen
            else "admission open"
        ),
    }


def set_frozen(
    frozen: bool,
    *,
    reason: str = "",
    by: str = "cli",
    root: Any = None,
) -> dict[str, Any]:
    """
    Persist freeze flag to keys_app.json.
    Env TOLLGATE_FROZEN still overrides at runtime if set.
    """
    cfg = load_config(force=True, root=root)
    adm = dict(cfg.get("admission") or {}) if isinstance(cfg.get("admission"), dict) else {}
    adm["frozen"] = bool(frozen)
    if frozen:
        adm["frozen_reason"] = (reason or adm.get("frozen_reason") or "manual freeze")[:200]
        adm["frozen_at"] = datetime.now(timezone.utc).isoformat()
        adm["frozen_by"] = (by or "cli")[:64]
        adm.setdefault("allow_system_when_frozen", True)
    else:
        adm["frozen_reason"] = ""
        adm["frozen_at"] = None
        adm["frozen_by"] = (by or "cli")[:64]
    cfg["admission"] = adm
    save_config(cfg, root=root)

    try:
        from tollgate.alerts import maybe_alert

        maybe_alert(
            "admission_frozen" if frozen else "admission_unfrozen",
            provider="",
            message=adm.get("frozen_reason") or ("frozen" if frozen else "unfrozen"),
            extra={"by": by, "frozen": frozen},
            force=True,
        )
    except Exception:  # noqa: BLE001
        pass

    try:
        from tollgate.audit_log import append_audit

        append_audit(
            "admission_frozen" if frozen else "admission_unfrozen",
            consumer=by,
            error=str(adm.get("frozen_reason") or ""),
            ok=not frozen,
            extra={"frozen": frozen, "by": by},
            root=root,
        )
    except Exception:  # noqa: BLE001
        pass

    st = freeze_status()
    st["applied"] = True
    st["ts"] = time.time()
    return st
