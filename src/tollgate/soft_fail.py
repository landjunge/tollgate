"""
Observability failures must not break the critical path — but must not be silent.

Rule (architect):
  Critical path  → fail closed / defined fallback
  Observability  → fail open + log (+ optional metric)
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("tollgate.soft_fail")

# In-process counters for doctor / tests (not durable)
_COUNTS: dict[str, int] = {}


def soft_fail(
    subsystem: str,
    exc: BaseException | None = None,
    *,
    message: str = "",
    provider: str = "",
    op: str = "",
    extra: dict[str, Any] | None = None,
    audit: bool = True,
) -> None:
    """
    Record a non-fatal subsystem error. Never raises.

    Use for: audit append, alerts, cache, agent_rates peek, optional metrics.
    Do **not** use for admit/limits/ledger reserve (those stay fail-closed).

    ``audit=False`` for hot paths (``/metrics`` scrape, bootstrap, audit write
    itself) — still counts + logs, does not write audit.jsonl.
    """
    name = (subsystem or "unknown").strip()[:64] or "unknown"
    _COUNTS[name] = int(_COUNTS.get(name) or 0) + 1
    detail = message or (str(exc) if exc is not None else "error")
    detail = detail[:400]
    try:
        _log.warning(
            "soft_fail subsystem=%s provider=%s op=%s detail=%s",
            name,
            (provider or "")[:64],
            (op or "")[:64],
            detail,
        )
    except Exception:  # noqa: BLE001
        pass
    if not audit:
        return
    # Best-effort audit breadcrumb (nested soft — must not recurse loudly)
    try:
        from tollgate.audit_log import append_audit

        append_audit(
            "soft_fail",
            provider=provider or None,
            op=op or None,
            error=detail,
            ok=False,
            extra={"subsystem": name, **(extra or {})},
        )
    except Exception:  # noqa: BLE001
        pass


def soft_fail_counts() -> dict[str, int]:
    return dict(_COUNTS)


def reset_soft_fail_counts() -> None:
    _COUNTS.clear()
