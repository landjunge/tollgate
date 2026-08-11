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
        self.base_url = (
            base_url
            or os.environ.get("TOLLGATE_URL")
            or "http://127.0.0.1:8787"
        ).rstrip("/")
        self.consumer = consumer
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Consumer-Key": self.consumer,
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
        """Route + invoke chat via remote Tollgate."""
        msgs = (
            [{"role": "user", "content": messages}]
            if isinstance(messages, str)
            else list(messages or [])
        )
        pid = provider
        mid = model
        if not pid:
            r = self.route(intent, tokens_est=max(64, sum(len(m.get("content", "")) for m in msgs) // 4))
            if not r.get("ok") and not r.get("provider"):
                return r
            pid = str(r.get("provider") or "")
            mid = mid or str(r.get("model") or "")
        return self.invoke(
            pid,
            "chat",
            arguments={
                "messages": msgs,
                "model": mid,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            model=mid,
            tokens_est=max(64, sum(len(m.get("content", "")) for m in msgs) // 4 + max_tokens),
            agent_id=agent_id or self.consumer,
        )

    def budget(self, provider: str = "") -> dict[str, Any]:
        q = f"?provider={provider}" if provider else ""
        return self._request("GET", f"/v1/budget{q}")

    def providers(self, *, live: bool = False) -> dict[str, Any]:
        return self._request("GET", f"/v1/providers?live={'true' if live else 'false'}")
