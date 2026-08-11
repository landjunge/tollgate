"""
Keys mini-app → MCP tool definitions + handlers.

Used by:
  * Hub ToolRegistry (tools_ops)
  * HTTP MCP-lite (/api/mcp/*)
  * stdio MCP server (python -m tollgate.mcp)
"""

from __future__ import annotations

import json
from typing import Any, Callable

from tollgate import get_keys_service

# name → (description, input_schema, handler)
def _ks():
    return get_keys_service()


def _json_text(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)[:24000]
    except Exception:  # noqa: BLE001
        return str(obj)[:24000]


KEYS_MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "keys_dashboard",
        "description": (
            "Keys mini-app dashboard: health grades A–F, usage totals, smart LLM route, "
            "alerts, config snapshot. Set live=true for network probes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "live": {
                    "type": "boolean",
                    "description": "Run live provider probes (Brave costs 1 cached search)",
                    "default": False,
                }
            },
        },
        "handler": lambda live=False, **_k: _ks().dashboard(live=bool(live)),
    },
    {
        "name": "keys_diagnose",
        "description": (
            "Diagnose dead keys, low credits, disabled providers; returns issues + actions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "live": {"type": "boolean", "default": True},
            },
        },
        "handler": lambda live=True, **_k: _ks().diagnose(live=bool(live)),
    },
    {
        "name": "keys_status",
        "description": (
            "Inventory of all providers with grades, or one provider if provider is set. "
            "Examples: provider=elevenlabs, provider=opencode_zen."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "Optional provider id (deepseek|brave|elevenlabs|opencode_zen|…)",
                },
                "live": {"type": "boolean", "default": False},
            },
        },
        "handler": lambda provider="", live=False, **_k: (
            _ks().status(str(provider), live=bool(live))
            if str(provider or "").strip()
            else _ks().inventory(live=bool(live))
        ),
    },
    {
        "name": "keys_route",
        "description": (
            "Smart route for an intent under limits + failover. "
            "intent: llm|free_llm|paid_llm|search|tts|media. "
            "Returns provider, model, base_url, remaining limits, fallbacks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["llm", "free_llm", "paid_llm", "search", "tts", "media", "any"],
                    "default": "llm",
                },
                "tokens_est": {
                    "type": "integer",
                    "description": "Estimated tokens for limit check",
                    "default": 0,
                },
                "chars_est": {
                    "type": "integer",
                    "description": "Estimated chars (TTS)",
                    "default": 0,
                },
                "live": {"type": "boolean", "default": False},
            },
        },
        "handler": lambda intent="llm", tokens_est=0, chars_est=0, live=False, **_k: _ks().route(
            str(intent or "llm"),
            tokens_est=int(tokens_est or 0),
            chars_est=int(chars_est or 0),
            live=bool(live),
        ),
    },
    {
        "name": "keys_preflight",
        "description": (
            "May I spend? Preflight for intent tts|search|free_llm|llm with optional cost."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "default": "any"},
                "cost": {"type": "integer", "default": 0},
                "live": {"type": "boolean", "default": False},
            },
        },
        "handler": lambda intent="any", cost=0, live=False, **_k: _ks().preflight(
            str(intent or "any"), cost=int(cost or 0), live=bool(live)
        ),
    },
    {
        "name": "keys_usage",
        "description": "Today's token/call/char ledger (keys_usage.json).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda **_k: _ks().usage(),
    },
    {
        "name": "keys_control",
        "description": (
            "Control plane pane: provider health, consumer burn, resilience, "
            "attention feed, chaos status. Protect · Route · Prove."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda **_k: __import__(
            "tollgate.control_plane", fromlist=["control_snapshot"]
        ).control_snapshot(),
    },
    {
        "name": "keys_resilience",
        "description": (
            "AI Resilience Score 0–100 + policy compliance + warnings. "
            "Prove pillar for CTOs."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda **_k: __import__(
            "tollgate.resilience", fromlist=["resilience_score"]
        ).resilience_score(),
    },
    {
        "name": "keys_chaos_status",
        "description": (
            "Active chaos injects, gradual recovery, last failover test report + history."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda **_k: __import__(
            "tollgate.chaos", fromlist=["status"]
        ).status(),
    },
    {
        "name": "keys_agent_protect_check",
        "description": (
            "Dry-run agent protection for a consumer lane: would this request be allowed? "
            "Pass tokens_est and tool_calls_est (loop depth)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "consumer": {
                    "type": "string",
                    "description": "Consumer/agent id (default gnom)",
                    "default": "gnom",
                },
                "tokens_est": {"type": "integer", "default": 0},
                "tool_calls_est": {
                    "type": "integer",
                    "default": 0,
                    "description": "Tool steps this turn (max_tool_calls envelope)",
                },
                "usd_est": {"type": "number", "default": 0},
            },
        },
        "handler": lambda consumer="gnom", tokens_est=0, tool_calls_est=0, usd_est=0, **_k: __import__(
            "tollgate.limits", fromlist=["check_consumer_limits"]
        ).check_consumer_limits(
            str(consumer or "gnom"),
            tokens_est=int(tokens_est or 0),
            tool_calls_est=int(tool_calls_est or 0),
            usd_est=float(usd_est or 0),
        ),
    },
    {
        "name": "keys_desk_status",
        "description": (
            "Compact desk status: freeze, resilience score, spend, attention. "
            "format=json|text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["json", "text"],
                    "default": "json",
                },
            },
        },
        "handler": lambda format="json", **_k: (
            {
                "ok": True,
                "format": "text",
                "text": __import__(
                    "tollgate.status", fromlist=["format_status_text"]
                ).format_status_text(),
            }
            if str(format or "json").lower() in ("text", "txt", "md")
            else __import__("tollgate.status", fromlist=["desk_status"]).desk_status()
        ),
    },
    {
        "name": "keys_freeze",
        "description": (
            "Global admission kill switch. action=status|on|off. "
            "When frozen, all billable traffic is denied (Protect emergency)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "on", "off"],
                    "default": "status",
                },
                "reason": {"type": "string", "default": ""},
            },
        },
        "handler": lambda action="status", reason="", **_k: (
            __import__("tollgate.freeze", fromlist=["freeze_status"]).freeze_status()
            if str(action or "status") == "status"
            else __import__("tollgate.freeze", fromlist=["set_frozen"]).set_frozen(
                str(action or "") == "on",
                reason=str(reason or ""),
                by="mcp",
            )
        ),
    },
    {
        "name": "keys_circuits",
        "description": "List or reset circuit breakers. action=list|reset, optional provider, all=true.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "reset"],
                    "default": "list",
                },
                "provider": {"type": "string", "default": ""},
                "all": {"type": "boolean", "default": False},
            },
        },
        "handler": lambda action="list", provider="", all=False, **_k: (
            {
                "ok": True,
                "circuits": __import__(
                    "tollgate.gateway.circuit", fromlist=["get_circuits"]
                )
                .get_circuits()
                .snapshot(),
            }
            if str(action or "list") == "list"
            else __import__(
                "tollgate.gateway.circuit", fromlist=["reset_circuits"]
            ).reset_circuits(
                str(provider or ""),
                all_circuits=bool(all),
            )
        ),
    },
    {
        "name": "keys_alert_test",
        "description": (
            "Force-send webhook_test to TOLLGATE_ALERT_WEBHOOK / "
            "cost_guard.alert_webhook_url. Or list event catalog (action=events)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["test", "events"],
                    "default": "test",
                },
                "message": {"type": "string", "default": "tollgate alert test"},
            },
        },
        "handler": lambda action="test", message="tollgate alert test", **_k: (
            __import__("tollgate.alerts", fromlist=["event_catalog"]).event_catalog()
            if str(action or "test") == "events"
            else __import__("tollgate.alerts", fromlist=["test_webhook"]).test_webhook(
                message=str(message or "tollgate alert test")
            )
        ),
    },
    {
        "name": "keys_report",
        "description": (
            "Daily operator report: Protect · Route · Prove evidence "
            "(spend, denies, resilience, last chaos). format=md|json."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["json", "md", "markdown"],
                    "default": "json",
                },
            },
        },
        "handler": lambda format="json", **_k: (
            {
                "ok": True,
                "format": "md",
                "markdown": __import__(
                    "tollgate.report", fromlist=["format_report_markdown"]
                ).format_report_markdown(),
            }
            if str(format or "json").lower() in ("md", "markdown", "text")
            else __import__("tollgate.report", fromlist=["build_report"]).build_report()
        ),
    },
    {
        "name": "keys_audit",
        "description": (
            "Query audit trail: admit denies, usage events. "
            "Who was stopped and why (Protect evidence). summary=true for aggregates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 40},
                "event": {
                    "type": "string",
                    "description": "admit_deny | usage | empty for all",
                    "default": "",
                },
                "consumer": {"type": "string", "default": ""},
                "provider": {"type": "string", "default": ""},
                "summary": {
                    "type": "boolean",
                    "default": False,
                    "description": "Return aggregates instead of event rows",
                },
            },
        },
        "handler": lambda limit=40, event="", consumer="", provider="", summary=False, **_k: (
            __import__("tollgate.audit_log", fromlist=["audit_summary"]).audit_summary()
            if summary
            else __import__("tollgate.audit_log", fromlist=["query_audit"]).query_audit(
                limit=int(limit or 40),
                event=str(event or ""),
                consumer=str(consumer or ""),
                provider=str(provider or ""),
            )
        ),
    },

    {
        "name": "keys_config_get",
        "description": "Read keys_app.json (limits, routing, auto_update, enabled providers).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda **_k: _ks().get_config(),
    },
    {
        "name": "keys_config_patch",
        "description": (
            "Deep-merge patch into keys_app.json. "
            'Example: {"providers":{"brave":{"max_calls_day":50}},"prefer_free":true}'
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "object",
                    "description": "Partial config object to merge",
                },
            },
            "required": ["patch"],
        },
        "handler": lambda patch=None, **_k: _ks().set_config(
            patch
            if isinstance(patch, dict)
            else (
                {k: v for k, v in _k.items() if k not in ("patch",)}
                if _k
                else {}
            )
        ),
    },
    {
        "name": "keys_limits",
        "description": "Remaining daily call/token/char budget for a provider.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "tokens_est": {"type": "integer", "default": 0},
                "chars_est": {"type": "integer", "default": 0},
            },
            "required": ["provider"],
        },
        "handler": lambda provider, tokens_est=0, chars_est=0, **_k: _ks().check_provider_limits(
            str(provider), tokens_est=int(tokens_est or 0), chars_est=int(chars_est or 0)
        ),
    },
    {
        "name": "keys_auto_update",
        "description": "Background provider refresh. action: status|start|stop|once",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "start", "stop", "once"],
                    "default": "status",
                }
            },
        },
        "handler": lambda action="status", **_k: _ks().auto_update(str(action or "status")),
    },
    {
        "name": "keys_call",
        "description": (
            "Generic keys op. provider + op. "
            "Providers: elevenlabs, brave, opencode_zen, openrouter, deepseek, nvidia, minimax. "
            "Ops: budget, search, chat, credits, models, quota, research, status. "
            "Meta provider=keys: dashboard, diagnose, route, usage, config."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string"},
                "op": {"type": "string", "default": "status"},
                "query": {"type": "string"},
                "message": {"type": "string"},
                "model": {"type": "string"},
                "intent": {"type": "string"},
                "cost": {"type": "integer"},
                "count": {"type": "integer"},
                "tokens_est": {"type": "integer"},
                "chars_est": {"type": "integer"},
                "live": {"type": "boolean"},
                "force": {"type": "boolean"},
                "patch": {"type": "object"},
                "action": {"type": "string"},
            },
            "required": ["provider"],
        },
        "handler": lambda provider="keys", op="status", **kw: _keys_call_dispatch(
            str(provider or "keys"), str(op or "status"), **kw
        ),
    },
    {
        "name": "keys_web_search",
        "description": (
            "Web search via Brave (counts against keys limits + Brave quota). "
            "Uses keys module rate headers and daily max_calls_day."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer", "default": 5},
                "country": {"type": "string", "default": "DE"},
                "search_lang": {"type": "string", "default": "de"},
            },
            "required": ["query"],
        },
        "handler": lambda query, count=5, country="DE", search_lang="de", **_k: _ks().call(
            "brave",
            "search",
            query=str(query),
            count=int(count or 5),
            country=str(country or "DE"),
            search_lang=str(search_lang or "de"),
        ),
    },
    {
        "name": "keys_elevenlabs_budget",
        "description": (
            "ElevenLabs credit floor check (ELEVENLABS_MIN_REMAINING / keys_app min_remaining). "
            "cost = estimated characters for next TTS."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"cost": {"type": "integer", "default": 0}},
        },
        "handler": lambda cost=0, **_k: _ks().call("elevenlabs", "budget", cost=int(cost or 0)),
    },
    {
        "name": "keys_zen_chat",
        "description": (
            "Chat via OpenCode Zen free/paid models (counts tokens). "
            "Default model deepseek-v4-flash-free (cost 0)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "model": {
                    "type": "string",
                    "default": "deepseek-v4-flash-free",
                    "description": "e.g. deepseek-v4-flash-free, big-pickle, mimo-v2.5-free",
                },
                "max_tokens": {"type": "integer", "default": 256},
            },
            "required": ["message"],
        },
        "handler": lambda message, model="deepseek-v4-flash-free", max_tokens=256, **_k: _ks().call(
            "opencode_zen",
            "chat",
            message=str(message),
            model=str(model or "deepseek-v4-flash-free"),
            max_tokens=int(max_tokens or 256),
        ),
    },
    {
        "name": "keys_research",
        "description": "Offline research notes for a provider (auth, limits, gotchas) or all.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "Optional provider id; omit for all",
                }
            },
        },
        "handler": lambda provider="", **_k: _ks().research(
            str(provider).strip() or None
        ),
    },
]


