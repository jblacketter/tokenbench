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


def _add_project(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--project",
        nargs="?",
        const=".",
        default=None,
        metavar="PATH",
        help="Scope to one project path (bare flag = current dir; omit for machine-wide)",
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
    _add_project(p_serve)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--no-ingest", action="store_true", help="Skip ingestion before serving")
    p_serve.add_argument("--open", action="store_true", help="Open a browser to the dashboard")

    p_status = sub.add_parser("status", help="Summarize the current store")
    _add_common(p_status)
    _add_project(p_status)

    p_limits = sub.add_parser(
        "limits", help="Show current rate-limit proximity and recent burn rate"
    )
    _add_common(p_limits)
    _add_project(p_limits)

    p_patterns = sub.add_parser(
        "patterns", help="Run the token-efficiency pattern measurements (offline)"
    )
    p_patterns.add_argument(
        "--markdown", action="store_true", help="Emit doc-ready markdown instead of a table"
    )
    p_patterns.add_argument(
        "--family", default=None, help="Filter to one family (e.g. 'Query')"
    )

    p_bench = sub.add_parser(
        "bench", help="Run the standardized token-efficiency benchmarks (offline)"
    )
    p_bench.add_argument(
        "--json", action="store_true", help="Emit the canonical results JSON artifact"
    )
    p_bench.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed benchmarks/results.json is in sync (exit 1 if not)",
    )
    p_bench.add_argument(
        "--category", default=None, help="Filter the table to one category"
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

    httpd = serve(db_path=args.db, host=args.host, port=args.port, project=args.project)
    url = f"http://{args.host}:{args.port}/"
    if args.project is not None:
        from .scope import normalize_project_path

        print(f"Scoped to project: {normalize_project_path(args.project)}")
    else:
        print("Scope: machine-wide (all projects)")
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

        analytics = Analytics(store, project=args.project)
        s = analytics.summary()
        scope = analytics.scope_info()
    scope_str = (
        f"project={scope['project']} ({scope['token_share']}% of machine tokens)"
        if scope["scoped"]
        else "scope=machine-wide"
    )
    print(
        f"store={args.db} {scope_str} events={s.event_count} sessions={s.session_count} "
        f"total_tokens={s.total_tokens:,} range={s.first_day or '-'}..{s.last_day or '-'}"
    )
    return 0


def cmd_limits(args) -> int:
    from .analytics import Analytics, LimitAnalytics, claude_budget_status, _now_epoch
    from .limits import DEFAULT_CLAUDE_BUDGET

    now = _now_epoch()
    with UsageStore(args.db) as store:
        analytics = Analytics(store, project=args.project)
        codex = LimitAnalytics(store).current_status(now_epoch=now)
        claude = claude_budget_status(analytics, DEFAULT_CLAUDE_BUDGET, now_epoch=now)
        burn = analytics.burn_rate(now_epoch=now)
        scope = analytics.scope_info()
    if scope["scoped"]:
        print(f"Scope: {scope['project']}  (Claude estimate + burn are project-scoped; "
              "Codex limits below are account-wide)\n")

    def _countdown(sec):
        if not sec:
            return ""
        h = sec // 3600
        return f"  (resets in ~{h // 24}d)" if h >= 24 else f"  (resets in ~{h}h)"

    print("Codex (from logs):")
    if codex:
        for w in codex:
            plan = f" [{w['plan_type']}]" if w.get("plan_type") else ""
            print(f"  {w['window_label']:<7} {w['used_percent']:>5.1f}% used{plan}{_countdown(w.get('reset_in_seconds'))}")
    else:
        print("  no rate-limit data ingested")
    print("Claude (estimate — logs carry no native limits):")
    for w in claude:
        if w.get("budget_tokens"):
            print(f"  {w['window_label']:<7} {w['used_percent']:>5.1f}% of {w['budget_tokens']:,} (est.)")
        else:
            print(f"  {w['window_label']:<7} {w['used_tokens']:,} tokens used — set a budget to get %")
    print(f"Burn rate: ~{burn['tokens_per_hour']:,} tokens/hour over last {int(burn['hours'])}h")
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


def cmd_bench(args) -> int:
    from .bench import canonical_json, check_results, measure_all, render_table

    if args.check:
        problems = check_results()
        if problems:
            print("Benchmark results OUT OF SYNC:")
            for p in problems:
                print(f"  - {p}")
            print("\nRegenerate with: tokenbench bench --json > benchmarks/results.json")
            return 1
        print("Benchmark results in sync with committed artifact.")
        return 0
    if args.json:
        print(canonical_json(), end="")
        return 0
    rows = measure_all()
    if args.category:
        wanted = args.category.lower()
        rows = [r for r in rows if r["category"].lower() == wanted]
        if not rows:
            print(f"No benchmark cases in category {args.category!r}.")
            return 1
    print(render_table(rows))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "ingest": cmd_ingest,
        "serve": cmd_serve,
        "status": cmd_status,
        "limits": cmd_limits,
        "patterns": cmd_patterns,
        "bench": cmd_bench,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
