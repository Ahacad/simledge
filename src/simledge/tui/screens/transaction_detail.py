"""Transaction detail modal — view and edit category/notes."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db, update_transaction_field


class TransactionDetailScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, txn):
        super().__init__()
        self.txn = txn

    def compose(self) -> ComposeResult:
        t = self.txn
        color = "#22c55e" if t["amount"] > 0 else "#ef4444"
        status = "Pending" if t["pending"] else "Posted"
        with Middle():
            with Center():
                with Vertical(id="txn-detail-box"):
                    yield Static(
                        f"[bold]{t['description']}[/]\n\n"
                        f"[dim]Date[/]        {t['posted']}\n"
                        f"[dim]Amount[/]      [{color}]${t['amount']:+,.2f}[/]\n"
                        f"[dim]Account[/]     {t['account']}"
                        f" ({t['institution']})\n"
                        f"[dim]Status[/]      {status}",
                        id="txn-detail-info",
                    )
                    yield Static("[dim]Category[/]", classes="field-label")
                    yield Input(
                        value=t["category"],
                        placeholder="Enter category...",
                        id="txn-category",
                    )
                    yield Static("[dim]Notes[/]", classes="field-label")
                    yield Input(
                        value=t["notes"],
                        placeholder="Enter notes...",
                        id="txn-notes",
                    )
                    yield Static(
                        "[dim]Enter[/] save  [dim]Esc[/] cancel",
                        id="txn-detail-hint",
                    )

    def on_input_submitted(self, event: Input.Submitted):
        self._save_and_dismiss()

    def _save_and_dismiss(self):
        category = self.query_one("#txn-category", Input).value.strip()
        notes = self.query_one("#txn-notes", Input).value.strip()
        conn = init_db(DB_PATH)
        update_transaction_field(conn, self.txn["id"], "category", category or None)
        update_transaction_field(conn, self.txn["id"], "notes", notes or None)
        conn.close()
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)
