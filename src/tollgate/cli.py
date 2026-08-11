"""tollgate CLI entry."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="tollgate", description="Tollgate — API admission gateway")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="Run HTTP server (uvicorn)")
    sub.add_parser("mcp", help="Run MCP stdio server")
    sub.add_parser("health", help="Print local health JSON (paths + auth mode)")
    sub.add_parser("paths", help="Print portable path snapshot")
    cadd = sub.add_parser("consumer-add", help="Add HTTP consumer (id:secret)")
    cadd.add_argument("id", help="consumer id (e.g. n8n, gnom)")
    cadd.add_argument("--admin", action="store_true", help="allow /v1/config")
    cadd.add_argument("--secret", default="", help="optional fixed secret")
    cadd.add_argument("--label", default="", help="display label")
    args = p.parse_args(argv)

    if args.cmd == "mcp" or (args.cmd is None and len(sys.argv) == 1):
        from tollgate.mcp import main as mcp_main

        mcp_main()
        return

    if args.cmd == "serve":
        import os

        import uvicorn

        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8787"))
        uvicorn.run("tollgate.server_v1:app", host=host, port=port, reload=False)
        return

    if args.cmd == "health":
        from tollgate import get_keys_service
        from tollgate.consumers import auth_status
        from tollgate.paths import path_snapshot, pin_data_home_env

        pin_data_home_env()
        print(
            json.dumps(
                {
                    "ok": True,
                    "portable": path_snapshot(),
                    "auth": auth_status(),
                    "app": get_keys_service().app_status(),
                },
                indent=2,
                default=str,
            )
        )
        return

    if args.cmd == "paths":
        from tollgate.paths import path_snapshot, pin_data_home_env

        pin_data_home_env()
        print(json.dumps(path_snapshot(), indent=2))
        return

    if args.cmd == "consumer-add":
        from tollgate.consumers import add_consumer
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        out = add_consumer(
            args.id,
            secret=args.secret or None,
            admin=bool(args.admin),
            label=args.label or args.id,
        )
        print(json.dumps(out, indent=2))
        if out.get("ok"):
            print(
                f"\nUse header: X-Consumer-Key: {out['id']}:{out['secret']}",
                file=sys.stderr,
            )
        return

    p.print_help()


if __name__ == "__main__":
    main()
