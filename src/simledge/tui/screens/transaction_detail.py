"""Transaction detail modal — view and edit category/notes."""

import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import Input, Static

from simledge.categorize import load_rules
from simledge.config import DB_PATH, RULES_PATH
from simledge.db import init_db, update_transaction_field
from simledge.tags import set_transaction_tags


def _get_category_suggestions(conn):
    """Get all known categories from DB transactions and rules file."""
    db_cats = conn.execute(
        "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category"
    ).fetchall()
    categories = {r[0] for r in db_cats}
    for rule in load_rules(RULES_PATH):
        categories.add(rule["category"])
    return sorted(categories)


def _suggest_from_rules(description):
    """Try to match a description against rules, return best category or empty string."""
    rules = load_rules(RULES_PATH)
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)
    for rule in sorted_rules:
        pattern = rule["pattern"]
        try:
            if re.search(pattern, description, re.IGNORECASE):
                return rule["category"]
        except re.error:
            if pattern.upper() in description.upper():
                return rule["category"]
    return ""


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

        # Build category suggestions and prefill
        conn = init_db(DB_PATH)
        suggestions = _get_category_suggestions(conn)
        conn.close()
        suggester = SuggestFromList(suggestions, case_sensitive=False)

        # Prefill: use existing category, or try rules match
        category_value = t["category"]
        if not category_value and t.get("description"):
            category_value = _suggest_from_rules(t["description"])

        with Middle(), Center(), Vertical(id="txn-detail-box"):
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
                value=category_value,
                placeholder="Enter category (Tab to accept suggestion)...",
                suggester=suggester,
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
                "[dim]Tab[/] accept suggestion  [dim]Enter[/] save  [dim]Esc[/] cancel",
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
