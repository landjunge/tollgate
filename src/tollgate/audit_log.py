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
