"""
stdio MCP server for Tollgate (keys admission + router).

Portable / USB::

  export TOLLGATE_HOME=…/WS-tollgate   # or TOLLGATE_PORTABLE=1
  python -m tollgate

Cursor mcp.json (no absolute machine paths)::

  {
    "mcpServers": {
      "tollgate": {
        "command": "python",
        "args": ["-m", "tollgate"],
        "env": { "TOLLGATE_PORTABLE": "1" }
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
SERVER_VERSION = "0.1.1"
PROTOCOL_VERSION = "2024-11-05"


def _ok(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _read_message() -> dict[str, Any] | None:
    """Read one JSON-RPC message (Content-Length framing or bare line)."""
    header = b""
    while True:
        ch = sys.stdin.buffer.read(1)
        if not ch:
            return None
        header += ch
        if header.endswith(b"\r\n\r\n") or header.endswith(b"\n\n"):
            break
        # bare JSON line (no Content-Length)
        if header.endswith(b"\n") and b"Content-Length" not in header:
            line = header.decode("utf-8", errors="replace").strip()
            if not line:
                header = b""
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None
    # parse Content-Length
    text = header.decode("utf-8", errors="replace")
    length = 0
    for line in text.splitlines():
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
            except ValueError:
                length = 0
    body = sys.stdin.buffer.read(length) if length else b""
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


def dispatch(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method") or ""
    req_id = msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    is_notification = "id" not in msg

    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return _ok(req_id, {})
    if method == "tools/list":
        return _ok(req_id, {"tools": mcp_tools_list()})
    if method == "tools/call":
        name = str(params.get("name") or "")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        out = mcp_call(name, arguments)
        if not out.get("ok"):
            # MCP tools/call still returns content; surface error text
            text = str(out.get("error") or out)
        else:
            text = json.dumps(out, ensure_ascii=False, default=str)
        return _ok(
            req_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": not out.get("ok", True),
            },
        )
    if method == "resources/list":
        return _ok(req_id, {"resources": mcp_resources_list()})
    if method == "resources/read":
        uri = str(params.get("uri") or "")
        out = mcp_resource_read(uri)
        if not out.get("ok"):
            return _err(req_id, -32000, out.get("error") or "read failed")
        return _ok(req_id, {"contents": out.get("contents") or []})

    if is_notification:
        return None

    return _err(req_id, -32601, f"method not found: {method}")


def main() -> None:
    try:
        import os

        from tollgate.paths import data_home, pin_data_home_env, user_dir
        from tollgate.secrets import ensure_env_from_key_txt, load_keys, parse_key_file

        pin_data_home_env()
        ensure_env_from_key_txt()
        load_keys()
        for kp in (user_dir() / "Key.txt", data_home() / "User" / "Key.txt"):
            if kp.is_file():
                for k, v in parse_key_file(kp.read_text(encoding="utf-8")).items():
                    os.environ.setdefault(k, v)
                break
    except Exception:  # noqa: BLE001
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
        except Exception as e:  # noqa: BLE001
            resp = _err(msg.get("id"), -32603, f"internal error: {e}")
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    main()