def _keys_call_dispatch(provider: str, op: str, **kw: Any) -> dict[str, Any]:
    """Map MCP keys_call args into KeysService.call."""
    ks = _ks()
    oname = (op or "status").strip().lower()
    pid = (provider or "keys").strip().lower()
    args: dict[str, Any] = {}
    # pass through known kwargs
    for k in (
        "query",
        "message",
        "model",
        "intent",
        "cost",
        "count",
        "tokens_est",
        "chars_est",
        "live",
        "force",
        "patch",
        "action",
        "prefer_free",
        "max_tokens",
    ):
        if k in kw and kw[k] is not None and kw[k] != "":
            args[k] = kw[k]
    return ks.call(pid, oname, **args)


def mcp_tools_list() -> dict[str, Any]:
    """MCP tools/list body for keys-only server."""
    return {
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t.get("inputSchema")
                or {"type": "object", "properties": {}},
            }
            for t in KEYS_MCP_TOOLS
        ]
    }


def mcp_tool_handlers() -> dict[str, Callable[..., Any]]:
    return {t["name"]: t["handler"] for t in KEYS_MCP_TOOLS}


def mcp_call(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """MCP tools/call-shaped result for a keys tool."""
    handlers = mcp_tool_handlers()
    nm = (name or "").strip()
    if nm not in handlers:
        return {
            "ok": False,
            "isError": True,
            "content": [{"type": "text", "text": f"unknown keys tool: {nm}"}],
            "error": {"message": f"unknown keys tool: {nm}"},
        }
    args = arguments if isinstance(arguments, dict) else {}
    try:
        raw = handlers[nm](**args)
    except TypeError as e:
        return {
            "ok": False,
            "isError": True,
            "content": [{"type": "text", "text": f"bad args: {e}"}],
            "error": {"message": str(e)},
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "isError": True,
            "content": [{"type": "text", "text": str(e)}],
            "error": {"message": str(e)},
        }

    if isinstance(raw, dict) and raw.get("ok") is False:
        msg = str(raw.get("error") or "failed")
        return {
            "ok": False,
            "isError": True,
            "content": [{"type": "text", "text": msg}],
            "error": {"message": msg},
            "result": raw,
        }

    return {
        "ok": True,
        "isError": False,
        "content": [{"type": "text", "text": _json_text(raw)}],
        "result": raw,
    }


def mcp_resources_list() -> dict[str, Any]:
    """Optional MCP resources for config + usage."""
    return {
        "resources": [
            {
                "uri": "keys://app/config",
                "name": "keys_app.json",
                "description": "Keys mini-app config (limits, routing, auto_update)",
                "mimeType": "application/json",
            },
            {
                "uri": "keys://app/usage",
                "name": "keys_usage.json",
                "description": "Today token/call ledger",
                "mimeType": "application/json",
            },
            {
                "uri": "keys://app/dashboard",
                "name": "dashboard",
                "description": "Live dashboard snapshot (no network probes)",
                "mimeType": "application/json",
            },
            {
                "uri": "keys://app/research",
                "name": "research_notes",
                "description": "Offline provider research notes",
                "mimeType": "application/json",
            },
        ]
    }


def mcp_resource_read(uri: str) -> dict[str, Any]:
    ks = _ks()
    u = (uri or "").strip()
    if u == "keys://app/config":
        data = ks.get_config()
    elif u == "keys://app/usage":
        data = ks.usage()
    elif u == "keys://app/dashboard":
        data = ks.dashboard(live=False)
    elif u == "keys://app/research":
        data = ks.research()
    else:
        return {
            "ok": False,
            "error": f"unknown resource: {uri}",
            "contents": [],
        }
    text = _json_text(data)
    return {
        "ok": True,
        "contents": [
            {
                "uri": u,
                "mimeType": "application/json",
                "text": text,
            }
        ],
    }


def register_keys_mcp_on_registry(registry: Any) -> list[str]:
    """
    Register all keys MCP tools on a ToolRegistry (plugin=keys).

    Returns list of registered names.
    """
    from tollgate.registry import ToolSpec

    names: list[str] = []
    for t in KEYS_MCP_TOOLS:
        name = t["name"]
        registry.register(
            ToolSpec(
                name=name,
                description=t["description"],
                handler=t["handler"],
                input_schema=t.get("inputSchema")
                or {"type": "object", "properties": {}},
                plugin="keys",
                tags=("keys", "mcp"),
            )
        )
        names.append(name)
    return names
