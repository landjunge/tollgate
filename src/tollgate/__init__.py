"""
Tollgate — multi-consumer API key admission + provider routing.

    from tollgate import get_keys_service, routed_chat, gateway_call
    ks = get_keys_service()
    ks.dashboard()
    routed_chat("hello", intent="free_llm")

HTTP:  uvicorn tollgate.server_v1:app  (or: tollgate serve)
MCP:   python -m tollgate
"""

from __future__ import annotations

from tollgate.chat_route import routed_chat
from tollgate.client import TollgateClient
from tollgate.distill.loader import load_distill, research_view
from tollgate.gateway.entry import gateway_call, gateway_search
from tollgate.research_notes import RESEARCH, RESEARCHED_AT, research_for
from tollgate.service import KeysService, get_keys_service

__all__ = [
    "KeysService",
    "RESEARCH",
    "RESEARCHED_AT",
    "TollgateClient",
    "gateway_call",
    "gateway_search",
    "get_keys_service",
    "load_distill",
    "research_for",
    "research_view",
    "routed_chat",
]

__version__ = "0.1.1"
