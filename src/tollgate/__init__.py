"""
Tollgate — multi-consumer API key admission + provider routing.

    from tollgate import get_keys_service
    ks = get_keys_service()
    ks.dashboard()
    ks.route("free_llm")

HTTP:  uvicorn tollgate.server_v1:app
MCP:   python -m tollgate
"""

from __future__ import annotations

from tollgate.service import KeysService, get_keys_service
from tollgate.distill.loader import load_distill, research_view
from tollgate.research_notes import RESEARCH, RESEARCHED_AT, research_for

__all__ = [
    "KeysService",
    "RESEARCH",
    "RESEARCHED_AT",
    "get_keys_service",
    "load_distill",
    "research_for",
    "research_view",
]

__version__ = "0.1.0"
