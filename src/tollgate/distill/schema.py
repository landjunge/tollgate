"""Lightweight distill schema — required fields for provider JSON."""

from __future__ import annotations

from typing import Any

# Bump when distill shape needs migration; loader defaults missing → 1
CURRENT_SCHEMA_VERSION = 1
MIN_SUPPORTED_SCHEMA_VERSION = 1

REQUIRED_TOP = ("id", "title", "distilled_at", "auth")


def validate_distill(data: dict[str, Any], *, path: str = "") -> list[str]:
    """Return list of validation errors (empty = ok)."""
    errs: list[str] = []
    if not isinstance(data, dict):
        return [f"{path}: not an object"]
    for key in REQUIRED_TOP:
        if key not in data:
            errs.append(f"{path}: missing '{key}'")
    # schema_version: optional on disk for back-compat; default 1
    sv = data.get("schema_version", 1)
    try:
        sv_i = int(sv)
    except (TypeError, ValueError):
        errs.append(f"{path}: schema_version must be int")
        sv_i = -1
    if sv_i >= 0 and sv_i < MIN_SUPPORTED_SCHEMA_VERSION:
        errs.append(
            f"{path}: schema_version {sv_i} < min supported {MIN_SUPPORTED_SCHEMA_VERSION}"
        )
    if sv_i > CURRENT_SCHEMA_VERSION:
        errs.append(
            f"{path}: schema_version {sv_i} newer than loader {CURRENT_SCHEMA_VERSION} "
            "(upgrade tollgate)"
        )
    pid = data.get("id")
    if pid is not None and not isinstance(pid, str):
        errs.append(f"{path}: id must be string")
    auth = data.get("auth")
    if auth is not None:
        if not isinstance(auth, dict):
            errs.append(f"{path}: auth must be object")
        else:
            if not auth.get("type") and not auth.get("header") and not auth.get("env"):
                errs.append(f"{path}: auth needs type/header/env")
    bu = data.get("base_urls")
    if bu is not None and not isinstance(bu, dict):
        errs.append(f"{path}: base_urls must be object")
    errors = data.get("errors")
    if errors is not None and not isinstance(errors, dict):
        errs.append(f"{path}: errors must be object")
    ops = data.get("ops")
    if ops is not None:
        if not isinstance(ops, list):
            errs.append(f"{path}: ops must be list")
        else:
            for i, op in enumerate(ops):
                if not isinstance(op, dict):
                    errs.append(f"{path}: ops[{i}] not object")
                elif not op.get("name"):
                    errs.append(f"{path}: ops[{i}] missing name")
    if str(pid or "").lower() in ("google", "gemini", "vertex"):
        hub = data.get("hub") if isinstance(data.get("hub"), dict) else {}
        if data.get("high_risk") is not True and not hub.get("high_risk"):
            if data.get("default_enabled") is True:
                errs.append(f"{path}: google-family must not default_enabled=true")
    return errs


def ensure_schema_version(data: dict[str, Any]) -> dict[str, Any]:
    """Return copy with schema_version filled for writers."""
    out = dict(data)
    out.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    return out
