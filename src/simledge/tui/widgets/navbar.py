"""Navigation bar showing available screens."""

from textual.widgets import Static


TABS = [
    ("1", "Overview"),
    ("2", "Transactions"),
    ("3", "Accounts"),
    ("4", "Trends"),
    ("5", "Net Worth"),
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
        }
        active_key = mode_map.get(self._active, "1")

        parts = []
        for key, label in TABS:
            if key == active_key:
                parts.append(f"[bold reverse] {key} {label} [/]")
            else:
                parts.append(f"[dim] {key} {label} [/]")

        return "  ".join(parts) + "  [dim]? Help  q Quit[/]"
