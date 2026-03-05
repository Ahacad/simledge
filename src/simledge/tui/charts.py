"""Chart rendering helpers using plotext."""

import plotext as plt
from rich.text import Text

TEAL = (45, 212, 191)
GREEN = (34, 197, 94)
RED = (239, 68, 68)


def _fmt_dollar(v):
    """Dollar format for chart labels — exact, no cents."""
    return f"${v:,.0f}"


def _dollar_yticks(values):
    """Set Y-axis ticks formatted as dollars."""
    if not values:
        return
    max_val = max(abs(v) for v in values)
    min_val = min(values)

    span = max_val - min_val
    if span == 0:
        plt.yticks([max_val], [_fmt_dollar(max_val)])
        return
    step = span / 4
    ticks = [min_val + step * i for i in range(5)]
    plt.yticks(ticks, [_fmt_dollar(v) for v in ticks])


def _sparse_xticks(labels):
    """Show ~6 evenly spaced X labels to avoid crowding."""
    n = len(labels)
    if n <= 7:
        plt.xticks(list(range(1, n + 1)), labels)
        return
    step = max(1, (n - 1) // 5)
    indices = list(range(0, n, step))
    if n - 1 not in indices:
        indices.append(n - 1)
    plt.xticks([i + 1 for i in indices], [labels[i] for i in indices])


def render_line_chart(values, labels, width=80, height=12, color=TEAL):
    """Render a line chart, return Rich Text."""
    if not values:
        return Text("No data")
    plt.clear_figure()
    plt.theme("dark")
    plt.plot(values, marker="braille", color=color)
    _sparse_xticks(labels)
    _dollar_yticks(values)
    plt.plotsize(width, height)
    canvas = plt.build()
    return Text.from_ansi(canvas)


def render_bar_chart(values, labels, width=80, height=12, color=TEAL):
    """Render a bar chart with value labels above each bar, return Rich Text."""
    if not values:
        return Text("No data")
    plt.clear_figure()
    plt.theme("dark")
    plt.bar(labels, values, color=color)
    _dollar_yticks(values)

    # Add value labels above each bar
    max_val = max(abs(v) for v in values) if values else 1
    offset = max_val * 0.03  # small offset above bar top
    for i, v in enumerate(values):
        plt.text(_fmt_dollar(v), i + 1, v + offset, alignment="center", color=color)

    plt.plotsize(width, height + 2)  # extra height for labels
    canvas = plt.build()
    return Text.from_ansi(canvas)


def render_data_table(labels, values, width=80):
    """Render a compact single-row data table below a chart.

    Returns a Rich markup string with labels and values aligned.
    """
    if not labels or not values:
        return ""
    col_width = max(8, width // len(labels))
    header = ""
    row = ""
    for label, val in zip(labels, values, strict=False):
        header += f"[dim]{label:^{col_width}}[/]"
        row += f"[bold]{_fmt_dollar(val):^{col_width}}[/]"
    return f"{header}\n{row}"
