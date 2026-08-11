"""Strip secrets from error strings before ledger / circuits / logs."""

from __future__ import annotations

import os
import re
from typing import Iterable

# common secret-ish patterns
_PATTERNS = [
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)(\S+)"),
    re.compile(r"(?i)(x-subscription-token\s*:\s*)(\S+)"),
    re.compile(r"(?i)(xi-api-key\s*:\s*)(\S+)"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([^\s\"']+)"),
    re.compile(r"(?i)(token\s*[=:]\s*)([^\s\"']{12,})"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}\b"),
    re.compile(r"\bBSA[A-Za-z0-9_\-]{10,}\b"),  # Brave-ish
    re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"),  # long opaque tokens (conservative mask)
]


def _env_secret_values() -> list[str]:
    out: list[str] = []
    for k, v in os.environ.items():
        if not v or len(v) < 8:
            continue
        if k.endswith("_API_KEY") or k.endswith("_TOKEN") or "SECRET" in k or "PASSWORD" in k:
            out.append(v)
        if k in ("OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY", "WORKER_API_KEY"):
            out.append(v)
    return out


def redact_secrets(text: str, *, extra: Iterable[str] | None = None) -> str:
    """
    Best-effort redaction for error/audit messages.
    Never trust provider error bodies to be free of echoed credentials.
    """
    if not text:
        return ""
    s = str(text)
    # exact env values first
    for secret in list(_env_secret_values()) + list(extra or []):
        if secret and secret in s:
            s = s.replace(secret, "***REDACTED***")
    for pat in _PATTERNS:
        if pat.groups >= 2:
            s = pat.sub(r"\1***REDACTED***", s)
        else:
            s = pat.sub("***REDACTED***", s)
    # truncate runaway bodies (HTML error pages etc.)
    if len(s) > 500:
        s = s[:499] + "…"
    return s
