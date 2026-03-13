"""Budget screen — manage monthly category budgets."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Input, Select, Static

from simledge.budget import (
    budget_vs_actual,
    delete_budget,
    set_budget,
    total_budget_summary,
)
from simledge.categorize import load_rules
from simledge.config import BUDGETS_PATH, DB_PATH, RULES_PATH
from simledge.db import init_db
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar

_CUSTOM = "__custom__"


def _get_all_categories(conn):
    """Get sorted list of all known categories from DB + rules.

    Includes parent categories extracted from subcategories (e.g. "Housing"
    from "Housing:Rent") so users can budget at any level.
    """
    db_cats = conn.execute(
        "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL"
    ).fetchall()
    all_cats = {r[0] for r in db_cats}
    for rule in load_rules(RULES_PATH):
        all_cats.add(rule["category"])

    # Extract parent categories from subcategories
    for cat in list(all_cats):
        if ":" in cat:
            all_cats.add(cat.split(":")[0])

    return sorted(all_cats)


class BudgetModal(ModalScreen):
    """Modal for creating or editing a budget."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, budget=None):
        super().__init__()
        self._budget = budget

    def compose(self) -> ComposeResult:
        title = "Edit Budget" if self._budget else "New Budget"
        is_edit = bool(self._budget)

        conn = init_db(DB_PATH)
        categories = _get_all_categories(conn)
        conn.close()

        options = [(c, c) for c in categories]
        options.append(("Custom...", _CUSTOM))

        init_value = Select.NULL
        if is_edit:
            cat = self._budget["category"]
            init_value = cat if cat in categories else _CUSTOM

        with Middle(), Center(), Vertical(id="budget-modal-box"):
            yield Static(f"[bold]{title}[/]", id="budget-modal-title")
            yield Select(
                options,
                value=init_value,
                prompt="Category...",
                id="budget-category-select",
                disabled=is_edit,
            )
            yield Input(
                placeholder="Type custom category...",
                value=self._budget["category"] if is_edit and init_value == _CUSTOM else "",
                id="budget-category-custom",
            )
            yield Input(
                placeholder="Monthly limit",
                value=str(self._budget["budget"]) if self._budget else "",
                id="budget-amount",
            )
            yield Static(
                "[dim]Amount: positive number\nEnter: save  Esc: cancel[/]",
                id="budget-modal-hint",
            )

    def on_mount(self):
        custom_input = self.query_one("#budget-category-custom", Input)
        select = self.query_one("#budget-category-select", Select)
        if select.value == _CUSTOM:
            custom_input.display = True
        else:
            custom_input.display = False

        if self._budget:
            self.query_one("#budget-amount", Input).focus()
        else:
            select.focus()

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "budget-category-select":
            custom_input = self.query_one("#budget-category-custom", Input)
            if event.value == _CUSTOM:
                custom_input.display = True
                custom_input.focus()
            else:
                custom_input.display = False

    def _get_category(self):
        select = self.query_one("#budget-category-select", Select)
        if select.value == _CUSTOM:
            return self.query_one("#budget-category-custom", Input).value.strip()
        if select.value == Select.NULL:
            return ""
        return str(select.value)

    def on_input_submitted(self, event: Input.Submitted):
        self._submit()

    def _submit(self):
        category = self._get_category()
        amount_str = self.query_one("#budget-amount", Input).value.strip()

        if not category:
            self.app.notify("Category is required", severity="error")
            return
        if len(category) > 100:
            self.app.notify("Category too long (max 100 chars)", severity="error")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.app.notify("Amount must be a positive number", severity="error")
            return
        if amount > 1_000_000:
            self.app.notify("Budget limit seems too high. Max $1M.", severity="error")
            return

        self.dismiss({"category": category, "amount": amount})

    def action_cancel(self):
        self.dismiss(None)


def _progress_bar(pct, width=20):
    """Build a colored progress bar string."""
    filled = min(int(width * pct / 100), width)
    bar_char = "\u2588"
    empty_char = "\u2591"

    if pct > 100:
        color = "#ef4444"
    elif pct >= 80:
        color = "#eab308"
    else:
        color = "#22c55e"

    bar = f"[{color}]{bar_char * filled}[/][#333]{empty_char * (width - filled)}[/]"
    warn = " \u26a0" if pct > 100 else ""
    return f"{bar} {pct:>5.1f}%{warn}"


_SORT_MODES = [
    ("Budget \u2193", lambda r: r["budget"], True),
    ("Budget \u2191", lambda r: r["budget"], False),
    ("Spent \u2193", lambda r: r["actual"], True),
    ("Spent \u2191", lambda r: r["actual"], False),
    ("Remaining \u2191", lambda r: r["remaining"], False),
    ("Remaining \u2193", lambda r: r["remaining"], True),
    ("% Used \u2193", lambda r: r["pct_used"], True),
    ("% Used \u2191", lambda r: r["pct_used"], False),
    ("Category A-Z", lambda r: r["category"].lower(), False),
]


