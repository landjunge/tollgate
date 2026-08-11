"""
Hard boundary: Tollgate stores operational state only — never agent memory.

Allowed in ledger meta / events: short technical fields.
Forbidden: free text that could become chat/transcript/project memory.
"""

from __future__ import annotations

from typing import Any

# Fields permitted on ledger last_meta / audit side-channels
META_ALLOWLIST: frozenset[str] = frozenset(
    {
        "model",
        "consumer",
        "agent_id",
        "job_id",
        "session_id",
        "request_class",
        "error_class",
        "cache_hit",
        "soft_degrade",
        "provider",
        "op",
        "status",
        "grade",
    }
)

# Explicit deny (defense in depth — even if not in allowlist)
META_DENYLIST: frozenset[str] = frozenset(
    {
        "content",
        "message",
        "messages",
        "prompt",
        "system",
        "transcript",
        "text",
        "body",
        "arguments",
        "query",
        "q",
        "input",
        "output",
        "completion",
        "response",
        "wish",
        "wishes",
        "memory",
        "file",
        "files",
        "path",
        "project",
        "user_text",
        "assistant",
        "history",
        "raw",
        "payload",
        # note: "chat" is a valid op name in by_op — not forbidden as a counter key
    }
)


def sanitize_meta(meta: dict[str, Any] | None, *, max_str: int = 128) -> dict[str, Any]:
    """
    Keep only operational short fields. Drop anything that looks like memory/content.
    """
    if not meta or not isinstance(meta, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in meta.items():
        key = str(k).strip().lower()
        if key in META_DENYLIST:
            continue
        if key not in META_ALLOWLIST:
            continue
        if isinstance(v, bool) or v is None:
            out[key] = v
        elif isinstance(v, (int, float)):
            out[key] = v
        elif isinstance(v, str):
            s = v.strip()
            if len(s) > max_str:
                s = s[: max_str - 1] + "…"
            # reject multi-line / obviously conversational blobs
            if "\n" in s or len(s.split()) > 24:
                continue
            out[key] = s
        # no nested dicts/lists (would re-open content smuggling)
    return out


def assert_no_memory_fields(obj: dict[str, Any], *, path: str = "ledger") -> list[str]:
    """
    Return errors if forbidden keys appear in ledger meta slots.

    Op names under by_op (e.g. ``chat``) are counters, not memory — only
    ``last_meta`` and unexpected free-text containers are checked.
    """
    errs: list[str] = []
    if not isinstance(obj, dict):
        return [f"{path}: not an object"]

    # top-level smuggling
    for k in obj:
        if str(k).lower() in META_DENYLIST:
            errs.append(f"{path}.{k}: forbidden at root")

    providers = obj.get("providers") or {}
    if isinstance(providers, dict):
        for pid, p in providers.items():
            if not isinstance(p, dict):
                continue
            for k in p:
                if str(k).lower() in META_DENYLIST:
                    errs.append(f"{path}.providers.{pid}.{k}: forbidden")
            meta = p.get("last_meta")
            if isinstance(meta, dict):
                for k, v in meta.items():
                    kl = str(k).lower()
                    if kl in META_DENYLIST or kl not in META_ALLOWLIST:
                        errs.append(f"{path}.providers.{pid}.last_meta.{k}: not allowed")
                    if isinstance(v, str) and ("\n" in v or len(v) > 200):
                        errs.append(f"{path}.providers.{pid}.last_meta.{k}: too long/multiline")
    return errs
