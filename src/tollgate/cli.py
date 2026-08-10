"""tollgate CLI entry."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="tollgate", description="Tollgate — API admission gateway")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="Run HTTP server (uvicorn)")
    sub.add_parser("mcp", help="Run MCP stdio server")
    sub.add_parser("health", help="Print local health JSON")
    args = p.parse_args(argv)
    if args.cmd == "mcp" or args.cmd is None and len(sys.argv) == 1:
        from tollgate.mcp import main as mcp_main
        mcp_main()
        return
    if args.cmd == "serve":
        import os
        import uvicorn
        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8787"))
        uvicorn.run("tollgate.server_v1:app", host=host, port=port, reload=False)
        return
    if args.cmd == "health":
        import json
        from tollgate import get_keys_service
        print(json.dumps(get_keys_service().app_status(), indent=2, default=str))
        return
    p.print_help()


if __name__ == "__main__":
    main()
