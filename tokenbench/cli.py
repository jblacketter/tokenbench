"""Command-line interface for TokenBench.

Subcommands:
  ingest [--dry-run]   Scan local logs and store normalized usage (or report only).
  serve                Ingest (unless --no-ingest) then serve the localhost dashboard.
  status               Print a one-line summary of the current store.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .ingest import dry_run, ingest, format_report
from .storage import UsageStore, DEFAULT_DB_PATH


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--db", default=str(DEFAULT_DB_PATH), help="SQLite path (default: data/tokenbench.sqlite3)"
    )
    p.add_argument(
        "--home", default=None, help="Override home dir for log discovery (testing)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenbench", description=__doc__)
    parser.add_argument("--version", action="version", version=f"tokenbench {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Scan local logs and store usage")
    _add_common(p_ingest)
    p_ingest.add_argument(
        "--dry-run", action="store_true", help="Report discoveries without writing to SQLite"
    )

    p_serve = sub.add_parser("serve", help="Serve the localhost dashboard")
    _add_common(p_serve)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--no-ingest", action="store_true", help="Skip ingestion before serving")
    p_serve.add_argument("--open", action="store_true", help="Open a browser to the dashboard")

    p_status = sub.add_parser("status", help="Summarize the current store")
    _add_common(p_status)

    p_patterns = sub.add_parser(
        "patterns", help="Run the token-efficiency pattern measurements (offline)"
    )
    p_patterns.add_argument(
        "--markdown", action="store_true", help="Emit doc-ready markdown instead of a table"
    )
    p_patterns.add_argument(
        "--family", default=None, help="Filter to one family (e.g. 'Query')"
    )

    return parser


def _home(args) -> Path | None:
    return Path(args.home) if args.home else None


def cmd_ingest(args) -> int:
    if args.dry_run:
        result = dry_run(_home(args))
    else:
        result = ingest(_home(args), db_path=args.db)
    print(format_report(result))
    return 0


def cmd_serve(args) -> int:
    from .dashboard import serve  # local import keeps http.server out of fast paths

    if not args.no_ingest:
        result = ingest(_home(args), db_path=args.db)
        print(format_report(result))
        print()

    httpd = serve(db_path=args.db, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/"
    print(f"TokenBench dashboard serving at {url}  (Ctrl-C to stop)")
    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        httpd.server_close()
    return 0


def cmd_status(args) -> int:
    with UsageStore(args.db) as store:
        from .analytics import Analytics

        s = Analytics(store).summary()
    print(
        f"store={args.db} events={s.event_count} sessions={s.session_count} "
        f"total_tokens={s.total_tokens:,} range={s.first_day or '-'}..{s.last_day or '-'}"
    )
    return 0


def cmd_patterns(args) -> int:
    from .patterns import all_scenarios, render_markdown, render_table

    scenarios = all_scenarios()
    if args.family:
        wanted = args.family.lower()
        scenarios = [s for s in scenarios if s.family.lower() == wanted]
        if not scenarios:
            print(f"No scenarios in family {args.family!r}.")
            return 1
    if args.markdown:
        print(render_markdown(scenarios))
    else:
        print(render_table(scenarios))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "ingest": cmd_ingest,
        "serve": cmd_serve,
        "status": cmd_status,
        "patterns": cmd_patterns,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
