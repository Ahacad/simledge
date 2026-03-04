"""Transactions screen — searchable, filterable table."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class TransactionsScreen(Screen):
    BINDINGS = [
        ("slash", "focus_search", "/ Search"),
        ("escape", "blur_search", "Esc Back"),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("transactions")
        with Vertical(id="txn-panel", classes="panel"):
            yield Input(placeholder="Press / to search...", id="search-input")
            yield DataTable(id="txn-table")
            yield Static("", id="txn-status")

    def on_mount(self):
        self.query_one("#txn-panel").border_title = "Transactions"
        self._load_transactions()
        self.query_one("#txn-table", DataTable).focus()

    def on_screen_resume(self):
        self.query_one("#txn-table", DataTable).focus()

    def _load_transactions(self, search=None):
        conn = init_db(DB_PATH)

        query = (
            "SELECT t.posted, t.description, COALESCE(t.category, '\u2014'),"
            " t.amount, a.name, t.pending"
            " FROM transactions t JOIN accounts a ON t.account_id = a.id"
        )
        params = []

        if search:
            query += " WHERE (t.description LIKE ? OR t.category LIKE ?)"
            params = [f"%{search}%", f"%{search}%"]

        query += " ORDER BY t.posted DESC, t.id DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()

        table = self.query_one("#txn-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount", "Account")

        for r in rows:
            posted, desc, cat, amount, acct_name, pending = r
            color = "[#22c55e]" if amount > 0 else "[#ef4444]"
            pending_mark = " \u23f3" if pending else ""
            table.add_row(
                posted,
                (desc or "")[:35],
                cat,
                f"{color}${amount:+,.2f}[/]{pending_mark}",
                acct_name,
            )

        self.query_one("#txn-status", Static).update(
            f"[dim]Showing {len(rows)} of {total} transactions[/]"
        )

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-input":
            search = event.value.strip()
            self._load_transactions(search=search if search else None)

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_blur_search(self):
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self.query_one("#txn-table", DataTable).focus()
        self._load_transactions()
