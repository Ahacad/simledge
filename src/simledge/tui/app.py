"""Main Textual application for SimpLedge."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Placeholder

from simledge.tui.screens.overview import OverviewScreen


class TransactionsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Transactions — coming soon")
        yield Footer()


class AccountsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Accounts — coming soon")
        yield Footer()


class TrendsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Trends — coming soon")
        yield Footer()


class NetWorthScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Placeholder("Net Worth — coming soon")
        yield Footer()


class SimpLedgeApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "SimpLedge"

    BINDINGS = [
        Binding("1", "switch_mode('overview')", "Overview", priority=True),
        Binding("2", "switch_mode('transactions')", "Transactions", priority=True),
        Binding("3", "switch_mode('accounts')", "Accounts", priority=True),
        Binding("4", "switch_mode('trends')", "Trends", priority=True),
        Binding("5", "switch_mode('networth')", "Net Worth", priority=True),
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


def run_app():
    app = SimpLedgeApp()
    app.run()
