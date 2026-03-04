"""Accounts screen — balances grouped by institution."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield NavBar("accounts")
        yield VerticalScroll(id="accounts-scroll")

    def on_mount(self):
        self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        account_ids = self.app.active_account_ids
        accounts = account_summary(conn, account_ids=account_ids)
        conn.close()

        scroll = self.query_one("#accounts-scroll", VerticalScroll)
        scroll.remove_children()

        if not accounts:
            panel = Vertical(Static("[dim]No accounts yet. Run: simledge sync[/]"), classes="panel")
            panel.border_title = "Accounts"
            scroll.mount(panel)
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

        m = self.app.privacy_mode
        for inst, accts in groups.items():
            lines = []
            for a in accts:
                bal = a["balance"] or 0
                color = "#22c55e" if bal >= 0 else "#ef4444"
                lines.append(f"{a['name']:<30} [{color}]{format_dollar(bal, masked=m):>13}[/]")
            panel = Vertical(Static("\n".join(lines)), classes="panel")
            panel.border_title = inst
            scroll.mount(panel)

        # Summary panel
        net = total_assets + total_debt
        summary_lines = [
            f"[bold]Assets:[/]   [#22c55e]{format_dollar(total_assets, masked=m):>13}[/]",
            f"[bold]Debt:[/]     [#ef4444]{format_dollar(total_debt, masked=m):>13}[/]",
            f"[bold]Net Worth:[/] {format_dollar(net, masked=m):>13}",
        ]
        summary = Vertical(Static("\n".join(summary_lines)), classes="panel")
        summary.border_title = "Summary"
        scroll.mount(summary)