class BudgetScreen(Screen):
    BINDINGS = [
        Binding("n", "new_budget", "New", priority=True),
        Binding("d", "delete_budget", "Delete", priority=True),
        Binding("enter", "edit_budget", "Edit", priority=True),
        Binding("o", "cycle_sort", "Sort", priority=True),
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("budget")
        with Vertical(id="budget-summary-panel", classes="panel"):
            yield Static("", id="budget-summary-content")
        with Vertical(id="budget-panel", classes="panel"):
            yield DataTable(id="budget-table")
            yield Static("", id="budget-status")

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._sort_idx = 0  # default: Budget ↓
        self.query_one("#budget-summary-panel").border_title = "Budget Summary"
        self.query_one("#budget-panel").border_title = "Category Budgets"
        self._refresh_data()
        self.query_one("#budget-table", DataTable).focus()

    def on_screen_resume(self):
        self._refresh_data()
        self.query_one("#budget-table", DataTable).focus()

    def action_prev_month(self):
        y, m = int(self._month[:4]), int(self._month[5:])
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        self._month = f"{y:04d}-{m:02d}"
        self._refresh_data()

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
        self._refresh_data()

    def action_goto_today(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._refresh_data()

    def action_cycle_sort(self):
        self._sort_idx = (self._sort_idx + 1) % len(_SORT_MODES)
        label = _SORT_MODES[self._sort_idx][0]
        self.app.notify(f"Sort: {label}")
        self._refresh_data()

    def _refresh_data(self):
        m = self.app.privacy_mode
        conn = init_db(DB_PATH)
        month = self._month
        month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        account_ids = self.app.active_account_ids

        items = budget_vs_actual(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
        summary = total_budget_summary(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
        conn.close()

        # Apply current sort mode
        _, key_func, reverse = _SORT_MODES[self._sort_idx]
        items.sort(key=key_func, reverse=reverse)

        # Summary panel
        self.query_one(
            "#budget-summary-panel"
        ).border_title = f"Budget Summary \u2014 {month_display}"
        remaining_color = "#22c55e" if summary["total_remaining"] >= 0 else "#ef4444"
        pace_text = (
            f"{format_dollar(summary['daily_pace'], masked=m)}/day"
            if summary["days_remaining"] > 0
            else "month ended"
        )
        summary_text = (
            f"[bold]Budgeted:[/] {format_dollar(summary['total_budgeted'], masked=m)}"
            f"    [bold]Spent:[/] [#ef4444]{format_dollar(summary['total_actual'], masked=m)}[/]"
            f"    [bold]Remaining:[/] [{remaining_color}]{format_dollar(summary['total_remaining'], signed=True, masked=m)}[/]\n"
            f"[bold]Unbudgeted:[/] [dim]{format_dollar(summary['unbudgeted_spending'], masked=m)}[/]"
            f"    [bold]Pace:[/] {pace_text}"
            f"    [bold]Days left:[/] {summary['days_remaining']}"
        )
        self.query_one("#budget-summary-content", Static).update(summary_text)

        # Budget table
        table = self.query_one("#budget-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Category", "Budget", "Spent", "Remaining", "Progress")

        for item in items:
            remaining = item["remaining"]
            rem_color = "#22c55e" if remaining >= 0 else "#ef4444"
            bar = _progress_bar(item["pct_used"])
            table.add_row(
                item["category"],
                format_dollar(item["budget"], masked=m),
                f"[#ef4444]{format_dollar(item['actual'], masked=m)}[/]",
                f"[{rem_color}]{format_dollar(remaining, signed=True, masked=m)}[/]",
                bar,
                key=item["category"],
            )

        budget_count = len(items)
        sort_label = _SORT_MODES[self._sort_idx][0]
        status_pace = (
            f"{format_dollar(summary['daily_pace'], masked=m)}/day remaining"
            if summary["days_remaining"] > 0
            else "month ended"
        )
        self.query_one("#budget-status", Static).update(
            f"[dim]{budget_count} budgets  |  {status_pace}  |  sort: {sort_label}"
            f"  |  n: new  d: delete  o: sort  Enter: edit[/]"
        )

    def _get_selected_category(self):
        table = self.query_one("#budget-table", DataTable)
        if table.row_count == 0:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return row_key.value

    def action_new_budget(self):
        self.app.push_screen(BudgetModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        set_budget(BUDGETS_PATH, result["category"], result["amount"])
        self.app.notify(f"Budget set: {result['category']} ${result['amount']:,.2f}")
        self._refresh_data()

    def action_edit_budget(self):
        table = self.query_one("#budget-table", DataTable)
        if table.row_count == 0:
            self.app.notify("No budget selected", severity="warning")
            return
        conn = init_db(DB_PATH)
        items = budget_vs_actual(
            conn, self._month, path=BUDGETS_PATH, account_ids=self.app.active_account_ids
        )
        conn.close()
        _, key_func, reverse = _SORT_MODES[self._sort_idx]
        items.sort(key=key_func, reverse=reverse)
        row_idx = table.cursor_coordinate.row
        if row_idx < len(items):
            item = items[row_idx]
            self.app.push_screen(
                BudgetModal(budget=item),
                callback=self._on_modal_result,
            )

    def action_delete_budget(self):
        category = self._get_selected_category()
        if category is None:
            self.app.notify("No budget selected", severity="warning")
            return
        delete_budget(BUDGETS_PATH, category)
        self.app.notify("Budget deleted")
        self._refresh_data()
