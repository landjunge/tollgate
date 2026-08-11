"""Load API secrets from Key.txt and env files (no gnom dependency)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from tollgate.paths import data_home, project_root, user_dir

_ALIASES: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "worker": "WORKER_API_KEY",
    "model": "DEEPSEEK_MODEL",
    "deepseek_model": "DEEPSEEK_MODEL",
}

_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][\w]*)\s*[=:]\s*(.+?)\s*$")

_PLACEHOLDER_MARKERS = (
    "your-",
    "your_",
    "example",
    "placeholder",
    "changeme",
    "change_me",
    "change-me",
    "insert",
    "paste",
    "xxx",
    "todo",
    "<your",
    "sk-xxx",
    "dummy",
    "test-key",
    "fake",
    "not-a-real",
)


def is_usable_api_key(value: str | None) -> bool:
    s = (value or "").strip()
    if len(s) < 3:
        return False
    low = s.lower()
    if any(m in low for m in _PLACEHOLDER_MARKERS):
        return False
    if "your" in low and "key" in low:
        return False
    if low.startswith("sk-") and low.endswith("-key") and "your" in low:
        return False
    return low not in ("sk", "sk-", "none", "null", "undefined", "changeme")


def _normalize_key(name: str) -> str:
    lower = name.strip().lower()
    if lower in _ALIASES:
        return _ALIASES[lower]
    return name.strip().upper()


def _strip_value(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.strip()


def parse_key_file(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        key = _normalize_key(m.group(1))
        val = _strip_value(m.group(2))
        if val:
            out[key] = val
    return out


def resolve_key_txt_path(root: Path | None = None) -> Path | None:
    """Prefer <data_home>/User/Key.txt, then root/User/Key.txt, then root/Key.txt."""
    candidates = [
        user_dir(root) / "Key.txt",
        data_home() / "User" / "Key.txt",
        data_home() / "Key.txt",
    ]
    if root is not None:
        candidates.extend([Path(root) / "User" / "Key.txt", Path(root) / "Key.txt"])
    # gnom compat
    gnom_ws = (os.environ.get("GNOM_WS") or "").strip()
    if gnom_ws:
        candidates.insert(0, Path(gnom_ws) / "User" / "Key.txt")
    for p in candidates:
        if p.is_file():
            return p
    return None


def ensure_env_from_key_txt(
    root: Path | None = None,
    *,
    key_filename: str = "Key.txt",
    env_filename: str = ".env",
    force: bool = False,
) -> Path | None:
    """Load Key.txt into process env; optionally write .env under data_home."""
    key_path = resolve_key_txt_path(root)
    if key_path is None:
        return None
    keys = parse_key_file(key_path.read_text(encoding="utf-8"))
    if not keys:
        return None
    for k, v in keys.items():
        if force:
            os.environ[k] = v
        else:
            os.environ.setdefault(k, v)
    env_path = data_home() / env_filename
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Tollgate — generated from Key.txt", ""]
        for k in sorted(keys):
            lines.append(f"{k}={keys[k]}")
        lines.append("")
        if force or not env_path.is_file():
            env_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return env_path


def load_keys(
    root: Path | None = None,
    *,
    env_filename: str = ".env",
    apply_environ: bool = True,
) -> dict[str, str]:
    keys: dict[str, str] = {}
    env_path = data_home() / env_filename
    if env_path.is_file():
        keys.update(parse_key_file(env_path.read_text(encoding="utf-8")))
    key_path = resolve_key_txt_path(root)
    if key_path is not None:
        keys.update(parse_key_file(key_path.read_text(encoding="utf-8")))
    for k, v in os.environ.items():
        if k.endswith("_API_KEY") or k in ("DEEPSEEK_API_KEY", "WORKER_API_KEY"):
            if v.strip():
                keys[k] = v.strip()
    if apply_environ:
        for k, v in keys.items():
            os.environ.setdefault(k, v)
    return keys
