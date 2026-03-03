"""CLI entry point for SimpLedge."""

import argparse
import asyncio
import sys

from simledge.config import DB_PATH, CONFIG_PATH


def main():
    parser = argparse.ArgumentParser(
        prog="simledge",
        description="Personal finance TUI — sync, analyze, export",
    )
    sub = parser.add_subparsers(dest="command")

    sync_p = sub.add_parser("sync", help="fetch data from SimpleFIN")
    sync_p.add_argument("--full", action="store_true", help="re-sync all history")
    sync_p.add_argument("--start", help="start date YYYY-MM-DD (fetch history from this date)")
    sync_p.add_argument("--raw", action="store_true", help="dump raw SimpleFIN JSON and exit")

    sub.add_parser("status", help="show last sync and DB stats")
    sub.add_parser("setup", help="configure SimpleFIN access")

    export_p = sub.add_parser("export", help="export data for analysis")
    export_p.add_argument("--month", help="YYYY-MM (default: current month)")
    export_p.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")

    rule_p = sub.add_parser("rule", help="manage category rules")
    rule_sub = rule_p.add_subparsers(dest="rule_command")
    add_p = rule_sub.add_parser("add", help="add a category rule")
    add_p.add_argument("pattern", help="regex or keyword to match")
    add_p.add_argument("category", help="category to assign")
    add_p.add_argument("--priority", type=int, default=0)
    rule_sub.add_parser("list", help="list all rules")
    rule_sub.add_parser("test", help="dry-run rules against uncategorized")

    args = parser.parse_args()

    if args.command is None:
        _run_tui()
    elif args.command == "sync":
        _run_sync(args)
    elif args.command == "status":
        _run_status()
    elif args.command == "setup":
        _run_setup()
    elif args.command == "export":
        _run_export(args)
    elif args.command == "rule":
        _run_rule(args)
    else:
        parser.print_help()


def _run_tui():
    from simledge.tui.app import run_app
    run_app()


def _run_sync(args):
    if args.raw:
        from simledge.sync import load_access_url, fetch_accounts
        import json
        access_url = load_access_url()
        if not access_url:
            print("No SimpleFIN access URL configured. Run: simledge setup")
            return
        data = asyncio.run(fetch_accounts(access_url, start_date=args.start))
        print(json.dumps(data, indent=2))
        return
    from simledge.sync import run_sync
    asyncio.run(run_sync(full=args.full, start_date=args.start))


def _run_status():
    from simledge.db import init_db, get_last_sync

    conn = init_db(DB_PATH)
    last = get_last_sync(conn)
    txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    acct_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    print(f"Last sync: {last or 'never'}")
    print(f"Accounts: {acct_count}")
    print(f"Transactions: {txn_count}")
    print(f"Database: {DB_PATH}")
    conn.close()


def _run_setup():
    import os
    print("SimpLedge Setup")
    print("=" * 40)
    print()
    print("1. Go to https://beta-bridge.simplefin.org/ and create an account ($1.50/mo)")
    print("2. Connect your bank accounts")
    print("3. Get a setup token from the SimpleFIN dashboard")
    print()
    token = input("Paste your SimpleFIN setup token: ").strip()
    if not token:
        print("No token provided. Aborting.")
        return

    # Claim the token to get access URL
    access_url = asyncio.run(_claim_token(token))
    if not access_url:
        return

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write(f'[simplefin]\naccess_url = "{access_url}"\n\n[sync]\nauto_pending = true\n\n[export]\ndefault_format = "markdown"\n')
    os.chmod(CONFIG_PATH, 0o600)
    print(f"\nConfig saved to {CONFIG_PATH} (permissions: 600)")
    print("Run 'simledge sync' to fetch your data.")


async def _claim_token(token):
    from base64 import b64decode
    import httpx

    try:
        claim_url = b64decode(token).decode("utf-8")
    except Exception:
        print("Invalid token format. Should be base64-encoded URL.")
        return None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(claim_url, timeout=30)
            resp.raise_for_status()
            access_url = resp.text.strip()
            print("Token claimed successfully.")
            return access_url
    except httpx.HTTPError as e:
        print(f"Failed to claim token: {e}")
        return None


def _run_export(args):
    from datetime import datetime
    from simledge.db import init_db
    from simledge.export import export_markdown, export_csv, export_json

    month = args.month or datetime.now().strftime("%Y-%m")
    conn = init_db(DB_PATH)

    if args.format == "markdown":
        print(export_markdown(conn, month))
    elif args.format == "csv":
        print(export_csv(conn, month))
    elif args.format == "json":
        print(export_json(conn, month))

    conn.close()


def _run_rule(args):
    from simledge.db import init_db
    from simledge.categorize import add_rule, list_rules, apply_rules

    conn = init_db(DB_PATH)

    if args.rule_command == "add":
        add_rule(conn, args.pattern, args.category, args.priority)
        print(f"Rule added: '{args.pattern}' → {args.category}")
    elif args.rule_command == "list":
        rules = list_rules(conn)
        if not rules:
            print("No rules configured. Add one: simledge rule add 'PATTERN' category")
        else:
            print(f"{'ID':>4}  {'Priority':>8}  {'Pattern':<30}  Category")
            print("-" * 70)
            for r in rules:
                print(f"{r['id']:>4}  {r['priority']:>8}  {r['pattern']:<30}  {r['category']}")
    elif args.rule_command == "test":
        count = apply_rules(conn, dry_run=True)
        print(f"Would categorize {count} transactions.")
    else:
        print("Usage: simledge rule {add,list,test}")

    conn.close()


if __name__ == "__main__":
    main()
