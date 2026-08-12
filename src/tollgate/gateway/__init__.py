"""
L4–L7 gateway core: admit → route → call → meter.

All billable traffic should enter via `gateway_call` / `admit`.
Pipeline: Prove availability → Protect → Execute → Route feedback.
"""

from tollgate.gateway.admit import admit, AdmitDecision
from tollgate.gateway.circuit import CircuitRegistry, get_circuits
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.decision import Decision, from_admit_decision
from tollgate.gateway.errors import ErrorClass, classify_http, PolicyDeny
from tollgate.gateway.entry import gateway_call

__all__ = [
    "AdmitDecision",
    "CircuitRegistry",
    "Decision",
    "ErrorClass",
    "PolicyDeny",
    "RequestClass",
    "RequestContext",
    "admit",
    "classify_http",
    "from_admit_decision",
    "gateway_call",
    "get_circuits",
]
