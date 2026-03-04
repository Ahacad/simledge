"""Transactions screen — searchable, filterable table."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db, get_transaction
from simledge.tui.screens.transaction_detail import TransactionDetailScreen
from simledge.tui.widgets.navbar import NavBar


class TransactionsScreen(Screen):
    BINDINGS = [
        ("slash", "focus_search", "/ Search"),
        ("escape", "blur_search", "Esc Back"),
        ("enter", "open_detail", "Enter Detail"),
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("transactions")
        with Vertical(id="txn-panel", classes="panel"):
            yield Input(placeholder="Press / to search...", id="search-input")
            yield DataTable(id="txn-table")
            yield Static("", id="txn-status")

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._update_title()
        self._load_transactions()
        self.query_one("#txn-table", DataTable).focus()

    def on_screen_resume(self):
        self.query_one("#txn-table", DataTable).focus()

    def _update_title(self):
        month_display = datetime.strptime(self._month, "%Y-%m").strftime("%B %Y")
        self.query_one("#txn-panel").border_title = f"Transactions — {month_display}"

    def action_prev_month(self):
        y, m = int(self._month[:4]), int(self._month[5:])
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        self._month = f"{y:04d}-{m:02d}"
        self._update_title()
        search = self.query_one("#search-input", Input).value.strip()
        self._load_transactions(search=search if search else None)

    def action_next_month(self):
        now = datetime.now().strftime("%Y-%m")
        if self._month >= now:
            return
        y, m = int(self._month[:4]), int(self._month[5:])
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        new_month = f"{y:04d}-{m:02d}"
        if new_month > now:
            return
        self._month = new_month
        self._update_title()
        search = self.query_one("#search-input", Input).value.strip()
        self._load_transactions(search=search if search else None)

    def action_goto_today(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._update_title()
        search = self.query_one("#search-input", Input).value.strip()
        self._load_transactions(search=search if search else None)

    def _load_transactions(self, search=None):
        conn = init_db(DB_PATH)

        query = (
            "SELECT t.id, t.posted, t.description, COALESCE(t.category, '\u2014'),"
            " t.amount, a.name, t.pending"
            " FROM transactions t JOIN accounts a ON t.account_id = a.id"
            " WHERE strftime('%Y-%m', t.posted) = ?"
        )
        params = [self._month]

        if search:
            query += " AND (t.description LIKE ? OR t.category LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY t.posted DESC, t.id DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', posted) = ?",
            (self._month,),
        ).fetchone()[0]
        conn.close()

        table = self.query_one("#txn-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount", "Account")

        for r in rows:
            txn_id, posted, desc, cat, amount, acct_name, pending = r
            color = "[#22c55e]" if amount > 0 else "[#ef4444]"
            pending_mark = " \u23f3" if pending else ""
            table.add_row(
                posted,
                (desc or "")[:35],
                cat,
                f"{color}${amount:+,.2f}[/]{pending_mark}",
                acct_name,
                key=txn_id,
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

    def action_open_detail(self):
        table = self.query_one("#txn-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        txn_id = str(row_key)
        conn = init_db(DB_PATH)
        txn = get_transaction(conn, txn_id)
        conn.close()
        if not txn:
            return

        def on_dismiss(changed):
            if changed:
                search = self.query_one("#search-input", Input).value.strip()
                self._load_transactions(search=search if search else None)

        self.app.push_screen(TransactionDetailScreen(txn), on_dismiss)
