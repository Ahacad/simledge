"""Rules screen — manage categorization rules via TOML file."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Input, Static

from simledge.categorize import apply_rules, init_rules, load_rules, save_rules
from simledge.config import DB_PATH, RULES_PATH
from simledge.db import init_db
from simledge.tui.widgets.navbar import NavBar


class RuleModal(ModalScreen):
    """Modal for creating or editing a rule."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, rule=None, index=None):
        super().__init__()
        self._rule = rule
        self._index = index

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
                placeholder="Category (e.g. Food:Groceries)",
                value=self._rule["category"] if self._rule else "",
                id="rule-category",
            )
            yield Input(
                placeholder="Priority (default 0, higher = matched first)",
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
            "index": self._index,
        }
        self.dismiss(result)

    def action_cancel(self):
        self.dismiss(None)


class ConfirmModal(ModalScreen):
    """Yes/no confirmation modal."""

    BINDINGS = [
        Binding("y", "confirm", "Yes", priority=True),
        Binding("n", "cancel", "No", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, message):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Middle(), Center(), Vertical(id="confirm-modal-box"):
            yield Static(f"[bold red]⚠ Warning[/]\n\n{self._message}", id="confirm-msg")
            yield Static("[dim]y: confirm  n/Esc: cancel[/]", id="confirm-hint")

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


class RulesScreen(Screen):
    BINDINGS = [
        Binding("n", "new_rule", "New", priority=True),
        Binding("d", "delete_rule", "Delete", priority=True),
        Binding("enter", "edit_rule", "Edit", priority=True),
        Binding("r", "run_rules", "Apply", priority=True),
        Binding("R", "force_apply_rules", "Force Apply", priority=True),
        Binding("t", "test_rules", "Dry Run", priority=True),
        Binding("i", "init_rules", "Init Defaults", priority=True),
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
        self._rules = load_rules(RULES_PATH)

        table = self.query_one("#rules-table", DataTable)
        table.clear(columns=True)

        total_width = max(80, self.app.size.width - 6)
        fixed = 4 + 8  # # + Priority
        remaining = total_width - fixed
        pat_width = int(remaining * 0.65)
        cat_width = remaining - pat_width
        table.add_column("#", width=4)
        table.add_column("Pattern", width=pat_width)
        table.add_column("Category", width=cat_width)
        table.add_column("Priority", width=8)

        for i, r in enumerate(self._rules):
            table.add_row(
                str(i + 1),
                r["pattern"],
                r["category"],
                str(r["priority"]),
                key=str(i),
            )

        status = f"[dim]{len(self._rules)} rules"
        if not self._rules:
            status += "  |  i: init defaults"
        status += "  |  n: new  d: delete  Enter: edit  r: apply  R: force apply  t: dry run[/]"
        self.query_one("#rules-status", Static).update(status)

    def on_resize(self, event):
        self._load_rules()

    def _get_selected_index(self):
        table = self.query_one("#rules-table", DataTable)
        if table.row_count == 0:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return int(row_key.value)

    def _save_and_reload(self):
        save_rules(RULES_PATH, self._rules)
        self._load_rules()

    def action_new_rule(self):
        self.app.push_screen(RuleModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        rule = {
            "pattern": result["pattern"],
            "category": result["category"],
            "priority": result["priority"],
        }
        idx = result.get("index")
        if idx is not None:
            self._rules[idx] = rule
            self.app.notify(f"Rule updated: {rule['pattern']}")
        else:
            self._rules.append(rule)
            self.app.notify(f"Rule added: {rule['pattern']}")
        self._save_and_reload()

    def action_edit_rule(self):
        idx = self._get_selected_index()
        if idx is None:
            self.app.notify("No rule selected", severity="warning")
            return
        rule = self._rules[idx]
        self.app.push_screen(RuleModal(rule=rule, index=idx), callback=self._on_modal_result)

    def action_delete_rule(self):
        idx = self._get_selected_index()
        if idx is None:
            self.app.notify("No rule selected", severity="warning")
            return
        del self._rules[idx]
        self._save_and_reload()
        self.app.notify("Rule deleted")

    def action_run_rules(self):
        rules = load_rules(RULES_PATH)
        conn = init_db(DB_PATH)
        count = apply_rules(rules, conn)
        conn.close()
        self.app.notify(f"Categorized {count} transactions")

    def action_test_rules(self):
        rules = load_rules(RULES_PATH)
        conn = init_db(DB_PATH)
        count = apply_rules(rules, conn, dry_run=True)
        conn.close()
        self.app.notify(f"Would categorize {count} transactions")

    def action_force_apply_rules(self):
        self.app.push_screen(
            ConfirmModal(
                "This will clear ALL existing categories\n"
                "and re-apply rules from scratch.\n\n"
                "Any manual categorizations will be lost."
            ),
            callback=self._on_force_apply_confirm,
        )

    def _on_force_apply_confirm(self, confirmed):
        if not confirmed:
            return
        rules = load_rules(RULES_PATH)
        conn = init_db(DB_PATH)
        conn.execute("UPDATE transactions SET category = NULL")
        conn.commit()
        count = apply_rules(rules, conn)
        conn.close()
        self.app.notify(f"Reset & re-categorized {count} transactions")

    def action_init_rules(self):
        created = init_rules(RULES_PATH)
        if created:
            self.app.notify("Default rules initialized")
        else:
            self.app.notify("Rules file already exists", severity="warning")
        self._load_rules()
