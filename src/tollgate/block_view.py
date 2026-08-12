"""
Product-facing "REQUEST BLOCKED" card — the Protect Aha moment.

Attached to admit denials so demos/n8n/IF-nodes don't parse free-text only.
"""

from __future__ import annotations

from typing import Any


def build_block_card(
    *,
    reason: str,
    consumer: str = "",
    provider: str = "",
    op: str = "",
    protection: str | None = None,
    limits: dict[str, Any] | None = None,
    tool_calls_est: int = 0,
    tokens_est: int = 0,
    usd_est: float = 0.0,
) -> dict[str, Any]:
    """
    Human + machine card for a hard deny.

    Example::

        {
          "headline": "REQUEST BLOCKED",
          "consumer": "support-agent",
          "reason": "max_tool_calls",
          "protection": "max_tool_calls",
          "tool_calls": {"est": 21, "max": 20},
          "message": "🛑 REQUEST BLOCKED …"
        }
    """
    lim = limits if isinstance(limits, dict) else {}
    # check_limits nests consumer_limits → envelope
    cl = lim.get("consumer_limits") if isinstance(lim.get("consumer_limits"), dict) else {}
    prot = (
        protection
        or lim.get("protection")
        or cl.get("protection")
        or _infer_protection(reason)
        or "policy"
    )
    env = lim.get("envelope") if isinstance(lim.get("envelope"), dict) else {}
    if not env and isinstance(cl.get("envelope"), dict):
        env = cl["envelope"]
    if not env and isinstance(lim.get("limits"), dict):
        env = lim.get("limits") or {}

    max_tools = int(env.get("max_tool_calls") or lim.get("max_tool_calls") or 0)
    max_tok = int(env.get("max_tokens_request") or lim.get("max_tokens_request") or 0)
    max_usd_req = float(env.get("max_usd_request") or lim.get("max_usd_request") or 0.0)
    max_rpm = int(env.get("max_requests_minute") or lim.get("max_requests_minute") or 0)

    tool_calls_est = max(0, int(tool_calls_est or lim.get("tool_calls_est") or 0))
    tokens_est = max(0, int(tokens_est or lim.get("tokens_est") or 0))
    usd_est = float(usd_est or lim.get("request_usd_est") or lim.get("usd_est") or 0.0)

    card: dict[str, Any] = {
        "headline": "REQUEST BLOCKED",
        "emoji": "🛑",
        "consumer": (consumer or lim.get("consumer") or "")[:64] or "anonymous",
        "provider": (provider or "")[:64],
        "op": (op or "")[:64],
        "reason": str(prot),
        "protection": str(prot),
        "detail": str(reason or "")[:400],
        "frozen": bool(lim.get("frozen") or prot == "freeze"),
    }

    if max_tools > 0 or tool_calls_est > 0:
        card["tool_calls"] = {
            "est": tool_calls_est,
            "max": max_tools if max_tools > 0 else None,
        }
    if max_tok > 0 or tokens_est > 0:
        card["tokens"] = {
            "est": tokens_est,
            "max": max_tok if max_tok > 0 else None,
        }
    if max_usd_req > 0 or usd_est > 0:
        card["cost"] = {
            "est_usd": round(usd_est, 6),
            "max_usd_request": max_usd_req if max_usd_req > 0 else None,
        }
    if max_rpm > 0:
        card["rate"] = {"max_requests_minute": max_rpm}

    # One paste-friendly block for terminals / slides
    lines = [
        f"{card['emoji']} {card['headline']}",
        "",
        f"Consumer:  {card['consumer']}",
        f"Reason:    {card['reason']}",
    ]
    if card.get("tool_calls"):
        tc = card["tool_calls"]
        mx = tc.get("max")
        lines.append(
            f"Tool calls: {tc.get('est')}"
            + (f" / {mx}" if mx is not None else "")
        )
    if card.get("cost") and (card["cost"].get("est_usd") or card["cost"].get("max_usd_request")):
        c = card["cost"]
        lines.append(
            f"Est. cost: ${float(c.get('est_usd') or 0):.4f}"
            + (
                f" (max ${float(c['max_usd_request']):.4f}/req)"
                if c.get("max_usd_request")
                else ""
            )
        )
    if provider:
        lines.append(f"Provider:  {provider}")
    lines.append("")
    human = human_block_sentence(
        prot=str(prot),
        consumer=str(card["consumer"]),
        tool_calls_est=tool_calls_est,
        max_tools=max_tools,
        reason=str(reason or ""),
    )
    lines.append(human)
    card["human"] = human
    card["message"] = "\n".join(lines)
    return card


def human_block_sentence(
    *,
    prot: str,
    consumer: str = "",
    tool_calls_est: int = 0,
    max_tools: int = 0,
    reason: str = "",
) -> str:
    """One-line operator English for denials (UI / SDKs / demos)."""
    who = f"Agent «{consumer}»" if consumer and consumer != "anonymous" else "This agent"
    p = (prot or "").lower()
    if p == "freeze" or "frozen" in (reason or "").lower():
        return f"{who}: admission is frozen (kill switch). Unfreeze when the incident is over."
    if p == "max_tool_calls" or "tool_call" in (reason or "").lower():
        if max_tools > 0:
            return (
                f"{who} was blocked: tool-loop limit reached "
                f"({tool_calls_est or '?'} estimated calls, max {max_tools})."
            )
        return f"{who} was blocked to stop a runaway tool loop."
    if p == "max_usd_day" or ("max_usd_day" in (reason or "").lower()):
        return f"{who} was blocked: daily budget exceeded."
    if p == "max_usd_request":
        return f"{who} was blocked: this single request would exceed the per-task budget."
    if p == "max_usd_hour":
        return f"{who} was blocked: hourly budget would be exceeded."
    if p == "max_requests_minute":
        return f"{who} was blocked: rate limit (requests per minute) exceeded."
    if p in ("max_tokens_request", "max_tokens_day"):
        return f"{who} was blocked: token limit exceeded."
    if p == "max_calls_day":
        return f"{who} was blocked: daily request count limit exceeded."
    if p == "scope" or "scope" in (reason or "").lower():
        return f"{who} was blocked: this provider/intent/op is not allowed for this lane."
    if p == "circuit" or "circuit" in (reason or "").lower():
        return (
            "Provider is in circuit-open (recent failures). "
            "Tollgate will retry after cool-down or use a fallback if configured."
        )
    if p == "ledger":
        return "Request blocked: usage ledger is unavailable (fail-closed)."
    # fallback: clean first line of reason
    r = (reason or "").strip().split("\n")[0][:180]
    return r or f"{who} was blocked by policy."


def _infer_protection(reason: str) -> str | None:
    r = (reason or "").lower()
    for key in (
        "max_tool_calls",
        "max_requests_minute",
        "max_usd_request",
        "max_usd_hour",
        "max_usd_day",
        "max_tokens_request",
        "max_tokens_day",
        "max_calls_day",
        "freeze",
        "scope",
        "high_risk",
        "circuit",
        "ledger",
    ):
        if key in r:
            return key
    if "agent protection" in r:
        return "agent_protection"
    return None
