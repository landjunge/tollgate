"""
stdio MCP server for Tollgate (keys admission + router).

Run:
  cd gnom-hub-v1 && PYTHONPATH=src .venv/bin/python -m tollgate.mcp

Cursor / Claude Desktop mcp.json example:
  {
    "mcpServers": {
      "tollgate": {
        "command": "/Users/landjunge/gnom-hub-v1/.venv/bin/python",
        "args": ["-m", "tollgate.mcp"],
        "env": {
          "PYTHONPATH": "/Users/landjunge/gnom-hub-v1/src",
          "GNOM_WS": "/Users/landjunge/WS-gnom-hub-v1"
        }
      }
    }
  }

Protocol: JSON-RPC 2.0 over stdin/stdout (MCP-compatible subset).
Methods: initialize, tools/list, tools/call, resources/list, resources/read, ping
"""

from __future__ import annotations

import json
import sys
from typing import Any

from tollgate.mcp_tools import (
    mcp_call,
    mcp_resource_read,
    mcp_resources_list,
    mcp_tools_list,
)

SERVER_NAME = "tollgate"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


def _read_message() -> dict[str, Any] | None:
    """Read one LSP/MCP-style Content-Length framed message, or a bare JSON line."""
    # Support both Content-Length framing and newline-delimited JSON
    header = b""
    while True:
        ch = sys.stdin.buffer.read(1)
        if not ch:
            return None
        header += ch
        if header.endswith(b"\r\n\r\n"):
            break
        # bare JSON line (no headers) — if we hit { first
        if header.startswith(b"{") and header.endswith(b"\n"):
            try:
                return json.loads(header.decode("utf-8"))
            except json.JSONDecodeError:
                return None
        # safety
        if len(header) > 65536:
            return None

    # parse Content-Length
    text = header.decode("utf-8", errors="replace")
    length = 0
    for line in text.split("\r\n"):
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
            except ValueError:
                length = 0
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _write_message(msg: dict[str, Any]) -> None:
    raw = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw
    )
    sys.stdout.buffer.flush()


def _ok(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    e: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }
    if data is not None:
        e["error"]["data"] = data
    return e


def dispatch(body: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one request; notifications return None (no response)."""
    req_id = body.get("id")
    method = str(body.get("method") or "").strip()
    params = body.get("params") if isinstance(body.get("params"), dict) else {}
    is_notification = "id" not in body

    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method in ("notifications/initialized", "initialized"):
        return None

    if method in ("ping",):
        return _ok(req_id, {})

    if method in ("tools/list", "tools.list"):
        return _ok(req_id, mcp_tools_list())

    if method in ("tools/call", "tools.call"):
        name = str(params.get("name") or "").strip()
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _err(req_id, -32602, "arguments must be object")
        if not name:
            return _err(req_id, -32602, "name required")
        out = mcp_call(name, arguments)
        # MCP tools/call result shape
        result = {
            "content": out.get("content")
            or [{"type": "text", "text": str(out)}],
            "isError": bool(out.get("isError")),
        }
        return _ok(req_id, result)

    if method in ("resources/list", "resources.list"):
        return _ok(req_id, mcp_resources_list())

    if method in ("resources/read", "resources.read"):
        uri = str(params.get("uri") or "").strip()
        if not uri:
            return _err(req_id, -32602, "uri required")
        out = mcp_resource_read(uri)
        if not out.get("ok"):
            return _err(req_id, -32000, out.get("error") or "read failed")
        return _ok(req_id, {"contents": out.get("contents") or []})

    if is_notification:
        return None

    return _err(req_id, -32601, f"method not found: {method}")


def main() -> None:
    try:
        from tollgate.paths import user_dir, data_home
        from tollgate.secrets import ensure_env_from_key_txt, load_keys, parse_key_file
        import os
        ensure_env_from_key_txt()
        load_keys()
        for kp in (user_dir() / "Key.txt", data_home() / "User" / "Key.txt"):
            if kp.is_file():
                for k, v in parse_key_file(kp.read_text(encoding="utf-8")).items():
                    os.environ.setdefault(k, v)
                break
    except Exception:
        pass

    sys.stderr.write(f"[{SERVER_NAME}] MCP stdio server ready\n")
    sys.stderr.flush()

    while True:
        msg = _read_message()
        if msg is None:
            break
        if not isinstance(msg, dict):
            continue
        try:
            resp = dispatch(msg)
        except Exception as e:
            resp = _err(msg.get("id"), -32603, f"internal error: {e}")
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    main()
