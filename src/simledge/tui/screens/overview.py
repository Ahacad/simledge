"""Overview screen — monthly summary, category bars, recent transactions."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Static

from simledge.analysis import (
    daily_average_spending,
    income_by_category,
    monthly_summary,
    recent_transactions,
    spending_by_category_grouped,
    spending_trend,
    top_merchants,
    uncategorized_count,
    yoy_comparison,
    ytd_comparison,
)
from simledge.budget import budget_vs_actual, total_budget_summary
from simledge.config import BUDGETS_PATH, DB_PATH
from simledge.db import get_last_sync, init_db
from simledge.goals import all_goals_progress
from simledge.tui.formatting import format_dollar
from simledge.tui.widgets.navbar import NavBar
from simledge.watchlist import all_watchlist_spending, get_watchlists


class OverviewScreen(Screen):
    BINDINGS = [
        Binding("h", "prev_month", "Prev month", show=False),
        Binding("left", "prev_month", "Prev month", show=False),
        Binding("l", "next_month", "Next month", show=False),
        Binding("right", "next_month", "Next month", show=False),
        Binding("t", "goto_today", "Today", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield NavBar("overview")
        with VerticalScroll():
            yield Vertical(Static("", id="summary-content"), id="summary-panel", classes="panel")
            yield Vertical(
                Static("", id="spending-trend-content"),
                id="spending-trend-panel",
                classes="panel",
            )
            yield Vertical(Static("", id="category-content"), id="category-panel", classes="panel")
            yield Vertical(
                Static("", id="merchants-content"), id="merchants-panel", classes="panel"
            )
            yield Vertical(
                Static("", id="budget-overview-content"),
                id="budget-overview-panel",
                classes="panel",
            )
            yield Vertical(Static("", id="cashflow-content"), id="cashflow-panel", classes="panel")
            yield Vertical(Static("", id="yoy-content"), id="yoy-panel", classes="panel")
            yield Vertical(
                Static("", id="goals-overview-content"), id="goals-overview-panel", classes="panel"
            )
            yield Vertical(
                Static("", id="watchlist-overview-content"),
                id="watchlist-overview-panel",
                classes="panel",
            )
            yield Vertical(
                DataTable(id="recent-table"),
                Static("", id="sync-status"),
                id="recent-panel",
                classes="panel",
            )

    def on_mount(self):
        self._month = datetime.now().strftime("%Y-%m")
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
        conn = init_db(DB_PATH)
        month = self._month
        month_display = datetime.strptime(month, "%Y-%m").strftime("%B %Y")

        account_ids = self.app.active_account_ids
        summary = monthly_summary(conn, month, account_ids=account_ids)
        categories = spending_by_category_grouped(conn, month, account_ids=account_ids)
        inc_cats = income_by_category(conn, month, account_ids=account_ids)
        budget_items = budget_vs_actual(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
        budget_summary = (
            total_budget_summary(conn, month, path=BUDGETS_PATH, account_ids=account_ids)
            if budget_items
            else None
        )
        yoy = yoy_comparison(conn, month, account_ids=account_ids)
        ytd = ytd_comparison(conn, account_ids=account_ids)
        goals_progress = all_goals_progress(conn)
        watchlists_exist = bool(get_watchlists(conn))
        wl_items = (
            all_watchlist_spending(conn, month, account_ids=account_ids) if watchlists_exist else []
        )
        trend = spending_trend(conn, months=6, account_ids=account_ids)
        merchants = top_merchants(conn, month, limit=5, account_ids=account_ids)
        uncat_count = uncategorized_count(conn, month, account_ids=account_ids)
        daily_avg = daily_average_spending(conn, month, account_ids=account_ids)
        recent = recent_transactions(conn, limit=20, account_ids=account_ids)
        last_sync = get_last_sync(conn)
        txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()

        # Panel titles
        self.query_one("#summary-panel").border_title = month_display
        self.query_one("#category-panel").border_title = "Categories"
        recent_count = min(len(recent), 20)
        self.query_one("#recent-panel").border_title = f"Recent ({recent_count})"

        # Summary
        m = self.app.privacy_mode
        spending = abs(summary["total_spending"])
        income = summary["total_income"]
        net = summary["net"]
        net_color = "[#22c55e]" if net >= 0 else "[#ef4444]"
        income_detail = ""
        if len(inc_cats) > 1:
            top_sources = " \u00b7 ".join(
                f"{c['category']} {format_dollar(c['total'], masked=m)}" for c in inc_cats[:3]
            )
            income_detail = f"\n[dim]  ({top_sources})[/]"
        summary_lines = (
            f"[bold]Spending:[/] [#ef4444]{format_dollar(spending, masked=m)}[/]"
            f"    [bold]Income:[/] [#22c55e]{format_dollar(income, masked=m)}[/]"
            f"    [bold]Net:[/] {net_color}{format_dollar(net, signed=True, masked=m)}[/]"
            + income_detail
            + f"\n[bold]Daily avg:[/] [dim]{format_dollar(daily_avg, masked=m)}[/]"
        )
        if uncat_count > 0:
            summary_lines += f"    [bold][#eab308]{uncat_count} uncategorized[/][/]"
        self.query_one("#summary-content", Static).update(summary_lines)

        # Category bars (hierarchical)
        if categories:
            total_spend = sum(abs(c["total"]) for c in categories)
            max_pct = max(
                (abs(c["total"]) / total_spend * 100) if total_spend else 0 for c in categories
            )
            bar_width = 25
            bar_char = "\u2588"
            empty_char = "\u2591"

            lines = []
            for c in categories:
                cat = c["category"]
                amt = abs(c["total"])
                pct = (amt / total_spend * 100) if total_spend else 0
                filled = int(bar_width * (pct / max_pct)) if max_pct > 0 else 0
                bar = f"[#2dd4bf]{bar_char * filled}[/][#333]{empty_char * (bar_width - filled)}[/]"
                cat_padded = f"{cat:<18}"
                lines.append(
                    f"[#2dd4bf]{cat_padded}[/] [bold]{format_dollar(amt, masked=m):>10}[/]  {bar}  [dim]{pct:>5.1f}%[/]"
                )
                for child in c.get("children", []):
                    child_name = child["category"].split(":", 1)[1]
                    child_amt = abs(child["total"])
                    child_pct = (child_amt / total_spend * 100) if total_spend else 0
                    child_filled = int(bar_width * (child_pct / max_pct)) if max_pct > 0 else 0
                    child_bar = f"[#1a9985]{bar_char * child_filled}[/][#333]{empty_char * (bar_width - child_filled)}[/]"
                    child_padded = f"{child_name:<16}"
                    lines.append(
                        f"  [#5eead4]{child_padded}[/] [bold]{format_dollar(child_amt, masked=m):>10}[/]  {child_bar}  [dim]{child_pct:>5.1f}%[/]"
                    )
            self.query_one("#category-content", Static).update("\n".join(lines))
        else:
            self.query_one("#category-content", Static).update(
                "[dim]No spending data this month[/]"
            )

        # Spending trend (last 6 months mini bar chart)
        trend_panel = self.query_one("#spending-trend-panel")
        if len(trend) >= 2:
            trend_panel.border_title = "Spending Trend (6mo)"
            trend_panel.display = True
            bar_char = "\u2588"
            max_trend = max(abs(t["total"]) for t in trend) or 1
            tw = 20
            tlines = []
            for t in trend:
                label = t["month"][2:]  # "24-01" from "2024-01"
                amt = abs(t["total"])
                filled = int(tw * amt / max_trend)
                is_current = t["month"] == month
                color = "#2dd4bf" if is_current else "#1a9985"
                bar = f"[{color}]{bar_char * filled}[/]"
                tlines.append(f"{label}  {bar} {format_dollar(amt, masked=m)}")
            self.query_one("#spending-trend-content", Static).update("\n".join(tlines))
        else:
            trend_panel.display = False

        # Top merchants
        merchants_panel = self.query_one("#merchants-panel")
        if merchants:
            merchants_panel.border_title = "Top Merchants"
            merchants_panel.display = True
            mlines = []
            for mc in merchants:
                mlines.append(
                    f"[#2dd4bf]{mc['merchant'][:30]:<30}[/]  "
                    f"[#ef4444]{format_dollar(abs(mc['total']), masked=m):>10}[/]  "
                    f"[dim]{mc['count']} txns[/]"
                )
            self.query_one("#merchants-content", Static).update("\n".join(mlines))
        else:
            merchants_panel.display = False

        # Budget overview (only if budgets exist)
        budget_panel = self.query_one("#budget-overview-panel")
        if budget_items:
            budget_panel.border_title = "Budget"
            budget_panel.display = True
            bar_char_b = "\u2588"
            empty_char_b = "\u2591"
            bw = 20
            blines = []
            alert_items = [i for i in budget_items if i["pct_used"] >= 80]
            show_items = alert_items if alert_items else budget_items[:3]
            for item in show_items:
                pct = item["pct_used"]
                filled = min(int(bw * pct / 100), bw)
                if pct > 100:
                    color = "#ef4444"
                    warn = " \u26a0"
                elif pct >= 80:
                    color = "#eab308"
                    warn = ""
                else:
                    color = "#22c55e"
                    warn = ""
                bar = f"[{color}]{bar_char_b * filled}[/][#333]{empty_char_b * (bw - filled)}[/]"
                blines.append(f"{item['category']:<14} {bar} {pct:>5.1f}%{warn}")
            pace = budget_summary["daily_pace"] if budget_summary["days_remaining"] > 0 else 0
            remaining = budget_summary["total_remaining"]
            rem_color = "#22c55e" if remaining >= 0 else "#ef4444"
            blines.append(
                f"\n[{rem_color}]{format_dollar(remaining, signed=True, masked=m)} remaining[/] \u00b7 {format_dollar(pace, masked=m)}/day pace"
            )
            self.query_one("#budget-overview-content", Static).update("\n".join(blines))
        else:
            budget_panel.display = False

        # Cash flow waterfall
        cashflow_panel = self.query_one("#cashflow-panel")
        income = summary["total_income"]
        total_spending = abs(summary["total_spending"])
        if income > 0 and budget_summary:
            cashflow_panel.border_title = "Cash Flow"
            cashflow_panel.display = True
            budgeted_spending = budget_summary["total_actual"]
            unbudgeted_spending = budget_summary["unbudgeted_spending"]
            surplus = income - total_spending

            # Waterfall bars
            max_val = max(income, total_spending, 1)
            bw = 30
            bar_char = "\u2588"

            def _bar(val, color):
                filled = int(bw * min(abs(val), max_val) / max_val)
                return f"[{color}]{bar_char * filled}[/]"

            surplus_color = "#22c55e" if surplus >= 0 else "#ef4444"
            clines = [
                f"  Income            {_bar(income, '#22c55e')}  {format_dollar(income, masked=m)}",
                f"  Budgeted spend    {_bar(budgeted_spending, '#ef4444')}  {format_dollar(budgeted_spending, masked=m)}",
                f"  Unbudgeted spend  {_bar(unbudgeted_spending, '#eab308')}  {format_dollar(unbudgeted_spending, masked=m)}",
                f"  [bold]Surplus           {_bar(abs(surplus), surplus_color)}  [{surplus_color}]{format_dollar(surplus, signed=True, masked=m)}[/][/]",
            ]

            # Goal feasibility
            if goals_progress:
                clines.append("")
                if surplus > 0:
                    for g in goals_progress:
                        if g["monthly_needed"] is not None and g["remaining"] > 0:
                            months = g["remaining"] / surplus if surplus > 0 else float("inf")
                            icon = (
                                "[#22c55e]\u2713[/]"
                                if surplus >= g["monthly_needed"]
                                else "[#ef4444]\u2717[/]"
                            )
                            clines.append(
                                f"  {icon} {g['name']}: need {format_dollar(g['monthly_needed'], masked=m)}/mo"
                                f" \u2014 {months:.0f}mo at current surplus"
                            )
                        elif g["remaining"] == 0:
                            clines.append(f"  [#22c55e]\u2713[/] {g['name']}: [#22c55e]reached![/]")
                else:
                    clines.append("  [#ef4444]Deficit — no surplus for goals[/]")

            self.query_one("#cashflow-content", Static).update("\n".join(clines))
        else:
            cashflow_panel.display = False

        # Year-over-Year panel
        yoy_panel = self.query_one("#yoy-panel")
        has_prev = yoy["previous_spending"] != 0 or yoy["previous_income"] != 0
        if has_prev:
            yoy_panel.border_title = "Year over Year"
            yoy_panel.display = True
            prev_month_name = datetime.strptime(yoy["previous_month"], "%Y-%m").strftime("%b %Y")
            ylines = [f"vs. {prev_month_name}:"]

            # Spending line
            prev_s = abs(yoy["previous_spending"])
            cur_s = abs(yoy["current_spending"])
            if yoy["spending_change_pct"] is not None:
                s_pct = yoy["spending_change_pct"]
                # Less spending = good (green down arrow)
                if s_pct < 0:
                    s_arrow, s_color = "\u25bc", "#22c55e"
                elif s_pct > 0:
                    s_arrow, s_color = "\u25b2", "#ef4444"
                else:
                    s_arrow, s_color = "\u2014", "dim"
                ylines.append(
                    f"Spending  {format_dollar(prev_s, masked=m)} \u2192 {format_dollar(cur_s, masked=m)}   [{s_color}]{s_arrow} {abs(s_pct):.1f}%[/]"
                )
            else:
                ylines.append(f"Spending  {format_dollar(cur_s, masked=m)}")

            # Income line
            prev_i = yoy["previous_income"]
            cur_i = yoy["current_income"]
            if yoy["income_change_pct"] is not None:
                i_pct = yoy["income_change_pct"]
                # More income = good (green up arrow)
                if i_pct > 0:
                    i_arrow, i_color = "\u25b2", "#22c55e"
                elif i_pct < 0:
                    i_arrow, i_color = "\u25bc", "#ef4444"
                else:
                    i_arrow, i_color = "\u2014", "dim"
                ylines.append(
                    f"Income    {format_dollar(prev_i, masked=m)} \u2192 {format_dollar(cur_i, masked=m)}   [{i_color}]{i_arrow} {abs(i_pct):.1f}%[/]"
                )
            else:
                ylines.append(f"Income    {format_dollar(cur_i, masked=m)}")

            # YTD line
            if ytd["previous_spending"] != 0:
                ytd_cur = abs(ytd["current_spending"])
                ytd_prev = abs(ytd["previous_spending"])
                ytd_pct = ytd["spending_change_pct"]
                if ytd_pct is not None:
                    ytd_arrow = "\u25bc" if ytd_pct < 0 else "\u25b2"
                    ytd_color = "#22c55e" if ytd_pct < 0 else "#ef4444"
                    ylines.append(
                        f"\nYTD: {format_dollar(ytd_cur, masked=m)} spent (vs {format_dollar(ytd_prev, masked=m)} last year, [{ytd_color}]{ytd_arrow} {abs(ytd_pct):.1f}%[/])"
                    )

            self.query_one("#yoy-content", Static).update("\n".join(ylines))
        else:
            yoy_panel.display = False

        # Goals panel (compact — only if goals exist)
        goals_panel = self.query_one("#goals-overview-panel")
        if goals_progress:
            goals_panel.border_title = "Goals"
            goals_panel.display = True
            bar_char = "\u2588"
            empty_char = "\u2591"
            glines = []
            for g in goals_progress:
                pct = g["pct_complete"]
                bw = 20
                filled = int(bw * min(pct, 100) / 100)
                color = "#22c55e" if pct >= 100 else "#2dd4bf" if pct >= 50 else "#ef4444"
                bar = f"[{color}]{bar_char * filled}[/][#333]{empty_char * (bw - filled)}[/]"
                glines.append(f"{g['name']:<16} {bar}  {pct:.0f}%")
            self.query_one("#goals-overview-content", Static).update("\n".join(glines))
        else:
            goals_panel.display = False

        # Watchlist overview panel
        wl_panel = self.query_one("#watchlist-overview-panel")
        if wl_items:
            wl_panel.border_title = "Watchlists"
            wl_panel.display = True
            bar_char = "\u2588"
            empty_char = "\u2591"
            bw = 20
            wlines = []
            show_items = wl_items[:5]
            for item in show_items:
                name = item["name"]
                if item["monthly_target"]:
                    pct = item["pct_used"]
                    filled = min(int(bw * pct / 100), bw)
                    if pct > 100:
                        color = "#ef4444"
                    elif pct >= 80:
                        color = "#eab308"
                    else:
                        color = "#22c55e"
                    bar = f"[{color}]{bar_char * filled}[/][#333]{empty_char * (bw - filled)}[/]"
                    warn = " \u26a0" if item["projected_month_end"] > item["monthly_target"] else ""
                    wlines.append(f"{name:<14} {bar} {pct:>5.1f}%{warn}")
                else:
                    wlines.append(
                        f"{name:<14} {format_dollar(item['actual'], masked=m)} \u00b7 {item['transaction_count']} txns"
                    )
            if len(wl_items) > 5:
                wlines.append(f"[dim]... and {len(wl_items) - 5} more (press 0)[/]")
            self.query_one("#watchlist-overview-content", Static).update("\n".join(wlines))
        else:
            wl_panel.display = False

        # Recent transactions
        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Date", "Description", "Category", "Amount")
        for t in recent:
            color = "[#22c55e]" if t["amount"] > 0 else "[#ef4444]"
            table.add_row(
                t["posted"],
                t["description"][:30],
                t["category"] or "\u2014",
                f"{color}{format_dollar(t['amount'], signed=True, masked=m)}[/]",
            )

        # Sync status
        self.query_one("#sync-status", Static).update(
            f"[dim]Last sync: {last_sync or 'never'}  \u2502  {txn_count} transactions[/]"
        )
