"""Pydantic validation for keys_app.json — fail loud at start, not on first call."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CostGuardModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    max_usd_day_global: float = Field(default=5.0, ge=0)
    require_explicit_enable_for_high_risk: bool = True
    high_risk_providers: list[str] = Field(default_factory=list)
    soft_warn_ratio: float = Field(default=0.8, ge=0, le=1.5)
    soft_warn_remaining_usd: float = Field(default=0.5, ge=0)
    alert_webhook_url: str = ""
    # anomaly: burn vs recent average (see cost.py)
    anomaly_burn_factor: float = Field(default=5.0, ge=1.0)
    notes: str = ""


class CircuitsModel(BaseModel):
    """Circuit-breaker defaults (OPEN cooldown + multiplicative jitter)."""

    model_config = ConfigDict(extra="allow")

    failure_threshold: int = Field(default=5, ge=1)
    cooldown_s: float = Field(default=30.0, gt=0)
    hard_cooldown_s: float = Field(default=300.0, gt=0)
    half_open_successes_needed: int = Field(default=1, ge=1)
    # Multiplicative factor on cooldown for OPEN→HALF_OPEN wake-up
    jitter_min: float = Field(default=0.8, gt=0)
    jitter_max: float = Field(default=1.2, gt=0)
    notes: str = ""

    @model_validator(mode="after")
    def _jitter_order(self) -> CircuitsModel:
        if self.jitter_min > self.jitter_max:
            # Swap rather than reject — keep desk usable
            lo, hi = self.jitter_max, self.jitter_min
            object.__setattr__(self, "jitter_min", lo)
            object.__setattr__(self, "jitter_max", hi)
        return self


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    priority: int = 50
    high_risk: bool = False
    max_calls_day: int = Field(default=0, ge=0)
    max_tokens_day: int = Field(default=0, ge=0)
    max_tokens_call: int = Field(default=0, ge=0)
    max_chars_day: int = Field(default=0, ge=0)
    max_usd_day: float = Field(default=0, ge=0)
    min_interval_ms: int = Field(default=0, ge=0)
    min_remaining: int = Field(default=0, ge=0)
    notes: str = ""


class RoutingModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    intents: dict[str, list[str]] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)


class ResponseCacheModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    ttl_s: float = Field(default=300, ge=0)
    max_entries: int = Field(default=256, ge=1)
    ops: list[str] = Field(default_factory=list)
    request_classes: list[str] = Field(default_factory=list)
    allow_interactive: bool = False
    include_consumer_in_key: bool = True


class AutoUpdateModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    interval_s: int = Field(default=300, ge=30)
    live_probes: bool = False
    refresh_models: bool = True


class KeysAppConfig(BaseModel):
    """Full keys_app.json shape (extra fields allowed for forward compat)."""

    model_config = ConfigDict(extra="allow")

    version: int = 2
    prefer_free: bool = True
    auto_failover: bool = True
    record_usage: bool = True
    cost_guard: CostGuardModel = Field(default_factory=CostGuardModel)
    circuits: CircuitsModel = Field(default_factory=CircuitsModel)
    auto_update: AutoUpdateModel = Field(default_factory=AutoUpdateModel)
    response_cache: ResponseCacheModel = Field(default_factory=ResponseCacheModel)
    routing: RoutingModel = Field(default_factory=RoutingModel)
    providers: dict[str, ProviderModel] = Field(default_factory=dict)

    @field_validator("providers", mode="before")
    @classmethod
    def _providers_dict(cls, v: Any) -> Any:
        return v if isinstance(v, dict) else {}


def validate_config_dict(cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Return (normalized_dict, errors).
    errors empty ⇒ ok; normalized is model_dump when ok.

    Backward compatible: configs **without** a ``circuits`` block are valid.
    ``CircuitsModel`` / ``KeysAppConfig`` defaults apply (jitter 0.8–1.2, 30s, …).
    Explicit ``circuits.jitter_*`` must be > 0 (enforced by CircuitsModel).
    """
    raw_in = cfg if isinstance(cfg, dict) else {}
    # Never require callers to have migrated keys_app.json for new circuit fields.
    # Missing / null circuits → pydantic default_factory(CircuitsModel).
    try:
        m = KeysAppConfig.model_validate(raw_in or {})
    except Exception as e:  # noqa: BLE001 — collect pydantic errors
        return None, [str(e)]
    # Semantic checks beyond schema
    errs: list[str] = []
    data = m.model_dump()
    cg = data.get("cost_guard") or {}
    high = {str(x).lower() for x in (cg.get("high_risk_providers") or [])}
    for pid, p in (data.get("providers") or {}).items():
        if not isinstance(p, dict):
            continue
        en = bool(p.get("enabled"))
        hr = bool(p.get("high_risk")) or pid.lower() in high
        if en and hr and float(p.get("max_usd_day") or 0) <= 0:
            errs.append(
                f"providers.{pid}: high-risk and enabled but max_usd_day unset/0 "
                "(set a tight dollar cap)"
            )
    # Circuits: only double-check when the *input* provided a circuits object.
    # Do not treat absence as error (old installs have no circuits key).
    raw_circ = raw_in.get("circuits") if isinstance(raw_in.get("circuits"), dict) else None
    if raw_circ is not None:
        circ = data.get("circuits") or {}
        try:
            jmin = float(circ["jitter_min"])
            jmax = float(circ["jitter_max"])
        except (KeyError, TypeError, ValueError):
            errs.append("circuits: jitter_min and jitter_max must be numeric and > 0")
        else:
            if jmin <= 0 or jmax <= 0:
                errs.append("circuits: jitter_min and jitter_max must be > 0")
    return data, errs


def assert_config_or_raise(cfg: dict[str, Any], *, strict: bool = False) -> list[str]:
    """
    Validate config. Returns warning strings.
    If strict and errors → raises ValueError.
    """
    _, errs = validate_config_dict(cfg)
    if strict and errs:
        raise ValueError("keys_app.json invalid:\n- " + "\n- ".join(errs))
    return errs
