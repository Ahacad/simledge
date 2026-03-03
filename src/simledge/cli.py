"""CLI entry point for SimpLedge."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="simledge",
        description="Personal finance TUI — sync, analyze, export",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="fetch data from SimpleFIN")
    sub.add_parser("status", help="show last sync and DB stats")
    sub.add_parser("setup", help="configure SimpleFIN access")

    export_p = sub.add_parser("export", help="export data for analysis")
    export_p.add_argument("--month", help="YYYY-MM")
    export_p.add_argument("--format", choices=["markdown", "csv", "json"], default="markdown")

    rule_p = sub.add_parser("rule", help="manage category rules")
    rule_sub = rule_p.add_subparsers(dest="rule_command")
    add_p = rule_sub.add_parser("add", help="add a category rule")
    add_p.add_argument("pattern", help="regex or keyword to match")
    add_p.add_argument("category", help="category to assign")
    rule_sub.add_parser("list", help="list all rules")
    rule_sub.add_parser("test", help="dry-run rules against uncategorized")

    args = parser.parse_args()

    if args.command is None:
        # Default: launch TUI
        print("TUI not implemented yet — use a subcommand. Try: simledge --help")
        sys.exit(0)

    print(f"Command '{args.command}' not implemented yet.")


if __name__ == "__main__":
    main()
