"""Prometheus text exposition from ledger + circuits (no extra deps)."""

from __future__ import annotations

from typing import Any


def _esc_label(v: str) -> str:
    return (
        str(v)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def _line(name: str, value: float | int, labels: dict[str, str] | None = None) -> str:
    if labels:
        parts = ",".join(f'{k}="{_esc_label(v)}"' for k, v in sorted(labels.items()))
        return f"{name}{{{parts}}} {value}"
    return f"{name} {value}"


def render_prometheus() -> str:
    """Build Prometheus text format from current process state."""
    from tollgate.consumers import auth_status
    from tollgate.cost import high_risk_ids, usd_used_today
    from tollgate.gateway.circuit import get_circuits
    from tollgate.paths import path_snapshot
    from tollgate.response_cache import stats as cache_stats
    from tollgate.usage_ledger import load_usage

    lines: list[str] = [
        "# HELP tollgate_up Always 1 when process serves metrics.",
        "# TYPE tollgate_up gauge",
        "tollgate_up 1",
    ]

    usage = load_usage()
    tot = usage.get("totals") or {}
    day = str(usage.get("day") or "")

    lines += [
        "# HELP tollgate_usage_calls_total Calls recorded today (ledger).",
        "# TYPE tollgate_usage_calls_total gauge",
        _line("tollgate_usage_calls_total", int(tot.get("calls") or 0), {"day": day}),
        "# HELP tollgate_usage_tokens_total Tokens recorded today.",
        "# TYPE tollgate_usage_tokens_total gauge",
        _line("tollgate_usage_tokens_total", int(tot.get("tokens") or 0), {"day": day}),
        "# HELP tollgate_usage_usd_total Estimated USD recorded today.",
        "# TYPE tollgate_usage_usd_total gauge",
        _line("tollgate_usage_usd_total", float(tot.get("usd") or 0.0), {"day": day}),
        "# HELP tollgate_usage_errors_total Errors recorded today.",
        "# TYPE tollgate_usage_errors_total gauge",
        _line("tollgate_usage_errors_total", int(tot.get("errors") or 0), {"day": day}),
    ]

    providers = usage.get("providers") or {}
    if isinstance(providers, dict):
        lines += [
            "# HELP tollgate_provider_calls_total Per-provider calls today.",
            "# TYPE tollgate_provider_calls_total gauge",
        ]
        for pid, p in providers.items():
            if not isinstance(p, dict):
                continue
            labels = {"provider": str(pid), "day": day}
            lines.append(_line("tollgate_provider_calls_total", int(p.get("calls") or 0), labels))
        lines += [
            "# HELP tollgate_provider_usd_total Per-provider estimated USD today.",
            "# TYPE tollgate_provider_usd_total gauge",
        ]
        for pid, p in providers.items():
            if not isinstance(p, dict):
                continue
            labels = {"provider": str(pid), "day": day}
            lines.append(
                _line("tollgate_provider_usd_total", float(p.get("usd") or 0.0), labels)
            )

    consumers = usage.get("consumers") or {}
    if isinstance(consumers, dict) and consumers:
        lines += [
            "# HELP tollgate_consumer_calls_total Per-consumer calls today.",
            "# TYPE tollgate_consumer_calls_total gauge",
        ]
        for cid, c in consumers.items():
            if not isinstance(c, dict):
                continue
            labels = {"consumer": str(cid), "day": day}
            lines.append(
                _line("tollgate_consumer_calls_total", int(c.get("calls") or 0), labels)
            )
        lines += [
            "# HELP tollgate_consumer_usd_total Per-consumer estimated USD today.",
            "# TYPE tollgate_consumer_usd_total gauge",
        ]
        for cid, c in consumers.items():
            if not isinstance(c, dict):
                continue
            labels = {"consumer": str(cid), "day": day}
            lines.append(
                _line("tollgate_consumer_usd_total", float(c.get("usd") or 0.0), labels)
            )

    # circuits: 0=closed 1=half_open 2=open
    state_map = {"closed": 0, "half_open": 1, "open": 2}
    lines += [
        "# HELP tollgate_circuit_state Circuit state (0 closed, 1 half_open, 2 open).",
        "# TYPE tollgate_circuit_state gauge",
        "# HELP tollgate_circuit_failures Failure counter on circuit.",
        "# TYPE tollgate_circuit_failures gauge",
    ]
    try:
        snap = get_circuits().snapshot()
        for row in snap or []:
            if not isinstance(row, dict):
                continue
            # Circuit.as_dict uses key = "provider|model|key_ref"
            key = str(row.get("key") or "")
            parts = key.split("|")
            prov = parts[0] if parts else "unknown"
            model = parts[1] if len(parts) > 1 else "*"
            st = str(row.get("state") or "closed")
            labels = {"provider": prov, "model": model}
            lines.append(
                _line("tollgate_circuit_state", state_map.get(st, -1), labels)
            )
            lines.append(
                _line(
                    "tollgate_circuit_failures",
                    int(row.get("failures") or 0),
                    labels,
                )
            )
    except Exception:  # noqa: BLE001
        pass

    # auth / portable / cache
    try:
        auth = auth_status()
        lines += [
            "# HELP tollgate_auth_required 1 if consumer secrets required.",
            "# TYPE tollgate_auth_required gauge",
            _line("tollgate_auth_required", 1 if auth.get("required") else 0),
            "# HELP tollgate_consumers Number of configured consumers.",
            "# TYPE tollgate_consumers gauge",
            _line("tollgate_consumers", int(auth.get("consumers_n") or 0)),
        ]
    except Exception:  # noqa: BLE001
        pass

    try:
        ps = path_snapshot()
        lines += [
            "# HELP tollgate_portable 1 if portable/USB mode.",
            "# TYPE tollgate_portable gauge",
            _line("tollgate_portable", 1 if ps.get("portable") else 0),
            "# HELP tollgate_usb 1 if on removable mount.",
            "# TYPE tollgate_usb gauge",
            _line("tollgate_usb", 1 if ps.get("usb") else 0),
        ]
    except Exception:  # noqa: BLE001
        pass

    try:
        cs = cache_stats()
        lines += [
            "# HELP tollgate_cache_entries Response cache entries.",
            "# TYPE tollgate_cache_entries gauge",
            _line("tollgate_cache_entries", int(cs.get("entries") or 0)),
            "# HELP tollgate_cache_enabled 1 if response cache on.",
            "# TYPE tollgate_cache_enabled gauge",
            _line("tollgate_cache_enabled", 1 if cs.get("enabled") else 0),
        ]
    except Exception:  # noqa: BLE001
        pass

    try:
        lines += [
            "# HELP tollgate_high_risk_providers Count of high-risk provider ids.",
            "# TYPE tollgate_high_risk_providers gauge",
            _line("tollgate_high_risk_providers", len(high_risk_ids())),
            "# HELP tollgate_usd_used_global Global estimated USD used today.",
            "# TYPE tollgate_usd_used_global gauge",
            _line("tollgate_usd_used_global", float(usd_used_today(None))),
        ]
    except Exception:  # noqa: BLE001
        pass

    lines.append("")  # trailing newline
    return "\n".join(lines)
