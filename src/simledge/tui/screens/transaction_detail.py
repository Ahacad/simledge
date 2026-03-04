"""Transaction detail modal — view and edit category/notes."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db, update_transaction_field
from simledge.tags import get_transaction_tags, set_transaction_tags


class TransactionDetailScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, txn, tags=None):
        super().__init__()
        self.txn = txn
        self._tags = tags or []

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
                    yield Static("[dim]Tags[/]", classes="field-label")
                    yield Input(
                        value=", ".join(self._tags),
                        placeholder="Comma-separated tags...",
                        id="txn-tags",
                    )
                    yield Static(
                        "[dim]Category: max 100 chars  |  Notes: max 500 chars  |  Tags: comma-separated, max 50 each\n"
                        "Enter[/] save  [dim]Esc[/] cancel",
                        id="txn-detail-hint",
                    )

    def on_input_submitted(self, event: Input.Submitted):
        self._save_and_dismiss()

    def _save_and_dismiss(self):
        category = self.query_one("#txn-category", Input).value.strip()
        notes = self.query_one("#txn-notes", Input).value.strip()
        tags_raw = self.query_one("#txn-tags", Input).value

        if category and len(category) > 100:
            self.app.notify("Category too long (max 100 chars)", severity="error")
            return
        if notes and len(notes) > 500:
            self.app.notify("Notes too long (max 500 chars)", severity="error")
            return

        tag_names = [t.strip() for t in tags_raw.split(",") if t.strip()]
        if any(len(t) > 50 for t in tag_names):
            self.app.notify("Tag names max 50 chars each", severity="error")
            return

        conn = init_db(DB_PATH)
        update_transaction_field(conn, self.txn["id"], "category", category or None)
        update_transaction_field(conn, self.txn["id"], "notes", notes or None)
        set_transaction_tags(conn, self.txn["id"], tag_names)
        conn.close()
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)
