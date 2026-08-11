"""HTTP client for remote Tollgate instances (n8n, other hosts, agents)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class TollgateClient:
    """Minimal stdlib client for Tollgate /v1/*."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        consumer: str = "gnom",
        timeout: float = 120.0,
    ) -> None:
        raw = (
            base_url
            or os.environ.get("TOLLGATE_URL")
            or "http://127.0.0.1:8787"
        ).rstrip("/")
        # accept http://host:8787 or http://host:8787/v1
        if raw.endswith("/v1"):
            raw = raw[: -len("/v1")]
        self.base_url = raw.rstrip("/")
        self.consumer = consumer or os.environ.get("TOLLGATE_CONSUMER") or "gnom"
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Consumer-Key": self.consumer,
            "Authorization": f"Bearer {self.consumer}",
            "User-Agent": "TollgateClient/0.1",
        }

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {"ok": True}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body) if err_body else {}
            except json.JSONDecodeError:
                parsed = {"error": err_body or str(e)}
            if isinstance(parsed, dict):
                parsed.setdefault("ok", False)
                parsed.setdefault("status", e.code)
                return parsed
            return {"ok": False, "error": str(e), "status": e.code}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/v1/health")

    def route(
        self,
        intent: str = "llm",
        *,
        tokens_est: int = 0,
        chars_est: int = 0,
        live: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/route",
            {
                "intent": intent,
                "tokens_est": tokens_est,
                "chars_est": chars_est,
                "live": live,
            },
        )

    def invoke(
        self,
        provider: str,
        op: str = "status",
        *,
        arguments: dict[str, Any] | None = None,
        **kw: Any,
    ) -> dict[str, Any]:
        body = {
            "provider": provider,
            "op": op,
            "arguments": arguments or {},
            **{k: v for k, v in kw.items() if v is not None},
        }
        return self._request("POST", "/v1/invoke", body)

    def chat(
        self,
        messages: list[dict[str, str]] | str,
        *,
        intent: str = "llm",
        provider: str = "",
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """OpenAI-compatible chat via remote Tollgate (admit + route + meter)."""
        msgs = (
            [{"role": "user", "content": messages}]
            if isinstance(messages, str)
            else list(messages or [])
        )
        mid = model or ("tollgate/free" if intent == "free_llm" else "tollgate/auto")
        body: dict[str, Any] = {
            "model": mid,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "intent": intent,
            "prefer_free": intent == "free_llm",
            "user": agent_id or self.consumer,
        }
        if provider:
            body["provider"] = provider
        out = self._request("POST", "/v1/chat/completions", body)
        # Normalize to invoke-style for in-process callers
        if "choices" in out and out.get("ok") is not False:
            msg = (out.get("choices") or [{}])[0].get("message") or {}
            usage = out.get("usage") if isinstance(out.get("usage"), dict) else {}
            tg = out.get("tollgate") if isinstance(out.get("tollgate"), dict) else {}
            return {
                "ok": True,
                "content": str(msg.get("content") or ""),
                "model": out.get("model") or mid,
                "provider": tg.get("provider"),
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "usage": usage,
                "raw_openai": out,
            }
        if isinstance(out.get("error"), dict):
            out = dict(out)
            out.setdefault("ok", False)
            out["error"] = out["error"].get("message") or out["error"]
        return out

    def budget(self, provider: str = "") -> dict[str, Any]:
        q = f"?provider={provider}" if provider else ""
        return self._request("GET", f"/v1/budget{q}")

    def providers(self, *, live: bool = False) -> dict[str, Any]:
        return self._request("GET", f"/v1/providers?live={'true' if live else 'false'}")
