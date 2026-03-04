"""Bills screen — recurring transaction detection and display."""

import calendar as cal_mod
from datetime import date, datetime, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.recurring import detect_recurring, calendar_bills
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar


class RecurringScreen(Screen):
    BINDINGS = [
        Binding("v", "toggle_view", "Toggle view", show=False),
        Binding("h,left", "prev_month", "Prev month", show=False),
        Binding("l,right", "next_month", "Next month", show=False),
        Binding("t", "today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("recurring")
        with VerticalScroll(id="recurring-scroll"):
            with Vertical(id="bills-panel", classes="panel"):
                yield DataTable(id="bills-table")
            with Vertical(id="calendar-grid-panel", classes="panel"):
                yield Static("", id="calendar-grid")
            with Vertical(id="calendar-details-panel", classes="panel"):
                yield Static("", id="calendar-details")
            with Vertical(id="bills-summary", classes="panel"):
                yield Static("", id="bills-summary-text")

    def on_mount(self):
        today = date.today()
        self._month = today.strftime("%Y-%m")
        self._view = "list"
        self.query_one("#bills-panel").border_title = "Bills & Subscriptions"
        self.query_one("#bills-summary").border_title = "Summary"
        self._refresh_data()
        self.query_one("#bills-table", DataTable).focus()

    def on_screen_resume(self):
        if self._view == "list":
            self.query_one("#bills-table", DataTable).focus()

    def action_toggle_view(self):
        self._view = "calendar" if self._view == "list" else "list"
        self._refresh_data()

    def action_prev_month(self):
        y, m = int(self._month[:4]), int(self._month[5:7])
        m -= 1
        if m < 1:
            m, y = 12, y - 1
        self._month = f"{y:04d}-{m:02d}"
        self._refresh_data()

    def action_next_month(self):
        y, m = int(self._month[:4]), int(self._month[5:7])
        m += 1
        if m > 12:
            m, y = 1, y + 1
        self._month = f"{y:04d}-{m:02d}"
        self._refresh_data()

    def action_today(self):
        self._month = date.today().strftime("%Y-%m")
        self._refresh_data()

    def _refresh_data(self):
        if self._view == "list":
            self._show_list_view()
        else:
            self._show_calendar_view()

    def _show_list_view(self):
        # Show list panels, hide calendar panels
        self.query_one("#bills-panel").display = True
        self.query_one("#calendar-grid-panel").display = False
        self.query_one("#calendar-details-panel").display = False

        conn = init_db(DB_PATH)
        items = detect_recurring(conn)
        conn.close()

        table = self.query_one("#bills-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Description", "Amount", "Frequency", "Last", "Next Expected",
            "Account",
        )

        today = datetime.now().date()
        soon = today + timedelta(days=7)
        monthly_total = 0.0
        count = 0

        m = self.app.privacy_mode
        for item in items:
            amt = item["last_amount"]
            amt_str = f"[#ef4444]{format_dollar(abs(amt), masked=m)}[/]"

            try:
                next_dt = datetime.strptime(item["next_expected"], "%Y-%m-%d").date()
                if next_dt <= soon:
                    next_str = f"[yellow]{item['next_expected']}[/]"
                else:
                    next_str = item["next_expected"]
            except (ValueError, TypeError):
                next_str = item["next_expected"]

            freq = item["frequency"].capitalize()

            table.add_row(
                (item["description"] or "")[:30],
                amt_str,
                freq,
                item["last_date"],
                next_str,
                item["account"],
            )
            count += 1

            # Accumulate monthly equivalent
            monthly_amt = abs(amt)
            if item["frequency"] == "weekly":
                monthly_amt *= 4.33
            elif item["frequency"] == "yearly":
                monthly_amt /= 12
            monthly_total += monthly_amt

        annual_total = monthly_total * 12
        summary_lines = [
            f"List view (v to switch) | {count} recurring bills",
            f"[bold]Monthly recurring:[/]  [#ef4444]{format_dollar(monthly_total, masked=m):>11}[/]",
            f"[bold]Annual recurring:[/]   [#ef4444]{format_dollar(annual_total, masked=m):>11}[/]",
        ]
        self.query_one("#bills-summary-text", Static).update(
            "\n".join(summary_lines)
        )

    def _show_calendar_view(self):
        # Hide list, show calendar panels
        self.query_one("#bills-panel").display = False
        self.query_one("#calendar-grid-panel").display = True
        self.query_one("#calendar-details-panel").display = True

        conn = init_db(DB_PATH)
        bills = calendar_bills(conn, self._month)
        conn.close()

        y, m = int(self._month[:4]), int(self._month[5:7])
        month_name = cal_mod.month_name[m]

        # Build calendar grid
        self.query_one("#calendar-grid-panel").border_title = f"{month_name} {y}"
        grid = self._build_grid(y, m, bills)
        self.query_one("#calendar-grid", Static).update(grid)

        # Build bill details
        self.query_one("#calendar-details-panel").border_title = "Bills"
        details = self._build_details(bills)
        self.query_one("#calendar-details", Static).update(details)

        # Summary
        paid = [b for b in bills if b["status"] == "paid"]
        overdue = [b for b in bills if b["status"] == "overdue"]
        upcoming = [b for b in bills if b["status"] == "upcoming"]

        paid_total = sum(abs(b.get("actual_amount") or b["expected_amount"]) for b in paid)
        due_total = sum(abs(b["expected_amount"]) for b in upcoming)
        overdue_total = sum(abs(b["expected_amount"]) for b in overdue)

        summary = (
            f"Calendar: {month_name} {y} (v to switch) | "
            f"{len(paid)} paid · {len(overdue)} overdue · {len(upcoming)} upcoming"
        )
        m = self.app.privacy_mode
        totals = (
            f"Paid: {format_dollar(paid_total, masked=m)} · Due: {format_dollar(due_total, masked=m)} · Overdue: {format_dollar(overdue_total, masked=m)}"
        )
        self.query_one("#bills-summary-text", Static).update(f"{summary}\n{totals}")

    def _build_grid(self, year, month, bills):
        today = date.today()
        # Map day -> status marker
        day_status = {}
        for b in bills:
            day = b["day"]
            status = b["status"]
            # Priority: overdue > upcoming > paid
            priority = {"overdue": 0, "upcoming": 1, "paid": 2}
            if day not in day_status or priority.get(status, 3) < priority.get(day_status[day], 3):
                day_status[day] = status

        status_markers = {
            "paid": ("[#22c55e]●", "[/]"),
            "upcoming": ("[#eab308]◐", "[/]"),
            "overdue": ("[#ef4444]○", "[/]"),
        }

        lines = ["Mon   Tue   Wed   Thu   Fri   Sat   Sun"]
        weeks = cal_mod.monthcalendar(year, month)

        for week in weeks:
            cells = []
            for day in week:
                if day == 0:
                    cells.append("      ")
                else:
                    is_today = (year == today.year and month == today.month and day == today.day)
                    if day in day_status:
                        pre, post = status_markers[day_status[day]]
                        s = f"{pre}{day:>2}{post}"
                    elif is_today:
                        s = f"[bold]{day:>2}[/]"
                    else:
                        s = f"{day:>2}"

                    # Pad to 6 chars visual width (markers add markup but same visual width)
                    if day in day_status:
                        s = f"{pre}{day:>2}{post}  "
                    elif is_today:
                        s = f"[bold]{day:>2}[/]    "
                    else:
                        s = f"{day:>2}    "
                    cells.append(s)

            lines.append("".join(cells))

        return "\n".join(lines)

    def _build_details(self, bills):
        if not bills:
            return "[dim]No bills expected this month.[/]"

        today = date.today()
        lines = []
        for b in bills:
            status = b["status"]
            amt = abs(b["expected_amount"])

            if status == "paid":
                color = "#22c55e"
                marker = "●"
                status_text = "paid"
            elif status == "overdue":
                color = "#ef4444"
                marker = "○"
                try:
                    bill_date = datetime.strptime(b["date"], "%Y-%m-%d").date()
                    days_late = (today - bill_date).days
                    status_text = f"{days_late} days late"
                except (ValueError, TypeError):
                    status_text = "overdue"
            else:
                color = "#eab308"
                marker = "◐"
                try:
                    bill_date = datetime.strptime(b["date"], "%Y-%m-%d").date()
                    days_until = (bill_date - today).days
                    status_text = f"due in {days_until}d"
                except (ValueError, TypeError):
                    status_text = "upcoming"

            desc = (b["description"] or "")[:20]
            m = self.app.privacy_mode
            lines.append(
                f"[{color}]{marker} {b['day']:>2}  {desc:<20} {format_dollar(amt, masked=m):>11}   {status_text}[/]"
            )

        return "\n".join(lines)
