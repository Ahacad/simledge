"""Rules screen — manage categorization rules."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Input, Static

from simledge.categorize import add_rule, apply_rules, delete_rule, list_rules, update_rule
from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class RuleModal(ModalScreen):
    """Modal for creating or editing a rule."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, rule=None):
        super().__init__()
        self._rule = rule

    def compose(self) -> ComposeResult:
        title = "Edit Rule" if self._rule else "New Rule"
        with Middle(), Center(), Vertical(id="rule-modal-box"):
            yield Static(f"[bold]{title}[/]", id="rule-modal-title")
            yield Input(
                placeholder="Pattern (regex or substring)",
                value=self._rule["pattern"] if self._rule else "",
                id="rule-pattern",
            )
            yield Input(
                placeholder="Category",
                value=self._rule["category"] if self._rule else "",
                id="rule-category",
            )
            yield Input(
                placeholder="Priority (default 0)",
                value=str(self._rule["priority"]) if self._rule else "0",
                id="rule-priority",
            )
            yield Static(
                "[dim]Enter: save  Esc: cancel[/]",
                id="rule-modal-hint",
            )

    def on_mount(self):
        self.query_one("#rule-pattern", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        pattern = self.query_one("#rule-pattern", Input).value.strip()
        category = self.query_one("#rule-category", Input).value.strip()
        priority_str = self.query_one("#rule-priority", Input).value.strip()

        if not pattern or not category:
            self.app.notify("Pattern and category are required", severity="error")
            return

        try:
            priority = int(priority_str) if priority_str else 0
        except ValueError:
            self.app.notify("Priority must be a number", severity="error")
            return

        result = {
            "pattern": pattern,
            "category": category,
            "priority": priority,
        }
        if self._rule:
            result["id"] = self._rule["id"]

        self.dismiss(result)

    def action_cancel(self):
        self.dismiss(None)


class RulesScreen(Screen):
    BINDINGS = [
        Binding("n", "new_rule", "New", priority=True),
        Binding("d", "delete_rule", "Delete", priority=True),
        Binding("enter", "edit_rule", "Edit", priority=True),
        Binding("r", "run_rules", "Apply", priority=True),
        Binding("t", "test_rules", "Dry Run", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("rules")
        with Vertical(id="rules-panel", classes="panel"):
            yield DataTable(id="rules-table")
            yield Static("", id="rules-status")

    def on_mount(self):
        self.query_one("#rules-panel").border_title = "Category Rules"
        self._load_rules()
        self.query_one("#rules-table", DataTable).focus()

    def on_screen_resume(self):
        self._load_rules()
        self.query_one("#rules-table", DataTable).focus()

    def _load_rules(self):
        conn = init_db(DB_PATH)
        rules = list_rules(conn)
        conn.close()

        table = self.query_one("#rules-table", DataTable)
        table.clear(columns=True)
        table.add_columns("#", "Pattern", "Category", "Priority")

        for r in rules:
            table.add_row(
                str(r["id"]),
                r["pattern"],
                r["category"],
                str(r["priority"]),
                key=str(r["id"]),
            )

        self.query_one("#rules-status", Static).update(
            f"[dim]{len(rules)} rules  |  n: new  d: delete  Enter: edit  r: apply  t: dry run[/]"
        )

    def _get_selected_rule_id(self):
        table = self.query_one("#rules-table", DataTable)
        if table.row_count == 0:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return int(row_key.value)

    def action_new_rule(self):
        self.app.push_screen(RuleModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        conn = init_db(DB_PATH)
        if "id" in result:
            update_rule(
                conn, result["id"], result["pattern"], result["category"], result["priority"]
            )
            self.app.notify(f"Rule updated: {result['pattern']}")
        else:
            add_rule(conn, result["pattern"], result["category"], result["priority"])
            self.app.notify(f"Rule added: {result['pattern']}")
        conn.close()
        self._load_rules()

    def action_edit_rule(self):
        rule_id = self._get_selected_rule_id()
        if rule_id is None:
            self.app.notify("No rule selected", severity="warning")
            return
        conn = init_db(DB_PATH)
        rules = list_rules(conn)
        conn.close()
        rule = next((r for r in rules if r["id"] == rule_id), None)
        if rule:
            self.app.push_screen(RuleModal(rule=rule), callback=self._on_modal_result)

    def action_delete_rule(self):
        rule_id = self._get_selected_rule_id()
        if rule_id is None:
            self.app.notify("No rule selected", severity="warning")
            return
        conn = init_db(DB_PATH)
        delete_rule(conn, rule_id)
        conn.close()
        self.app.notify("Rule deleted")
        self._load_rules()

    def action_run_rules(self):
        conn = init_db(DB_PATH)
        count = apply_rules(conn)
        conn.close()
        self.app.notify(f"Categorized {count} transactions")

    def action_test_rules(self):
        conn = init_db(DB_PATH)
        count = apply_rules(conn, dry_run=True)
        conn.close()
        self.app.notify(f"Would categorize {count} transactions")
