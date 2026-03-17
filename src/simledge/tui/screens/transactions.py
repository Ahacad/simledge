"""Transactions screen — searchable, filterable table."""

import time
from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Checkbox, DataTable, Input, Select, Static

from simledge.colors import get_category_color
from simledge.config import DB_PATH
from simledge.db import get_transaction, init_db
from simledge.tags import get_transaction_tags
from simledge.tui.formatting import format_dollar
from simledge.tui.screens.transaction_detail import TransactionDetailScreen
from simledge.tui.widgets.navbar import NavBar


class FilterModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("c", "clear_all", "Clear all", priority=True),
    ]

    def __init__(self, current_filters=None, categories=None):
        super().__init__()
        self._current = current_filters or {}
        self._categories = categories or []

    def compose(self) -> ComposeResult:
        f = self._current
        with Middle(), Center(), Vertical(id="filter-modal-box"):
            yield Static("[bold]Filters[/]", id="filter-modal-title")
            yield Static("[dim]Description[/]", classes="field-label")
            yield Input(
                value=f.get("description", ""),
                placeholder="Filter by description...",
                id="filter-description",
            )
            yield Static("[dim]Category[/]", classes="field-label")
            cat_options = [("All categories", "")]
            cat_options.extend(self._categories)
            yield Select(
                cat_options,
                value=f.get("category", ""),
                prompt="Category...",
                id="filter-category",
                allow_blank=False,
            )
            yield Static("[dim]Tag[/]", classes="field-label")
            yield Input(
                value=f.get("tag", ""),
                placeholder="Filter by tag...",
                id="filter-tag",
            )
            yield Static("[dim]Min amount[/]", classes="field-label")
            yield Input(
                value=f.get("min_amount", ""),
                placeholder="e.g. 50",
                id="filter-min-amount",
            )
            yield Static("[dim]Max amount[/]", classes="field-label")
            yield Input(
                value=f.get("max_amount", ""),
                placeholder="e.g. 500",
                id="filter-max-amount",
            )
            yield Checkbox(
                "Pending only",
                value=f.get("pending_only", False),
                id="filter-pending",
            )
            yield Static(
                "[dim]Enter[/] apply  [dim]Esc[/] cancel  [dim]c[/] clear all",
                id="filter-modal-hint",
            )

    def on_input_submitted(self, event: Input.Submitted):
        self._apply()

    def _apply(self):
        filters = {}
        desc = self.query_one("#filter-description", Input).value.strip()
        if desc:
            filters["description"] = desc
        cat_select = self.query_one("#filter-category", Select)
        cat = str(cat_select.value) if cat_select.value not in (Select.BLANK, "") else ""
        if cat:
            filters["category"] = cat
        tag = self.query_one("#filter-tag", Input).value.strip()
        if tag:
            filters["tag"] = tag
        min_amt = self.query_one("#filter-min-amount", Input).value.strip()
        if min_amt:
            filters["min_amount"] = min_amt
        max_amt = self.query_one("#filter-max-amount", Input).value.strip()
        if max_amt:
            filters["max_amount"] = max_amt
        if self.query_one("#filter-pending", Checkbox).value:
            filters["pending_only"] = True
        self.dismiss(filters)

    def action_cancel(self):
        self.dismiss(None)

    def action_clear_all(self):
        self.dismiss({})


class TagFilterModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def compose(self) -> ComposeResult:
        with Middle(), Center(), Vertical(id="tag-filter-box"):
            yield Static("[bold]Filter by Tag[/]", id="tag-filter-title")
            yield Input(
                placeholder="Enter tag name...",
                id="tag-filter-input",
            )
            yield Static(
                "[dim]Enter[/] apply  [dim]Esc[/] cancel",
                id="tag-filter-hint",
            )

    def on_mount(self):
        self.query_one("#tag-filter-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        value = self.query_one("#tag-filter-input", Input).value.strip()
        self.dismiss(value)

    def action_cancel(self):
        self.dismiss(None)


class TransactionsScreen(Screen):
    BINDINGS = [
        ("slash", "focus_search", "/ Search"),
        ("escape", "clear_or_blur", "Esc Back"),
        Binding("f", "open_filters", "f Filters", show=False),
        Binding("g", "filter_tag", "g Tag filter", show=False),
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
        Binding("O", "reset_sort", "Reset sort", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("transactions")
        with Vertical(id="txn-panel", classes="panel"):
            yield Input(placeholder="Press / to search, f for filters...", id="search-input")
            yield DataTable(id="txn-table", cursor_type="row")
            yield Static("", id="txn-status")

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._filters = {}
        self._sort_column = "Date"
        self._sort_asc = False  # default: newest first
        self._sort_col_map = {
            "Date": "t.posted",
            "Amount": "t.amount",
            "Category": "t.category",
            "Account": "a.display_name",
        }
        self._update_title()
        self._apply_initial_filter()
        self._load_transactions()
        self.query_one("#txn-table", DataTable).focus()

    def on_screen_resume(self):
        initial = getattr(self.app, "txn_initial_filter", None)
        if initial:
            self.app.txn_initial_filter = None
            self._filters.update(initial)
            self._reload()
        self.query_one("#txn-table", DataTable).focus()

    def _apply_initial_filter(self):
        initial = getattr(self.app, "txn_initial_filter", None)
        if initial:
            self.app.txn_initial_filter = None
            self._filters.update(initial)

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
        self._reload()

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
        self._reload()

    def action_goto_today(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._update_title()
        self._reload()

    def _refresh_data(self):
        self._reload()

    def _reload(self):
        search = self.query_one("#search-input", Input).value.strip()
        self._load_transactions(search=search if search else None)

    def _load_transactions(self, search=None):
        conn = init_db(DB_PATH)

        query = (
            "SELECT t.id, t.posted, t.description, COALESCE(t.category, '\u2014'),"
            " t.amount, COALESCE(a.display_name, a.name), t.pending"
            " FROM transactions t JOIN accounts a ON t.account_id = a.id"
            " WHERE strftime('%Y-%m', t.posted) = ?"
        )
        params = [self._month]

        account_ids = self.app.active_account_ids
        if account_ids is not None:
            ids = list(account_ids)
            placeholders = ",".join("?" for _ in ids)
            query += f" AND t.account_id IN ({placeholders})"
            params.extend(ids)

        if search:
            query += " AND (t.description LIKE ? OR t.category LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Advanced filters
        f = self._filters
        if f.get("description"):
            query += " AND t.description LIKE ?"
            params.append(f"%{f['description']}%")
        if f.get("category"):
            query += " AND t.category LIKE ?"
            params.append(f"%{f['category']}%")
        if f.get("min_amount"):
            try:
                val = float(f["min_amount"])
                query += " AND ABS(t.amount) >= ?"
                params.append(val)
            except ValueError:
                pass
        if f.get("max_amount"):
            try:
                val = float(f["max_amount"])
                query += " AND ABS(t.amount) <= ?"
                params.append(val)
            except ValueError:
                pass
        if f.get("pending_only"):
            query += " AND t.pending = 1"
        if f.get("tag"):
            query += (
                " AND t.id IN (SELECT transaction_id FROM transaction_tags tt"
                " JOIN tags tg ON tt.tag_id = tg.id WHERE tg.name = ?)"
            )
            params.append(f["tag"].strip().lower())

        order_col = self._sort_col_map.get(self._sort_column, "t.posted")
        order_dir = "ASC" if self._sort_asc else "DESC"
        query += f" ORDER BY {order_col} {order_dir}, t.id DESC LIMIT 500"

        rows = conn.execute(query, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', posted) = ?",
            (self._month,),
        ).fetchone()[0]
        conn.close()

        table = self.query_one("#txn-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            self._col_header("Date"),
            "Description",
            self._col_header("Category"),
            self._col_header("Amount"),
            self._col_header("Account"),
        )

        m = self.app.privacy_mode
        for r in rows:
            txn_id, posted, desc, cat, amount, acct_name, pending = r
            color = "[#22c55e]" if amount > 0 else "[#ef4444]"
            pending_mark = " \u23f3" if pending else ""
            cat_color = get_category_color(cat)
            table.add_row(
                posted,
                (desc or "")[:35],
                f"[{cat_color}]{cat}[/]",
                f"{color}{format_dollar(amount, signed=True, masked=m)}[/]{pending_mark}",
                acct_name,
                key=txn_id,
            )

        status = f"[dim]Showing {len(rows)} of {total} transactions"
        filter_count = len(self._filters)
        if filter_count:
            tags = []
            if "description" in self._filters:
                tags.append(f"desc: {self._filters['description']}")
            if "category" in self._filters:
                tags.append(f"cat: {self._filters['category']}")
            if "min_amount" in self._filters:
                tags.append(f"min: ${self._filters['min_amount']}")
            if "max_amount" in self._filters:
                tags.append(f"max: ${self._filters['max_amount']}")
            if self._filters.get("pending_only"):
                tags.append("pending")
            if "tag" in self._filters:
                tags.append(f"tag: {self._filters['tag']}")
            status += f" [{'] ['.join(tags)}]"
        status += "[/]"
        self.query_one("#txn-status", Static).update(status)

    def _col_header(self, name):
        if name == self._sort_column:
            arrow = " \u25b2" if self._sort_asc else " \u25bc"
            return f"{name}{arrow}"
        return name

    def on_click(self, event):
        now = time.monotonic()
        if now - getattr(self, "_last_click_time", 0) < 0.35:
            # Rapid clicks can corrupt DataTable rendering state.
            # Schedule a rebuild to clear it (same effect as pressing Escape).
            self.set_timer(0.15, self._reload)
        self._last_click_time = now

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected):
        label = str(event.label).replace(" \u25b2", "").replace(" \u25bc", "")
        if label not in self._sort_col_map:
            return  # Description not sortable
        if label == self._sort_column:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_column = label
            self._sort_asc = label != "Date"  # Date defaults desc, others asc
        self._reload()

    def action_reset_sort(self):
        self._sort_column = "Date"
        self._sort_asc = False
        self._reload()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-input":
            search = event.value.strip()
            self._load_transactions(search=search if search else None)

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_clear_or_blur(self):
        search_input = self.query_one("#search-input", Input)
        if search_input.has_focus and search_input.value:
            search_input.value = ""
            self.query_one("#txn-table", DataTable).focus()
            self._load_transactions()
        elif self._filters:
            self._filters = {}
            self.query_one("#txn-table", DataTable).focus()
            self._reload()
        else:
            search_input.value = ""
            self.query_one("#txn-table", DataTable).focus()
            self._load_transactions()

    def action_open_filters(self):
        conn = init_db(DB_PATH)
        rows = conn.execute(
            "SELECT DISTINCT category FROM transactions"
            " WHERE category IS NOT NULL ORDER BY category"
        ).fetchall()
        conn.close()
        categories = self._build_category_options([r[0] for r in rows])
        self.app.push_screen(
            FilterModal(self._filters, categories=categories),
            self._on_filter_dismiss,
        )

    def _build_category_options(self, raw_categories):
        """Build category list with parent/child grouping as (label, value) tuples."""
        parents = {}
        standalone = []
        for cat in raw_categories:
            if ":" in cat:
                parent = cat.split(":")[0]
                parents.setdefault(parent, []).append(cat)
            else:
                standalone.append(cat)

        result = []
        seen_parents = set()
        for cat in standalone:
            result.append((cat, cat))
            seen_parents.add(cat)
            if cat in parents:
                for child in parents[cat]:
                    result.append((f"  {child}", child))

        # Parents that weren't standalone categories
        for parent, children in sorted(parents.items()):
            if parent not in seen_parents:
                result.append((parent, parent))
                for child in children:
                    result.append((f"  {child}", child))

        return result

    def _on_filter_dismiss(self, result):
        if result is None:
            return
        self._filters = result
        self._reload()

    def action_filter_tag(self):
        if self._filters.get("tag"):
            del self._filters["tag"]
            self._reload()
            return
        self.app.push_screen(TagFilterModal(), self._on_tag_filter_dismiss)

    def _on_tag_filter_dismiss(self, result):
        if result is None:
            return
        if result:
            self._filters["tag"] = result
        elif "tag" in self._filters:
            del self._filters["tag"]
        self._reload()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if getattr(self, "_detail_open", False):
            return
        # Release any stuck mouse state from rapid clicks
        event.data_table.release_mouse()

        txn_id = str(event.row_key.value)
        conn = init_db(DB_PATH)
        txn = get_transaction(conn, txn_id)
        tags = get_transaction_tags(conn, txn_id)
        conn.close()
        if not txn:
            return

        self._detail_open = True

        def on_dismiss(changed):
            self._detail_open = False
            if changed:
                self._reload()

        self.app.push_screen(TransactionDetailScreen(txn, tags=tags), on_dismiss)
