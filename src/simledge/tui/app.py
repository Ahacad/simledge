"""Main Textual application for SimpLedge."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Checkbox, Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.sync import run_sync
from simledge.tui.screens.overview import OverviewScreen
from simledge.tui.screens.transactions import TransactionsScreen
from simledge.tui.screens.accounts import AccountsScreen
from simledge.tui.screens.trends import TrendsScreen
from simledge.tui.screens.networth import NetWorthScreen
from simledge.tui.screens.rules import RulesScreen
from simledge.tui.screens.recurring import RecurringScreen


HELP_TEXT = """\
[bold]SimpLedge Keyboard Shortcuts[/]

[bold]Navigation[/]
  [bold]1[/]  Overview      [bold]2[/]  Transactions
  [bold]3[/]  Accounts      [bold]4[/]  Trends
  [bold]5[/]  Net Worth     [bold]6[/]  Rules
  [bold]7[/]  Bills

[bold]Date Navigation[/]
  [bold]h/←[/]  Prev month   [bold]l/→[/]  Next month
  [bold]t[/]  Today          [bold]-/+[/]  Adjust range

[bold]Actions[/]
  [bold]s[/]  Sync from SimpleFIN
  [bold]a[/]  Filter accounts
  [bold]/[/]  Quick search (Transactions)
  [bold]f[/]  Advanced filters (Transactions)
  [bold]Esc[/]  Clear filters / close help
  [bold]?[/]  Show this help
  [bold]q[/]  Quit

[bold]Rules Screen[/]
  [bold]n[/]  New rule       [bold]d[/]  Delete rule
  [bold]Enter[/]  Edit rule  [bold]r[/]  Apply rules
  [bold]t[/]  Test (dry run)
"""


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("question_mark", "dismiss", "Close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Static(HELP_TEXT, id="help-box")


class AccountFilterModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("enter", "apply", "Apply", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                with Vertical(id="filter-box"):
                    yield Static("[bold]Filter Accounts[/]\n[dim]Space: toggle  Enter: apply  Esc: cancel[/]", id="filter-header")
                    yield VerticalScroll(id="filter-list")

    def on_mount(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()

        active = self.app.active_account_ids
        scroll = self.query_one("#filter-list", VerticalScroll)

        groups = {}
        for a in accounts:
            inst = a["institution"] or "Unknown"
            groups.setdefault(inst, []).append(a)

        for inst, accts in groups.items():
            scroll.mount(Static(f"[bold #2dd4bf]{inst}[/]", classes="filter-group-label"))
            for a in accts:
                bal = a["balance"] or 0
                color = "#22c55e" if bal >= 0 else "#ef4444"
                label = f"{a['name']}  [{color}]${bal:,.2f}[/]"
                checked = active is None or a["id"] in active
                cb = Checkbox(label, value=checked, id=f"filter-{a['id']}")
                cb._account_id = a["id"]
                scroll.mount(cb)

    def action_cancel(self):
        self.dismiss(None)

    def action_apply(self):
        checkboxes = self.query(Checkbox)
        selected = set()
        total = 0
        for cb in checkboxes:
            total += 1
            if cb.value:
                selected.add(cb._account_id)

        if len(selected) == total:
            self.dismiss("all")
        else:
            self.dismiss(selected)


class SimpLedgeApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "SimpLedge"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("1", "switch_mode('overview')", "Overview", priority=True, show=False),
        Binding("2", "switch_mode('transactions')", "Transactions", priority=True, show=False),
        Binding("3", "switch_mode('accounts')", "Accounts", priority=True, show=False),
        Binding("4", "switch_mode('trends')", "Trends", priority=True, show=False),
        Binding("5", "switch_mode('networth')", "Net Worth", priority=True, show=False),
        Binding("6", "switch_mode('rules')", "Rules", priority=True, show=False),
        Binding("7", "switch_mode('recurring')", "Bills", priority=True, show=False),
        Binding("s", "sync", "Sync", priority=True, show=False),
        Binding("a", "show_filter", "Filter", priority=True, show=False),
        Binding("question_mark", "show_help", "? Help", priority=True, show=False),
        Binding("q", "quit", "Quit", priority=True, show=False),
    ]

    MODES = {
        "overview": OverviewScreen,
        "transactions": TransactionsScreen,
        "accounts": AccountsScreen,
        "trends": TrendsScreen,
        "networth": NetWorthScreen,
        "rules": RulesScreen,
        "recurring": RecurringScreen,
    }

    def __init__(self):
        super().__init__()
        self.active_account_ids = None  # None = all accounts

    def on_mount(self):
        self.switch_mode("overview")

    def action_show_help(self):
        self.push_screen(HelpScreen())

    def action_show_filter(self):
        self.push_screen(AccountFilterModal(), callback=self._on_filter_dismiss)

    def _on_filter_dismiss(self, result):
        if result is None:
            return  # cancelled
        if result == "all":
            self.active_account_ids = None
        else:
            self.active_account_ids = result
        screen = self.screen
        if hasattr(screen, "_refresh_data"):
            screen._refresh_data()

    async def _do_sync(self):
        result = await run_sync(quiet=True)
        if result["status"] == "success":
            self.notify(f"Synced {result['accounts']} accounts, {result['transactions']} transactions")
        else:
            self.notify(result["status"], severity="error")
        if hasattr(self.screen, "_refresh_data"):
            self.screen._refresh_data()

    def action_sync(self):
        self.notify("Syncing...")
        self.run_worker(self._do_sync(), exclusive=True)


def run_app():
    app = SimpLedgeApp()
    app.run()
