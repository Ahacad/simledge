"""Transaction detail modal — view and edit category/notes."""

import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Select, Static

from simledge.categorize import load_rules
from simledge.config import DB_PATH, RULES_PATH
from simledge.db import init_db, update_transaction_field
from simledge.tags import set_transaction_tags

_CUSTOM = "__custom__"


def _get_category_tree(conn):
    """Build parent -> [children] mapping from DB + rules.

    Returns (parents_with_children, standalone_categories):
      parents_with_children: {"Food": ["Groceries", "Dining", ...], ...}
      standalone: ["Transfer", "uncategorized", ...]
    """
    db_cats = conn.execute(
        "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL"
    ).fetchall()
    all_cats = {r[0] for r in db_cats}
    for rule in load_rules(RULES_PATH):
        all_cats.add(rule["category"])

    parents = {}
    standalone = set()
    for cat in sorted(all_cats):
        if ":" in cat:
            parent, child = cat.split(":", 1)
            parents.setdefault(parent, []).append(child)
        else:
            standalone.add(cat)

    # Parents that also appear standalone — keep them as parents
    for p in list(parents):
        standalone.discard(p)

    return parents, sorted(standalone)


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

        # Build category tree
        conn = init_db(DB_PATH)
        self._cat_parents, self._cat_standalone = _get_category_tree(conn)
        conn.close()

        # Determine initial value from existing or rules
        category_value = t["category"]
        if not category_value and t.get("description"):
            category_value = _suggest_from_rules(t["description"])
        self._prefilled = category_value

        # Parse initial parent/child
        init_parent = Select.NULL
        init_child = Select.NULL
        if category_value:
            if ":" in category_value:
                p, c = category_value.split(":", 1)
                if p in self._cat_parents:
                    init_parent = p
                    init_child = c
                else:
                    init_parent = _CUSTOM
            elif category_value in self._cat_standalone or category_value in self._cat_parents:
                init_parent = category_value
            else:
                init_parent = _CUSTOM

        # Build parent options
        parent_options = []
        for p in sorted(self._cat_parents):
            count = len(self._cat_parents[p])
            parent_options.append((f"{p} ({count})", p))
        for s in self._cat_standalone:
            parent_options.append((s, s))
        parent_options.append(("Custom...", _CUSTOM))

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
            with Horizontal(id="category-selects"):
                yield Select(
                    parent_options,
                    value=init_parent,
                    prompt="Category...",
                    id="txn-cat-parent",
                )
                yield Select(
                    [],
                    prompt="Subcategory...",
                    id="txn-cat-child",
                )
            yield Input(
                value=category_value if init_parent == _CUSTOM else "",
                placeholder="Type custom category...",
                id="txn-category-custom",
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
                "[dim]Type to search  [dim]Enter[/] save  [dim]Esc[/] cancel",
                id="txn-detail-hint",
            )

    def on_mount(self):
        custom_input = self.query_one("#txn-category-custom", Input)
        child_select = self.query_one("#txn-cat-child", Select)
        parent_select = self.query_one("#txn-cat-parent", Select)

        parent_val = parent_select.value
        if parent_val == _CUSTOM:
            child_select.display = False
            custom_input.display = True
        elif parent_val != Select.NULL and parent_val in self._cat_parents:
            self._update_child_options(parent_val)
            custom_input.display = False
        else:
            child_select.display = False
            custom_input.display = False

    def _update_child_options(self, parent):
        """Populate the child select with subcategories for the given parent."""
        child_select = self.query_one("#txn-cat-child", Select)
        children = self._cat_parents.get(parent, [])
        if children:
            options = [(c, c) for c in sorted(children)]
            child_select.set_options(options)
            child_select.display = True
            # Restore prefilled child if applicable
            if self._prefilled and ":" in self._prefilled:
                _, prefill_child = self._prefilled.split(":", 1)
                if prefill_child in children:
                    child_select.value = prefill_child
        else:
            child_select.display = False

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "txn-cat-parent":
            custom_input = self.query_one("#txn-category-custom", Input)
            child_select = self.query_one("#txn-cat-child", Select)
            val = event.value

            if val == _CUSTOM:
                child_select.display = False
                custom_input.display = True
                custom_input.focus()
            elif val != Select.NULL and val in self._cat_parents:
                custom_input.display = False
                self._update_child_options(val)
            else:
                # Standalone category — no children
                child_select.display = False
                custom_input.display = False

    def on_input_submitted(self, event: Input.Submitted):
        self._save_and_dismiss()

    def _get_category_value(self):
        parent_select = self.query_one("#txn-cat-parent", Select)
        parent = parent_select.value

        if parent == _CUSTOM:
            return self.query_one("#txn-category-custom", Input).value.strip()
        if parent == Select.NULL:
            return ""

        parent_str = str(parent)
        # Check if this parent has children
        if parent_str in self._cat_parents:
            child_select = self.query_one("#txn-cat-child", Select)
            child = child_select.value
            if child != Select.NULL:
                return f"{parent_str}:{child}"
            return parent_str
        return parent_str

    def _save_and_dismiss(self):
        category = self._get_category_value()
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
