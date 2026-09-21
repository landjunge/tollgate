"""G4: emit Authority Event Envelope. Never a ThreadDesk DB. Never changes admit."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = "tollgate"


def enabled() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return bool((os.environ.get("TOLLGATE_AUTHORITY_EVENTS") or "").strip())
    raw = (os.environ.get("TOLLGATE_AUTHORITY_EVENTS") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def events_path() -> Path:
    override = (os.environ.get("TOLLGATE_AUTHORITY_EVENTS_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.cwd() / "data" / "authority-events.jsonl"


def _iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(event: dict[str, Any]) -> bytes:
    body = {k: v for k, v in event.items() if k != "event_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(event)).hexdigest()


def _last_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line).get("event_hash")
            except json.JSONDecodeError:
                continue
    return str(last) if last else None


def emit(
    event_type: str,
    *,
    decision: str | None = None,
    reason_code: str | None = None,
    action: str = "",
    resource: str = "",
    actor: str = "",
    budget_ref: str | None = None,
) -> dict[str, Any] | None:
    if not enabled():
        return None
    try:
        path = events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        wf = (os.environ.get("TOLLGATE_WORKFLOW_ID") or "tollgate-local").strip()
        event: dict[str, Any] = {
            "schema_version": "1",
            "event_id": uuid.uuid4().hex[:16],
            "timestamp": _iso(),
            "trace_id": wf,
            "span_id": uuid.uuid4().hex[:8],
            "workflow_id": wf,
            "project_id": "tollgate",
            "source_tool": SOURCE,
            "event_type": event_type,
            "previous_event_hash": _last_hash(path),
            "data_labels": ["PUBLIC"],
        }
        if actor:
            event["actor"] = {"agent_id": actor, "role": "consumer"}
        if action:
            event["action"] = action
        if resource:
            event["resource"] = resource
        if decision:
            event["decision"] = decision
        if reason_code:
            event["reason_code"] = reason_code
        if budget_ref:
            event["budget_ref"] = budget_ref
        event["event_hash"] = _hash(event)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")
        return event
    except Exception:  # noqa: BLE001
        return None


def emit_from_decision(decision: Any) -> None:
    """Map a gateway Decision to envelope events. Must not raise."""
    if not enabled() or decision is None:
        return
    try:
        from tollgate.gateway.errors import ErrorClass

        allowed = bool(getattr(decision, "allowed", False))
        code = getattr(decision, "code", None)
        code_s = getattr(code, "value", None) or str(code or "")
        reason = str(getattr(decision, "reason", "") or "")
        protection = str(getattr(decision, "protection", "") or "")
        op = str(getattr(decision, "op", "") or "call")
        provider = str(getattr(decision, "provider", "") or "")
        blob = f"{reason} {protection}".lower()
        if allowed:
            kind = "budget.checked"
            dec = "ALLOW"
        elif code in (ErrorClass.BUDGET_HARD, ErrorClass.BUDGET_SOFT) or "budget" in blob:
            kind = "budget.checked"
            dec = "DENY"
        elif "loop" in blob or "tool_call" in blob:
            kind = "loop.detected"
            dec = "DENY"
        elif "frozen" in blob or "freeze" in blob:
            kind = "consumer.frozen"
            dec = "FREEZE"
        else:
            kind = "request.blocked"
            dec = "DENY"
        emit(
            kind,
            decision=dec,
            reason_code=code_s or None,
            action=op,
            resource=f"provider:{provider}" if provider else "tollgate:admit",
            budget_ref="budget:consumer" if "budget" in kind else None,
        )
    except Exception:  # noqa: BLE001
        return
