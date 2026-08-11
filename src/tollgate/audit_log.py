"""
Append-only operational audit trail.

File: User/audit.jsonl — lines are only ever APPENDED, never rewritten.
This is the technical enforcement of \"audit row on deny/spend\" without
making the daily counter file (keys_usage.json) immutable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tollgate.filelock import FileLock
from tollgate.paths import user_dir
from tollgate.redact import redact_secrets

AUDIT_NAME = "audit.jsonl"


def audit_path(root: Path | None = None) -> Path:
    return (user_dir(root) / AUDIT_NAME).resolve()


def append_audit(
    event: str,
    *,
    provider: str = "",
    op: str = "",
    consumer: str = "",
    error: str = "",
    tokens: int = 0,
    usd: float = 0.0,
    ok: bool | None = None,
    extra: dict[str, Any] | None = None,
    root: Path | None = None,
) -> None:
    """Append one JSON line. Failures are swallowed (audit must not crash calls)."""
    path = audit_path(root)
    row: dict[str, Any] = {
        "ts": time.time(),
        "event": str(event)[:64],
        "provider": str(provider)[:64],
        "op": str(op)[:64],
        "consumer": str(consumer)[:64],
        "ok": ok,
        "tokens": int(tokens or 0),
        "usd": float(usd or 0.0),
        "error": redact_secrets(error) if error else "",
    }
    if extra:
        # only short scalars
        clean: dict[str, Any] = {}
        for k, v in list(extra.items())[:12]:
            kl = str(k)[:32]
            if isinstance(v, (bool, int, float)) or v is None:
                clean[kl] = v
            elif isinstance(v, str):
                clean[kl] = redact_secrets(v)[:120]
        row["extra"] = clean
    line = json.dumps(row, ensure_ascii=False) + "\n"
    try:
        with FileLock(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:  # noqa: BLE001
        pass


def _read_tail_lines(path: Path, *, max_lines: int = 5000) -> list[str]:
    """Efficient-ish tail of audit.jsonl (reads whole file if modest)."""
    if not path.is_file():
        return []
    try:
        # typical desk audit is small; full read is fine under a few MB
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    if max_lines > 0 and len(lines) > max_lines:
        return lines[-max_lines:]
    return lines


def query_audit(
    *,
    limit: int = 50,
    event: str = "",
    consumer: str = "",
    provider: str = "",
    since_s: float = 0.0,
    max_scan: int = 8000,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Query recent audit rows (ops only — never secrets/transcripts).

    Filters are AND. ``since_s`` = unix ts lower bound (0 = no bound).
    """
    path = audit_path(root)
    lim = max(1, min(int(limit or 50), 500))
    scan = max(lim, min(int(max_scan or 8000), 50_000))
    ev_f = (event or "").strip().lower()
    cid_f = (consumer or "").strip().lower()
    pid_f = (provider or "").strip().lower()
    since = float(since_s or 0.0)

    matched: list[dict[str, Any]] = []
    scanned = 0
    for ln in reversed(_read_tail_lines(path, max_lines=scan)):
        scanned += 1
        try:
            row = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(row, dict):
            continue
        if since > 0 and float(row.get("ts") or 0) < since:
            continue
        if ev_f and str(row.get("event") or "").lower() != ev_f:
            continue
        if cid_f and str(row.get("consumer") or "").lower() != cid_f:
            continue
        if pid_f and str(row.get("provider") or "").lower() != pid_f:
            continue
        matched.append(row)
        if len(matched) >= lim:
            break

    return {
        "ok": True,
        "path": str(path),
        "count": len(matched),
        "scanned": scanned,
        "filters": {
            "event": ev_f or None,
            "consumer": cid_f or None,
            "provider": pid_f or None,
            "since_s": since or None,
            "limit": lim,
        },
        "events": matched,
    }


def audit_summary(
    *,
    max_scan: int = 5000,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Aggregate last N audit lines: counts by event/consumer, top deny reasons.
    """
    path = audit_path(root)
    lines = _read_tail_lines(path, max_lines=max(100, min(int(max_scan), 50_000)))
    by_event: dict[str, int] = {}
    by_consumer: dict[str, int] = {}
    deny_reasons: dict[str, int] = {}
    protection_blocks = 0
    admit_denies = 0
    usage_ok = 0
    total_usd = 0.0

    for ln in lines:
        try:
            row = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(row, dict):
            continue
        ev = str(row.get("event") or "unknown")[:64]
        by_event[ev] = by_event.get(ev, 0) + 1
        cid = str(row.get("consumer") or "").strip() or "anonymous"
        if ev in ("admit_deny", "usage"):
            by_consumer[cid] = by_consumer.get(cid, 0) + 1
        total_usd += float(row.get("usd") or 0.0)
        if ev == "admit_deny":
            admit_denies += 1
            err = str(row.get("error") or "")[:160]
            extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
            reason = str(extra.get("protection") or extra.get("reason") or err or "deny")[:120]
            deny_reasons[reason] = deny_reasons.get(reason, 0) + 1
            if extra.get("protection") or "agent protection" in err.lower():
                protection_blocks += 1
        if ev == "usage" and row.get("ok") is True:
            usage_ok += 1

    top_denies = sorted(deny_reasons.items(), key=lambda x: -x[1])[:12]
    top_consumers = sorted(by_consumer.items(), key=lambda x: -x[1])[:12]

    return {
        "ok": True,
        "scanned": len(lines),
        "path": str(path),
        "by_event": by_event,
        "admit_denies": admit_denies,
        "agent_protection_blocks": protection_blocks,
        "usage_ok": usage_ok,
        "usd_logged": round(total_usd, 6),
        "top_deny_reasons": [{"reason": r, "count": n} for r, n in top_denies],
        "top_consumers": [{"consumer": c, "events": n} for c, n in top_consumers],
    }


def recent_denies(
    *,
    limit: int = 15,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Short list of latest admit_deny rows for control plane / dashboard."""
    q = query_audit(limit=limit, event="admit_deny", root=root)
    out: list[dict[str, Any]] = []
    for row in q.get("events") or []:
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        out.append(
            {
                "ts": row.get("ts"),
                "consumer": row.get("consumer") or "anonymous",
                "provider": row.get("provider") or "",
                "op": row.get("op") or "",
                "error": (row.get("error") or "")[:160],
                "protection": extra.get("protection") or None,
                "reason": extra.get("reason") or row.get("error") or "deny",
            }
        )
    return out
