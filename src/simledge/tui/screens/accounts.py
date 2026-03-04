"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("accounts")
        with VerticalScroll():
            yield Static("", id="accounts-content")

    def on_mount(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()

        if not accounts:
            self.query_one("#accounts-content", Static).update(
                "\n  No accounts yet. Run: simledge sync"
            )
            return

        # Group by institution
        groups = {}
        total_assets = 0
        total_debt = 0
        for a in accounts:
            inst = a["institution"] or "Unknown"
            groups.setdefault(inst, []).append(a)
            bal = a["balance"] or 0
            if bal >= 0:
                total_assets += bal
            else:
                total_debt += bal

        lines = ["\n"]
        for inst, accts in groups.items():
            lines.append(f"  {inst}")
            underline = "\u2500" * len(inst)
            lines.append(f"  {underline}")
            for a in accts:
                bal = a["balance"] or 0
                color = "[green]" if bal >= 0 else "[red]"
                lines.append(f"    {a['name']:<30} {color}${bal:>12,.2f}[/]")
            lines.append("")

        separator = "\u2501" * 50
        lines.append(f"  {separator}")
        lines.append(f"  Total Assets:  [green]${total_assets:>12,.2f}[/]")
        lines.append(f"  Total Debt:    [red]${total_debt:>12,.2f}[/]")
        lines.append(f"  Net Worth:     ${total_assets + total_debt:>12,.2f}")

        self.query_one("#accounts-content", Static).update("\n".join(lines))
