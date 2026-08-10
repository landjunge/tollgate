"""
Provider research — **thin facade over distill/**.

Do not hand-edit facts here. Update:
  src/tollgate/distill/<provider>.json
  docs/keys/providers/<provider>.md  (optional long form)

Code that needs facts: `from tollgate.distill.loader import load_distill, research_view`
"""

from __future__ import annotations

from tollgate.distill.loader import (
    all_distills,
    list_distill_ids,
    load_distill,
    research_view,
)

# Stable date stamp for dashboards (max distilled_at across files)
def _researched_at() -> str:
    dates = []
    for pid in list_distill_ids():
        d = load_distill(pid).get("distilled_at")
        if d:
            dates.append(str(d))
    return max(dates) if dates else "unknown"


RESEARCHED_AT = _researched_at()


def _build_research() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for pid in list_distill_ids():
        view = research_view(pid)
        if view:
            out[pid] = view
    return out


# Lazy-compatible dict for existing imports of RESEARCH
RESEARCH: dict[str, dict] = _build_research()


def research_for(provider_id: str) -> dict:
    """Return distill-backed research view for one provider."""
    view = research_view(provider_id)
    if view:
        return view
    # legacy fallback if someone still patched RESEARCH
    return dict(RESEARCH.get((provider_id or "").strip().lower()) or {})


def reload_research() -> dict[str, dict]:
    """Call after editing distill JSON (tests / hot reload)."""
    global RESEARCH, RESEARCHED_AT
    load_distill.cache_clear()
    list_distill_ids.cache_clear()
    RESEARCH = _build_research()
    RESEARCHED_AT = _researched_at()
    return RESEARCH


__all__ = [
    "RESEARCH",
    "RESEARCHED_AT",
    "research_for",
    "reload_research",
    "load_distill",
    "all_distills",
]
