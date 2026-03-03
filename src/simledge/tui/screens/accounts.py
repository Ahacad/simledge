"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="accounts-content")
        yield Footer()

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
            lines.append(f"  {'\u2500' * len(inst)}")
            for a in accts:
                bal = a["balance"] or 0
                color = "[green]" if bal >= 0 else "[red]"
                lines.append(f"    {a['name']:<30} {color}${bal:>12,.2f}[/]")
            lines.append("")

        lines.append(f"  {'\u2501' * 50}")
        lines.append(f"  Total Assets:  [green]${total_assets:>12,.2f}[/]")
        lines.append(f"  Total Debt:    [red]${total_debt:>12,.2f}[/]")
        lines.append(f"  Net Worth:     ${total_assets + total_debt:>12,.2f}")

        self.query_one("#accounts-content", Static).update("\n".join(lines))
