"""Main Textual application for SimpLedge."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import Static

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
        Binding("1", "switch_mode('overview')", "Overview", priority=True),
        Binding("2", "switch_mode('transactions')", "Transactions", priority=True),
        Binding("3", "switch_mode('accounts')", "Accounts", priority=True),
        Binding("4", "switch_mode('trends')", "Trends", priority=True),
        Binding("5", "switch_mode('networth')", "Net Worth", priority=True),
        Binding("question_mark", "show_help", "? Help", priority=True),
        Binding("q", "quit", "Quit", priority=True),
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


def run_app():
    app = SimpLedgeApp()
    app.run()
