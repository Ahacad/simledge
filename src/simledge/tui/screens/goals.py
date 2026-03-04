"""Goals screen — savings goals with progress tracking."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll, Center, Middle
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.goals import (
    create_goal, get_goals, update_goal, delete_goal, all_goals_progress,
)
from simledge.analysis import account_summary
from simledge.tui.widgets.navbar import NavBar


class GoalModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, goal=None):
        super().__init__()
        self._goal = goal

    def compose(self) -> ComposeResult:
        title = "Edit Goal" if self._goal else "New Goal"
        with Middle():
            with Center():
                with Vertical(id="goal-modal-box"):
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
                    yield Input(
                        placeholder="Account name (optional, for auto-tracking)",
                        value="",
                        id="goal-account",
                    )
                    yield Static(
                        "[dim]Enter: save  Esc: cancel[/]",
                        id="goal-modal-hint",
                    )

    def on_mount(self):
        self.query_one("#goal-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        name = self.query_one("#goal-name", Input).value.strip()
        target_str = self.query_one("#goal-target", Input).value.strip()
        date_str = self.query_one("#goal-date", Input).value.strip()
        account_str = self.query_one("#goal-account", Input).value.strip()

        if not name:
            self.app.notify("Name is required", severity="error")
            return
        try:
            target = float(target_str)
            if target <= 0:
                raise ValueError
        except ValueError:
            self.app.notify("Target must be a positive number", severity="error")
            return

        result = {"name": name, "target_amount": target}
        result["target_date"] = date_str if date_str else None
        result["account_name"] = account_str if account_str else None

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
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("goals")
        with VerticalScroll(id="goals-scroll"):
            yield Vertical(Static("", id="goals-content"), id="goals-panel", classes="panel")
            yield Static("", id="goals-status")

    def on_mount(self):
        self.query_one("#goals-panel").border_title = "Savings Goals"
        self._refresh_data()

    def on_screen_resume(self):
        self._refresh_data()

    def _refresh_data(self):
        conn = init_db(DB_PATH)
        progress = all_goals_progress(conn)
        conn.close()

        if not progress:
            self.query_one("#goals-content", Static).update(
                "[dim]No goals yet. Press n to create one.[/]"
            )
            self.query_one("#goals-status", Static).update(
                "[dim]0 goals  |  n: new[/]"
            )
            return

        lines = []
        for g in progress:
            pct = g["pct_complete"]
            bar = _build_progress_bar(pct)
            current = g["current_amount"]
            target = g["target_amount"]

            lines.append(
                f"[bold]{g['name']}[/]"
                f"     [#2dd4bf]${current:,.2f}[/] / ${target:,.2f}"
            )
            lines.append(f"{bar}  {pct:.0f}%")

            if g["monthly_needed"] is not None:
                td = g["target_date"]
                month_label = td[:7] if td else ""
                lines.append(
                    f"[dim]Need ${g['monthly_needed']:,.2f}/mo to hit {month_label}[/]"
                )
            elif not g["linked"]:
                lines.append("[dim]Link an account to track progress[/]")

            lines.append("")

        self.query_one("#goals-content", Static).update("\n".join(lines).rstrip())
        self.query_one("#goals-status", Static).update(
            f"[dim]{len(progress)} goals  |  n: new  d: delete  Enter: edit[/]"
        )

    def _resolve_account_id(self, conn, account_name):
        if not account_name:
            return None
        accounts = account_summary(conn)
        for a in accounts:
            if a["name"].lower() == account_name.lower():
                return a["id"]
        return None

    def action_new_goal(self):
        self.app.push_screen(GoalModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        conn = init_db(DB_PATH)
        if "id" in result:
            update_goal(
                conn, result["id"],
                name=result["name"],
                target_amount=result["target_amount"],
                target_date=result.get("target_date"),
            )
            self.app.notify(f"Goal updated: {result['name']}")
        else:
            account_id = self._resolve_account_id(conn, result.get("account_name"))
            create_goal(
                conn, result["name"], result["target_amount"],
                target_date=result.get("target_date"),
                account_id=account_id,
            )
            self.app.notify(f"Goal created: {result['name']}")
        conn.close()
        self._refresh_data()

    def action_edit_goal(self):
        conn = init_db(DB_PATH)
        goals = get_goals(conn)
        conn.close()
        if not goals:
            self.app.notify("No goals to edit", severity="warning")
            return
        goal = goals[0]
        self.app.push_screen(GoalModal(goal=goal), callback=self._on_modal_result)

    def action_delete_goal(self):
        conn = init_db(DB_PATH)
        goals = get_goals(conn)
        if not goals:
            conn.close()
            self.app.notify("No goals to delete", severity="warning")
            return
        goal = goals[0]
        delete_goal(conn, goal["id"])
        conn.close()
        self.app.notify(f"Goal deleted: {goal['name']}")
        self._refresh_data()
