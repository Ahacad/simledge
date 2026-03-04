"""Navigation bar showing available screens."""

from textual.widgets import Static


TABS = [
    ("1", "Overview"),
    ("2", "Transactions"),
    ("3", "Accounts"),
    ("4", "Trends"),
    ("5", "Net Worth"),
    ("6", "Rules"),
    ("7", "Bills"),
    ("8", "Budget"),
    ("9", "Goals"),
    ("0", "Watchlists"),
]


class NavBar(Static):
    """Horizontal tab bar showing screen navigation."""

    def __init__(self, active="overview"):
        super().__init__()
        self._active = active

    def render(self):
        mode_map = {
            "overview": "1",
            "transactions": "2",
            "accounts": "3",
            "trends": "4",
            "networth": "5",
            "rules": "6",
            "recurring": "7",
            "budget": "8",
            "goals": "9",
            "watchlist": "0",
        }
        active_key = mode_map.get(self._active, "1")

        parts = []
        for key, label in TABS:
            if key == active_key:
                parts.append(f"[bold #1a1a2e on #2dd4bf] {key} {label} [/]")
            else:
                parts.append(f"[dim] {key} {label} [/]")

        suffix = "  [dim]? Help  a Filter  q Quit[/]"
        if hasattr(self.app, "active_account_ids") and self.app.active_account_ids is not None:
            suffix = "  [#2dd4bf][filtered][/]" + suffix
        if hasattr(self.app, "privacy_mode") and self.app.privacy_mode:
            suffix = "  [#eab308][private][/]" + suffix
        return "  ".join(parts) + suffix
