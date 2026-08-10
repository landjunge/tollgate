"""Catalog of known key families and which env vars the hub owns."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KeyFamily:
    """One logical provider / secret family."""

    id: str
    title: str
    env_keys: tuple[str, ...]
    """Primary secrets (presence = 'has key')."""
    meta_keys: tuple[str, ...] = ()
    """Non-secret config next to the key (voice id, min remaining, free-only flags)."""
    description: str = ""
    ops: tuple[str, ...] = ()
    """Special function names exposed via KeysService.call(id, op)."""
    probe: bool = False
    """Whether status() may hit the network."""


# Env names that always win from User/Key.txt when merging into .env
HUB_OWNED: frozenset[str] = frozenset(
    {
        "DEEPSEEK_API_KEY",
        "WORKER_API_KEY",
        "DEEPSEEK_MODEL",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_CHAT_IDS",
        "BRAVE_API_KEY",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_MIN_REMAINING",
        "ELEVENLABS_VOICE_ID",
        "ELEVENLABS_VOICE_NAME",
        "ELEVENLABS_KEY_NAME",
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_GNOM_CONFIG",
        "OPENROUTER_API_KEY_GNOMHUB",
        "OPENROUTER_API_KEY_HERMES",
        "OPENROUTER_FREE_ONLY",
        "NVIDIA_API_KEY",
        "MINIMAX_API_KEY",
        "MINIMAX_GROUP_ID",
        "OPENCODE_ZEN_API_KEY",
        "OPENCODE_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_AI_API_KEY",
    }
)


FAMILIES: tuple[KeyFamily, ...] = (
    KeyFamily(
        id="deepseek",
        title="DeepSeek (system LLM)",
        env_keys=("DEEPSEEK_API_KEY",),
        meta_keys=("DEEPSEEK_MODEL",),
        description="OpenAI-compatible; concurrency limits flash=2500 pro=500",
        ops=("status", "models", "research"),
        probe=True,
    ),
    KeyFamily(
        id="worker",
        title="DeepSeek workers",
        env_keys=("WORKER_API_KEY",),
        description="Same DeepSeek pool unless separate account key",
        ops=("status", "models", "research"),
        probe=True,
    ),
    KeyFamily(
        id="brave",
        title="Brave Search",
        env_keys=("BRAVE_API_KEY",),
        description="X-Subscription-Token; 1s window + monthly quota headers",
        ops=("status", "search", "quota", "research"),
        probe=True,
    ),
    KeyFamily(
        id="elevenlabs",
        title="ElevenLabs TTS",
        env_keys=("ELEVENLABS_API_KEY",),
        meta_keys=(
            "ELEVENLABS_MIN_REMAINING",
            "ELEVENLABS_VOICE_ID",
            "ELEVENLABS_VOICE_NAME",
            "ELEVENLABS_KEY_NAME",
        ),
        description="Monthly credits + hub floor ELEVENLABS_MIN_REMAINING",
        ops=("status", "budget", "subscription", "ensure_budget", "research"),
        probe=True,
    ),
    KeyFamily(
        id="openrouter",
        title="OpenRouter",
        env_keys=("OPENROUTER_API_KEY",),
        meta_keys=("OPENROUTER_FREE_ONLY",),
        description="Key chain + GET /key credits; free models :free caps",
        ops=("status", "credits", "models", "research"),
        probe=True,
    ),
    KeyFamily(
        id="nvidia",
        title="NVIDIA NIM",
        env_keys=("NVIDIA_API_KEY",),
        description="integrate.api.nvidia.com catalog; /models ≠ chat ACL",
        ops=("status", "models", "research"),
        probe=True,
    ),
    KeyFamily(
        id="minimax",
        title="MiniMax",
        env_keys=("MINIMAX_API_KEY",),
        meta_keys=("MINIMAX_GROUP_ID",),
        description="Region hosts; live probe required (2049=invalid)",
        ops=("status", "probe", "research"),
        probe=True,
    ),
    KeyFamily(
        id="opencode_zen",
        title="OpenCode Zen",
        env_keys=("OPENCODE_ZEN_API_KEY", "OPENCODE_API_KEY"),
        description="Zen gateway /zen/v1 — free models + pay-as-you-go; browser UA required",
        ops=("status", "models", "chat", "research"),
        probe=True,
    ),
    KeyFamily(
        id="telegram",
        title="Telegram bot",
        env_keys=("TELEGRAM_BOT_TOKEN",),
        meta_keys=("TELEGRAM_ALLOWED_CHAT_IDS", "TELEGRAM_HOME_CHANNEL"),
        description="Optional; getMe when live",
        ops=("status", "research"),
        probe=False,
    ),
    KeyFamily(
        id="google",
        title="Google / Gemini (HIGH COST RISK)",
        env_keys=("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"),
        description="Disabled by default — complex billing; set limits in keys_app.json",
        ops=("status", "research"),
        probe=False,
    ),
)


_BY_ID: dict[str, KeyFamily] = {f.id: f for f in FAMILIES}


def get_family(provider_id: str) -> KeyFamily | None:
    return _BY_ID.get((provider_id or "").strip().lower())


def list_families() -> list[KeyFamily]:
    return list(FAMILIES)
