"""Main Textual application for SimpLedge."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import Static

from simledge.sync import run_sync
from simledge.tui.screens.overview import OverviewScreen
from simledge.tui.screens.transactions import TransactionsScreen
from simledge.tui.screens.accounts import AccountsScreen
from simledge.tui.screens.trends import TrendsScreen
from simledge.tui.screens.networth import NetWorthScreen


HELP_TEXT = """\
[bold]SimpLedge Keyboard Shortcuts[/]

[bold]Navigation[/]
  [bold]1[/]  Overview      [bold]2[/]  Transactions
  [bold]3[/]  Accounts      [bold]4[/]  Trends
  [bold]5[/]  Net Worth

[bold]Actions[/]
  [bold]s[/]  Sync from SimpleFIN
  [bold]/[/]  Search (Transactions screen)
  [bold]Esc[/]  Clear search / close help
  [bold]?[/]  Show this help
  [bold]q[/]  Quit
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
        Binding("s", "sync", "Sync", priority=True, show=False),
        Binding("question_mark", "show_help", "? Help", priority=True, show=False),
        Binding("q", "quit", "Quit", priority=True, show=False),
    ]

    MODES = {
        "overview": OverviewScreen,
        "transactions": TransactionsScreen,
        "accounts": AccountsScreen,
        "trends": TrendsScreen,
        "networth": NetWorthScreen,
    }

    def on_mount(self):
        self.switch_mode("overview")

    def action_show_help(self):
        self.push_screen(HelpScreen())

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
