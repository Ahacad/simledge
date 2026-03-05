"""Accounts screen — balances grouped by institution with editable display names."""

import contextlib

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Input, Select, Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db, update_account_display_name, update_account_type
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar

ACCOUNT_TYPES = [
    ("Checking", "checking"),
    ("Savings", "savings"),
    ("Credit Card", "credit"),
    ("Investment", "investment"),
    ("Other", "other"),
]


class AccountsScreen(Screen):
    BINDINGS = [
        Binding("e", "edit_name", "e Rename", priority=True),
        Binding("t", "edit_type", "t Type", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("accounts")
        with Vertical(id="accounts-panel", classes="panel"):
            yield DataTable(id="accounts-table")
            yield Static("", id="accounts-summary")
            yield Static("", id="accounts-status")

    def on_mount(self):
        self._editing = False
        self._edit_account_id = None
        self._refresh_data()
        self.query_one("#accounts-table", DataTable).focus()

    def on_screen_resume(self):
        self._refresh_data()
        self.query_one("#accounts-table", DataTable).focus()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        account_ids = self.app.active_account_ids
        accounts = account_summary(conn, account_ids=account_ids)
        conn.close()

        self._accounts = accounts

        table = self.query_one("#accounts-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Institution", "Account", "Type", "Balance")

        m = self.app.privacy_mode
        total_assets = 0
        total_debt = 0

        for a in accounts:
            bal = a["balance"] or 0
            color = "#22c55e" if bal >= 0 else "#ef4444"
            display = a["display_name"] or a["name"]
            inst = a["institution"] or "Unknown"
            acct_type = (a["type"] or "").replace("_", " ").title()
            table.add_row(
                inst,
                display,
                acct_type,
                f"[{color}]{format_dollar(bal, masked=m):>13}[/]",
                key=a["id"],
            )
            if bal >= 0:
                total_assets += bal
            else:
                total_debt += bal

        net = total_assets + total_debt
        summary = (
            f"[bold]Assets:[/] [#22c55e]{format_dollar(total_assets, masked=m)}[/]"
            f"    [bold]Debt:[/] [#ef4444]{format_dollar(total_debt, masked=m)}[/]"
            f"    [bold]Net:[/] {format_dollar(net, masked=m)}"
        )
        self.query_one("#accounts-summary", Static).update(summary)

        status = f"[dim]{len(accounts)} accounts  |  e: rename  t: type[/]"
        self.query_one("#accounts-status", Static).update(status)
        self.query_one("#accounts-panel").border_title = "Accounts"

    def action_edit_name(self):
        if self._editing:
            return
        table = self.query_one("#accounts-table", DataTable)
        if table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        account_id = str(row_key.value)

        # Find current display name
        acct = next((a for a in self._accounts if a["id"] == account_id), None)
        if not acct:
            return

        self._edit_account_id = account_id
        current = acct["display_name"] or acct["name"]

        # Replace status bar with input
        status = self.query_one("#accounts-status", Static)
        status.display = False

        inp = Input(
            value=current,
            placeholder="Display name (empty to reset)",
            id="edit-name-input",
        )
        self.query_one("#accounts-panel").mount(inp)
        inp.focus()
        self._editing = True

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "edit-name-input":
            self._save_name(event.value.strip())

    def key_escape(self):
        if self._editing:
            self._cancel_edit()
            return

    def _save_name(self, name):
        conn = init_db(DB_PATH)
        update_account_display_name(conn, self._edit_account_id, name)
        conn.close()
        self._cleanup_edit()
        self._refresh_data()
        self.app.notify(f"Account renamed to '{name}'" if name else "Name reset to default")

    def _cancel_edit(self):
        self._cleanup_edit()

    def _cleanup_edit(self):
        self._editing = False
        self._edit_account_id = None
        for widget_id in ("#edit-name-input", "#edit-type-select"):
            with contextlib.suppress(Exception):
                self.query_one(widget_id).remove()
        self.query_one("#accounts-status", Static).display = True
        self.query_one("#accounts-table", DataTable).focus()

    def action_edit_type(self):
        if self._editing:
            return
        table = self.query_one("#accounts-table", DataTable)
        if table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        account_id = str(row_key.value)

        acct = next((a for a in self._accounts if a["id"] == account_id), None)
        if not acct:
            return

        self._edit_account_id = account_id
        current = acct["type"]

        status = self.query_one("#accounts-status", Static)
        status.display = False

        sel = Select(
            ACCOUNT_TYPES,
            value=current if current else Select.BLANK,
            prompt="Account type...",
            id="edit-type-select",
        )
        self.query_one("#accounts-panel").mount(sel)
        sel.focus()
        self._editing = True

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "edit-type-select":
            val = event.value
            if val == Select.BLANK:
                return
            conn = init_db(DB_PATH)
            update_account_type(conn, self._edit_account_id, val)
            conn.close()
            self._cleanup_edit()
            self._refresh_data()
            label = next((name for name, v in ACCOUNT_TYPES if v == val), val)
            self.app.notify(f"Account type set to '{label}'")
