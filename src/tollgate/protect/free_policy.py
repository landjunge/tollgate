"""
Free / paid spend policy — single place for “may this request spend money?”

Truth was previously split across:
  router prefer_free · RequestClass.FREE · allow_paid_fallback · config.prefer_free

Call FreePolicy.resolve(...) from Route and Protect; do not re-derive ad-hoc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tollgate.gateway.context import RequestClass
from tollgate.schema import PROVIDER_CAPS


@dataclass(frozen=True)
class FreePolicy:
    """Resolved free/paid posture for one request."""

    intent: str
    prefer_free: bool
    free_only: bool  # free_llm: never spill to paid-only providers
    allow_paid_fallback: bool
    request_class: RequestClass
    may_spend: bool  # False when free_only or FREE class without paid fallback

    def is_free_capable(self, provider_id: str) -> bool:
        pid = (provider_id or "").strip().lower()
        return "free_llm" in PROVIDER_CAPS.get(pid, ())

    def may_use_high_risk(self, provider_id: str) -> tuple[bool, str]:
        """
        Protect gate: FREE class cannot use high-risk paid providers
        unless allow_paid_fallback.
        """
        if self.request_class != RequestClass.FREE and not self.free_only:
            return True, ""
        if self.allow_paid_fallback and not self.free_only:
            return True, ""
        from tollgate.cost import is_high_risk

        pid = (provider_id or "").strip().lower()
        if is_high_risk(pid) and not self.allow_paid_fallback:
            return False, (
                f"request_class=free cannot use high-risk provider {pid}"
            )
        # free_only also blocks non-free-capable even if not high_risk
        if self.free_only and not self.is_free_capable(pid):
            return False, (
                f"free_llm: paid-only provider {pid} excluded (no paid spillover)"
            )
        return True, ""

    def order_chain(self, chain: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Filter/reorder provider chain for free_llm / prefer_free.

        Returns (new_chain, tried_skip_entries).
        """
        tried: list[dict[str, Any]] = []
        chain = [str(p).strip().lower() for p in chain if p]

        if self.free_only:
            free_only = [p for p in chain if self.is_free_capable(p)]
            for pid in chain:
                if pid not in free_only:
                    tried.append(
                        {
                            "provider": pid,
                            "skip": (
                                "free_llm: paid-only provider excluded "
                                "(no paid spillover)"
                            ),
                        }
                    )
            return free_only, tried

        if self.prefer_free and self.intent == "llm":
            free_first = [p for p in chain if self.is_free_capable(p)]
            rest = [p for p in chain if p not in free_first]
            return free_first + rest, tried

        return chain, tried


def resolve(
    *,
    intent: str = "llm",
    prefer_free: bool | None = None,
    allow_paid_fallback: bool = False,
    request_class: RequestClass | None = None,
    config: dict[str, Any] | None = None,
) -> FreePolicy:
    """
    Single resolution for free/paid posture.

    - free_llm → free_only, may_spend=False (no paid spillover)
    - llm + prefer_free → FREE class for ranking/admit, may_spend=True (paid fallback OK)
    - paid_llm → may_spend=True, prefer_free=False
    """
    intent_n = (intent or "llm").strip().lower()
    cfg = config
    if cfg is None:
        try:
            from tollgate.app_config import load_config

            cfg = load_config()
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("config", e, message="free_policy resolve without config")
            cfg = {}
    cfg_pref = bool((cfg or {}).get("prefer_free", True))
    pref = cfg_pref if prefer_free is None else bool(prefer_free)
    allow_paid = bool(allow_paid_fallback)

    free_only = intent_n == "free_llm"
    if free_only:
        return FreePolicy(
            intent=intent_n,
            prefer_free=True,
            free_only=True,
            allow_paid_fallback=False,
            request_class=RequestClass.FREE,
            may_spend=False,
        )

    if intent_n == "paid_llm":
        return FreePolicy(
            intent=intent_n,
            prefer_free=False,
            free_only=False,
            allow_paid_fallback=True,
            request_class=request_class or RequestClass.INTERACTIVE,
            may_spend=True,
        )

    if request_class is not None:
        rclass = request_class
    elif pref and intent_n == "llm":
        rclass = RequestClass.FREE
    else:
        rclass = RequestClass.INTERACTIVE

    # llm with prefer_free may still fall back to paid → may_spend True
    may_spend = intent_n in ("llm", "paid_llm", "search", "tts") or allow_paid
    if rclass == RequestClass.FREE and not allow_paid and intent_n not in (
        "llm",
        "search",
        "tts",
    ):
        may_spend = False

    return FreePolicy(
        intent=intent_n,
        prefer_free=pref,
        free_only=False,
        allow_paid_fallback=allow_paid,
        request_class=rclass,
        may_spend=may_spend,
    )


def admit_free_gate(provider_id: str, ctx: Any) -> str | None:
    """
    Protect: return deny reason or None if provider OK under free policy.

    Uses ctx.request_class + ctx.allow_paid_fallback (no intent at admit).
    """
    rclass = getattr(ctx, "request_class", RequestClass.INTERACTIVE) or RequestClass.INTERACTIVE
    allow = bool(getattr(ctx, "allow_paid_fallback", False))
    pol = FreePolicy(
        intent="llm",
        prefer_free=rclass == RequestClass.FREE,
        free_only=False,
        allow_paid_fallback=allow,
        request_class=rclass,
        may_spend=allow or rclass != RequestClass.FREE,
    )
    ok, reason = pol.may_use_high_risk(provider_id)
    return None if ok else reason
