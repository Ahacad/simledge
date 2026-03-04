"""Watchlist screen — named spending trackers with targets."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll, Center, Middle
from textual.screen import Screen, ModalScreen
from textual.widgets import Input, Static

from simledge.config import DB_PATH
from simledge.db import init_db
from simledge.watchlist import (
    create_watchlist, get_watchlists, update_watchlist,
    delete_watchlist, all_watchlist_spending,
)
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar


class WatchlistModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, watchlist=None):
        super().__init__()
        self._watchlist = watchlist

    def compose(self) -> ComposeResult:
        title = "Edit Watchlist" if self._watchlist else "New Watchlist"
        w = self._watchlist
        with Middle():
            with Center():
                with Vertical(id="watchlist-modal-box"):
                    yield Static(f"[bold]{title}[/]", id="watchlist-modal-title")
                    yield Input(
                        placeholder="Name",
                        value=w["name"] if w else "",
                        id="wl-name",
                    )
                    yield Input(
                        placeholder="Monthly target (optional)",
                        value=str(w["monthly_target"]) if w and w.get("monthly_target") else "",
                        id="wl-target",
                    )
                    yield Input(
                        placeholder="Filter category (e.g. Food:Coffee)",
                        value=w.get("filter_category") or "" if w else "",
                        id="wl-category",
                    )
                    yield Input(
                        placeholder="Filter tag",
                        value=w.get("filter_tag") or "" if w else "",
                        id="wl-tag",
                    )
                    yield Input(
                        placeholder="Filter description (e.g. %amazon%)",
                        value=w.get("filter_description") or "" if w else "",
                        id="wl-description",
                    )
                    yield Static(
                        "[dim]At least one filter required. Use % for wildcards.\n"
                        "Name: max 100 chars  |  Target: positive number (optional)\n"
                        "Enter: save  Esc: cancel[/]",
                        id="watchlist-modal-hint",
                    )

    def on_mount(self):
        self.query_one("#wl-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        name = self.query_one("#wl-name", Input).value.strip()
        target_str = self.query_one("#wl-target", Input).value.strip()
        fcat = self.query_one("#wl-category", Input).value.strip() or None
        ftag = self.query_one("#wl-tag", Input).value.strip() or None
        fdesc = self.query_one("#wl-description", Input).value.strip() or None

        if not name:
            self.app.notify("Name is required", severity="error")
            return
        if len(name) > 100:
            self.app.notify("Name too long (max 100 chars)", severity="error")
            return

        if not any([fcat, ftag, fdesc]):
            self.app.notify("At least one filter is required", severity="error")
            return

        target = None
        if target_str:
            try:
                target = float(target_str)
                if target <= 0:
                    raise ValueError
            except ValueError:
                self.app.notify("Target must be a positive number", severity="error")
                return

        result = {
            "name": name,
            "monthly_target": target,
            "filter_category": fcat,
            "filter_tag": ftag,
            "filter_description": fdesc,
        }
        if self._watchlist:
            result["id"] = self._watchlist["id"]
        self.dismiss(result)

    def action_cancel(self):
        self.dismiss(None)


def _progress_bar(pct, width=20):
    filled = min(int(width * pct / 100), width)
    bar_char = "\u2588"
    empty_char = "\u2591"
    if pct > 100:
        color = "#ef4444"
    elif pct >= 80:
        color = "#eab308"
    else:
        color = "#22c55e"
    return f"[{color}]{bar_char * filled}[/][#333]{empty_char * (width - filled)}[/]"


class WatchlistScreen(Screen):
    BINDINGS = [
        Binding("n", "new_watchlist", "New", priority=True),
        Binding("d", "delete_watchlist", "Delete", priority=True),
        Binding("enter", "edit_watchlist", "Edit", priority=True),
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("watchlist")
        with Vertical(id="watchlist-summary-panel", classes="panel"):
            yield Static("", id="watchlist-summary-content")
        with VerticalScroll(id="watchlist-scroll"):
            yield Vertical(
                Static("", id="watchlist-cards-content"),
                id="watchlist-cards-panel",
                classes="panel",
            )
        yield Static("", id="watchlist-status")

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
        self._selected_idx = 0
        self.query_one("#watchlist-summary-panel").border_title = "Summary"
        self._refresh_data()

    def on_screen_resume(self):
        self._refresh_data()

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
        m = self.app.privacy_mode
        conn = init_db(DB_PATH)
        month = self._month
        month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        account_ids = self.app.active_account_ids

        items = all_watchlist_spending(conn, month, account_ids=account_ids)
        self._items = items
        conn.close()

        # Summary
        total = len(items)
        on_track = sum(1 for i in items if i["on_track"] is True)
        over = sum(1 for i in items if i["on_track"] is False)
        self.query_one("#watchlist-summary-panel").border_title = f"Summary \u2014 {month_display}"
        self.query_one("#watchlist-summary-content", Static).update(
            f"[bold]{total}[/] watchlists"
            f"    [#22c55e]{on_track} on track[/]"
            f"    [#ef4444]{over} over target[/]"
        )

        # Cards
        self.query_one("#watchlist-cards-panel").border_title = f"Watchlists ({month_display})"
        if not items:
            self.query_one("#watchlist-cards-content", Static).update(
                "[dim]No watchlists yet. Press n to create one.[/]"
            )
            self.query_one("#watchlist-status", Static).update(
                "[dim]0 watchlists  |  n: new[/]"
            )
            return

        # Pre-fetch watchlist definitions for filter display
        conn_wl = init_db(DB_PATH)
        wls = get_watchlists(conn_wl)
        conn_wl.close()
        wl_by_id = {w["id"]: w for w in wls}

        lines = []
        for item in items:
            name = item["name"]
            actual = item["actual"]
            target = item["monthly_target"]
            projected = item["projected_month_end"]
            txn_count = item["transaction_count"]

            if target:
                pct = item["pct_used"]
                warn = ""
                if projected > target:
                    warn = f"  [#eab308]\u26a0 Projected: {format_dollar(projected, masked=m)}[/]"
                lines.append(
                    f"[bold]{name}[/]"
                    f"         {format_dollar(actual, masked=m)} / {format_dollar(target, masked=m)}"
                )
                lines.append(f"{_progress_bar(pct)}  {pct:.0f}%{warn}")
            else:
                lines.append(
                    f"[bold]{name}[/]"
                    f"         {format_dollar(actual, masked=m)} (no target)"
                )

            # Show active filters
            wl = wl_by_id.get(item["id"])
            filters = []
            if wl:
                if wl.get("filter_category"):
                    filters.append(f"cat: {wl['filter_category']}")
                if wl.get("filter_tag"):
                    filters.append(f"tag: {wl['filter_tag']}")
                if wl.get("filter_description"):
                    filters.append(f"desc: {wl['filter_description']}")

            filter_str = " \u00b7 ".join(filters)
            lines.append(f"[dim]{txn_count} transactions \u00b7 {filter_str}[/]")
            lines.append("")

        self.query_one("#watchlist-cards-content", Static).update(
            "\n".join(lines).rstrip()
        )
        self.query_one("#watchlist-status", Static).update(
            f"[dim]{total} watchlists | {on_track} on track | {over} over target"
            f"  |  n: new  d: delete  Enter: edit[/]"
        )

    def action_new_watchlist(self):
        self.app.push_screen(WatchlistModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result):
        if result is None:
            return
        conn = init_db(DB_PATH)
        if "id" in result:
            update_watchlist(
                conn, result["id"],
                name=result["name"],
                monthly_target=result["monthly_target"],
                filter_category=result["filter_category"],
                filter_tag=result["filter_tag"],
                filter_description=result["filter_description"],
            )
            self.app.notify(f"Watchlist updated: {result['name']}")
        else:
            create_watchlist(
                conn, result["name"],
                monthly_target=result["monthly_target"],
                filter_category=result["filter_category"],
                filter_tag=result["filter_tag"],
                filter_description=result["filter_description"],
            )
            self.app.notify(f"Watchlist created: {result['name']}")
        conn.close()
        self._refresh_data()

    def action_edit_watchlist(self):
        conn = init_db(DB_PATH)
        watchlists = get_watchlists(conn)
        conn.close()
        if not watchlists:
            self.app.notify("No watchlists to edit", severity="warning")
            return
        idx = min(self._selected_idx, len(watchlists) - 1)
        self.app.push_screen(
            WatchlistModal(watchlist=watchlists[idx]),
            callback=self._on_modal_result,
        )

    def action_delete_watchlist(self):
        conn = init_db(DB_PATH)
        watchlists = get_watchlists(conn)
        if not watchlists:
            conn.close()
            self.app.notify("No watchlists to delete", severity="warning")
            return
        idx = min(self._selected_idx, len(watchlists) - 1)
        wl = watchlists[idx]
        delete_watchlist(conn, wl["id"])
        conn.close()
        self.app.notify(f"Watchlist deleted: {wl['name']}")
        self._refresh_data()
