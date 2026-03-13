"""Goals screen — savings goals with progress tracking."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Select, Static

from simledge.analysis import account_summary
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.goals import (
    all_goals_progress,
    create_goal,
    delete_goal,
    get_goals,
    update_goal,
)
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar


class GoalModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    _NONE = "__none__"

    def __init__(self, goal=None, accounts=None):
        super().__init__()
        self._goal = goal
        self._accounts = accounts or []

    def compose(self) -> ComposeResult:
        title = "Edit Goal" if self._goal else "New Goal"
        with Middle(), Center(), Vertical(id="goal-modal-box"):
            yield Static(f"[bold]{title}[/]", id="goal-modal-title")
            yield Input(
                placeholder="Goal name",
                value=self._goal["name"] if self._goal else "",
                id="goal-name",
            )
            yield Input(
                placeholder="Target amount",
                value=str(self._goal["target_amount"]) if self._goal else "",
                id="goal-target",
            )
            yield Input(
                placeholder="Target date (YYYY-MM-DD, optional)",
                value=self._goal["target_date"] or "" if self._goal else "",
                id="goal-date",
            )
            acct_options = [
                (f"{a['display_name'] or a['name']} ({a['institution']})", a["id"])
                for a in self._accounts
            ]
            acct_options.insert(0, ("(None — no linked account)", self._NONE))
            init_acct = (
                self._goal["account_id"]
                if self._goal and self._goal.get("account_id")
                else self._NONE
            )
            yield Select(
                acct_options,
                value=init_acct,
                prompt="Link account (optional)...",
                id="goal-account",
            )
            yield Static(
                "[dim]Name: required  |  Target: positive number  |  Date: YYYY-MM-DD\n"
                "Account: select to auto-track balance  |  Enter: save  Esc: cancel[/]",
                id="goal-modal-hint",
            )

    def on_mount(self):
        self.query_one("#goal-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        name = self.query_one("#goal-name", Input).value.strip()
        target_str = self.query_one("#goal-target", Input).value.strip()
        date_str = self.query_one("#goal-date", Input).value.strip()
        acct_select = self.query_one("#goal-account", Select)
        account_id = acct_select.value if acct_select.value != self._NONE else None

        if not name:
            self.app.notify("Name is required", severity="error")
            return
        if len(name) > 100:
            self.app.notify("Name too long (max 100 chars)", severity="error")
            return
        try:
            target = float(target_str)
            if target <= 0:
                raise ValueError
        except ValueError:
            self.app.notify("Target must be a positive number", severity="error")
            return
        if date_str:
            import re

            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                self.app.notify("Date must be YYYY-MM-DD format", severity="error")
                return

        result = {"name": name, "target_amount": target}
        result["target_date"] = date_str if date_str else None
        result["account_id"] = account_id

        if self._goal:
            result["id"] = self._goal["id"]

        self.dismiss(result)

    def action_cancel(self):
        self.dismiss(None)


def _build_progress_bar(pct, width=22):
    filled = int(width * min(pct, 100) / 100)
    bar_char = "\u2588"
    empty_char = "\u2591"
    if pct >= 100:
        color = "#22c55e"
    elif pct >= 50:
        color = "#2dd4bf"
    else:
        color = "#ef4444"
    return f"[{color}]{bar_char * filled}[/][#333]{empty_char * (width - filled)}[/]"


class GoalsScreen(Screen):
    BINDINGS = [
        Binding("n", "new_goal", "New", priority=True),
        Binding("d", "delete_goal", "Delete", priority=True),
        Binding("enter", "edit_goal", "Edit", priority=True),
        Binding("j", "select_next", "Next", show=False),
        Binding("k", "select_prev", "Prev", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("up", "select_prev", "Prev", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("goals")
        with VerticalScroll(id="goals-scroll"):
            yield Vertical(Static("", id="goals-content"), id="goals-panel", classes="panel")
            yield Static("", id="goals-status")

    def on_mount(self):
        self._selected_idx = 0
        self.query_one("#goals-panel").border_title = "Savings Goals"
        self._refresh_data()

    def on_screen_resume(self):
        self._refresh_data()

    def _refresh_data(self):
        m = self.app.privacy_mode
        conn = init_db(DB_PATH)
        progress = all_goals_progress(conn)
        conn.close()

        if not progress:
            self.query_one("#goals-content", Static).update(
                "[dim]No goals yet. Press n to create one.[/]"
            )
            self.query_one("#goals-status", Static).update("[dim]0 goals  |  n: new[/]")
            return

        if progress:
            self._selected_idx = min(self._selected_idx, len(progress) - 1)

        lines = []
        for i, g in enumerate(progress):
            pct = g["pct_complete"]
            bar = _build_progress_bar(pct)
            current = g["current_amount"]
            target = g["target_amount"]

            prefix = "[bold #2dd4bf]>[/] " if i == self._selected_idx else "  "
            lines.append(
                f"{prefix}[bold]{g['name']}[/]"
                f"     [#2dd4bf]{format_dollar(current, masked=m)}[/] / {format_dollar(target, masked=m)}"
            )
            lines.append(f"  {bar}  {pct:.0f}%")

            if g["monthly_needed"] is not None:
                td = g["target_date"]
                month_label = td[:7] if td else ""
                lines.append(
                    f"  [dim]Need {format_dollar(g['monthly_needed'], masked=m)}/mo to hit {month_label}[/]"
                )
            elif not g["linked"]:
                lines.append("  [dim]Link an account to track progress[/]")

            lines.append("")

        self.query_one("#goals-content", Static).update("\n".join(lines).rstrip())
        self.query_one("#goals-status", Static).update(
            f"[dim]{len(progress)} goals  |  n: new  d: delete  Enter: edit[/]"
        )

    def _get_accounts(self):
        conn = init_db(DB_PATH)
        accounts = account_summary(conn)
        conn.close()
        return accounts

    def action_new_goal(self):
        self.app.push_screen(
            GoalModal(accounts=self._get_accounts()), callback=self._on_modal_result
        )

    def _on_modal_result(self, result):
        if result is None:
            return
        conn = init_db(DB_PATH)
        if "id" in result:
            update_goal(
                conn,
                result["id"],
                name=result["name"],
                target_amount=result["target_amount"],
                target_date=result.get("target_date"),
                account_id=result.get("account_id"),
            )
            self.app.notify(f"Goal updated: {result['name']}")
        else:
            account_id = result.get("account_id")
            create_goal(
                conn,
                result["name"],
                result["target_amount"],
                target_date=result.get("target_date"),
                account_id=account_id,
            )
            self.app.notify(f"Goal created: {result['name']}")
        conn.close()
        self._refresh_data()

    def action_select_next(self):
        conn = init_db(DB_PATH)
        goals = get_goals(conn)
        conn.close()
        if goals and self._selected_idx < len(goals) - 1:
            self._selected_idx += 1
            self._refresh_data()

    def action_select_prev(self):
        if self._selected_idx > 0:
            self._selected_idx -= 1
            self._refresh_data()

    def action_edit_goal(self):
        conn = init_db(DB_PATH)
        goals = get_goals(conn)
        conn.close()
        if not goals:
            self.app.notify("No goals to edit", severity="warning")
            return
        idx = min(self._selected_idx, len(goals) - 1)
        goal = goals[idx]
        self.app.push_screen(
            GoalModal(goal=goal, accounts=self._get_accounts()), callback=self._on_modal_result
        )

    def action_delete_goal(self):
        conn = init_db(DB_PATH)
        goals = get_goals(conn)
        if not goals:
            conn.close()
            self.app.notify("No goals to delete", severity="warning")
            return
        idx = min(self._selected_idx, len(goals) - 1)
        goal = goals[idx]
        delete_goal(conn, goal["id"])
        conn.close()
        self.app.notify(f"Goal deleted: {goal['name']}")
        self._selected_idx = max(0, self._selected_idx - 1)
        self._refresh_data()
