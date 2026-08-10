"""Error taxonomy — different failures need different next actions."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorClass(str, Enum):
    OK = "OK"
    AUTH_DEAD = "AUTH_DEAD"  # mark key dead; never rotate-loop
    RATE_LIMIT = "RATE_LIMIT"  # cooldown + optional failover
    PROVIDER_DOWN = "PROVIDER_DOWN"  # 5xx / network
    EDGE_BLOCK = "EDGE_BLOCK"  # Cloudflare 1010/403 bot — not a key problem
    EMPTY_COMPLETION = "EMPTY_COMPLETION"
    POLICY_DENY = "POLICY_DENY"  # local policy
    BUDGET_HARD = "BUDGET_HARD"
    BUDGET_SOFT = "BUDGET_SOFT"
    UNKNOWN = "UNKNOWN"


class PolicyDeny(Exception):
    """Hard admission deny — must not call provider HTTP."""

    def __init__(self, message: str, *, code: ErrorClass = ErrorClass.POLICY_DENY, extra: dict | None = None):
        super().__init__(message)
        self.code = code
        self.extra = extra or {}


def classify_http(status: int | None, body: Any = None, *, headers: dict | None = None) -> ErrorClass:
    """Map HTTP outcome → taxonomy."""
    if status is None:
        return ErrorClass.PROVIDER_DOWN
    if status in (401, 403):
        # Cloudflare bot block often 403 with cf error page
        text = str(body or "").lower()
        if "cloudflare" in text or "error 1010" in text or "1010" in text:
            return ErrorClass.EDGE_BLOCK
        if status == 401:
            return ErrorClass.AUTH_DEAD
        # 403 may be permissions (EL scopes) — treat as AUTH_DEAD for key policy
        return ErrorClass.AUTH_DEAD
    if status == 429:
        return ErrorClass.RATE_LIMIT
    if status >= 500:
        return ErrorClass.PROVIDER_DOWN
    if status == 402:
        return ErrorClass.BUDGET_HARD  # provider-side insufficient credits
    if 200 <= status < 300:
        return ErrorClass.OK
    return ErrorClass.UNKNOWN


def classify_result(result: dict[str, Any] | None) -> ErrorClass:
    if not isinstance(result, dict):
        return ErrorClass.UNKNOWN
    if result.get("ok") is True:
        return ErrorClass.OK
    err = str(result.get("error") or "").lower()
    status = result.get("status")
    if status is not None:
        return classify_http(int(status) if status else None, err)
    if "high risk" in err or "disabled" in err or "limit" in err or "budget" in err or "max_" in err:
        if "usd" in err or "budget" in err:
            return ErrorClass.BUDGET_HARD
        return ErrorClass.POLICY_DENY
    if "401" in err or "invalid api key" in err or "unauthorized" in err:
        return ErrorClass.AUTH_DEAD
    if "429" in err or "rate" in err:
        return ErrorClass.RATE_LIMIT
    if "1010" in err or "cloudflare" in err:
        return ErrorClass.EDGE_BLOCK
    return ErrorClass.UNKNOWN
