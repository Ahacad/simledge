"""Budget screen — manage monthly category budgets."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Center, Middle
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Input, Static

from simledge.budget import (
    get_budgets, set_budget, delete_budget,
    budget_vs_actual, total_budget_summary,
)
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


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
        with Middle():
            with Center():
                with Vertical(id="budget-modal-box"):
                    yield Static(f"[bold]{title}[/]", id="budget-modal-title")
                    yield Input(
                        placeholder="Category",
                        value=self._budget["category"] if self._budget else "",
                        id="budget-category",
                        disabled=bool(self._budget),
                    )
                    yield Input(
                        placeholder="Monthly limit",
                        value=str(self._budget["budget"]) if self._budget else "",
                        id="budget-amount",
                    )
                    yield Static(
                        "[dim]Enter: save  Esc: cancel[/]",
                        id="budget-modal-hint",
                    )

    def on_mount(self):
        if self._budget:
            self.query_one("#budget-amount", Input).focus()
        else:
            self.query_one("#budget-category", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        category = self.query_one("#budget-category", Input).value.strip()
        amount_str = self.query_one("#budget-amount", Input).value.strip()

        if not category:
            self.app.notify("Category is required", severity="error")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.app.notify("Amount must be a positive number", severity="error")
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


class BudgetScreen(Screen):
    BINDINGS = [
        Binding("n", "new_budget", "New", priority=True),
        Binding("d", "delete_budget", "Delete", priority=True),
        Binding("enter", "edit_budget", "Edit", priority=True),
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

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        month = self._month
        month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        account_ids = self.app.active_account_ids

        items = budget_vs_actual(conn, month, account_ids=account_ids)
        summary = total_budget_summary(conn, month, account_ids=account_ids)
        budgets = get_budgets(conn)
        conn.close()

        # Build budget id lookup
        budget_ids = {b["category"].lower(): b["id"] for b in budgets}

        # Summary panel
        self.query_one("#budget-summary-panel").border_title = f"Budget Summary \u2014 {month_display}"
        remaining_color = "#22c55e" if summary["total_remaining"] >= 0 else "#ef4444"
        pace_text = f"${summary['daily_pace']:,.2f}/day" if summary["days_remaining"] > 0 else "month ended"
        summary_text = (
            f"[bold]Budgeted:[/] ${summary['total_budgeted']:,.2f}"
            f"    [bold]Spent:[/] [#ef4444]${summary['total_actual']:,.2f}[/]"
            f"    [bold]Remaining:[/] [{remaining_color}]${summary['total_remaining']:+,.2f}[/]\n"
            f"[bold]Unbudgeted:[/] [dim]${summary['unbudgeted_spending']:,.2f}[/]"
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
                f"${item['budget']:,.2f}",
                f"[#ef4444]${item['actual']:,.2f}[/]",
                f"[{rem_color}]${remaining:+,.2f}[/]",
                bar,
                key=str(budget_ids.get(item["category"].lower(), item["category"])),
            )

        budget_count = len(items)
        status_pace = f"${summary['daily_pace']:,.2f}/day remaining" if summary["days_remaining"] > 0 else "month ended"
        self.query_one("#budget-status", Static).update(
            f"[dim]{budget_count} budgets  |  {status_pace}  |"
            f"  n: new  d: delete  Enter: edit[/]"
        )

    def _get_selected_budget(self):
        table = self.query_one("#budget-table", DataTable)
        if table.row_count == 0:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        try:
            return int(row_key.value)
        except (ValueError, TypeError):
            return None

    def action_new_budget(self):
        self.app.push_screen(BudgetModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        conn = init_db(DB_PATH)
        set_budget(conn, result["category"], result["amount"])
        conn.close()
        self.app.notify(f"Budget set: {result['category']} ${result['amount']:,.2f}")
        self._refresh_data()

    def action_edit_budget(self):
        table = self.query_one("#budget-table", DataTable)
        if table.row_count == 0:
            self.app.notify("No budget selected", severity="warning")
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        # Find the budget data from table row
        conn = init_db(DB_PATH)
        items = budget_vs_actual(conn, self._month, account_ids=self.app.active_account_ids)
        conn.close()
        row_idx = table.cursor_coordinate.row
        if row_idx < len(items):
            item = items[row_idx]
            self.app.push_screen(
                BudgetModal(budget=item),
                callback=self._on_modal_result,
            )

    def action_delete_budget(self):
        budget_id = self._get_selected_budget()
        if budget_id is None:
            self.app.notify("No budget selected", severity="warning")
            return
        conn = init_db(DB_PATH)
        delete_budget(conn, budget_id)
        conn.close()
        self.app.notify("Budget deleted")
        self._refresh_data()
