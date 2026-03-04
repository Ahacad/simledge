"""Chart rendering helpers using plotext."""

import plotext as plt
from rich.text import Text

TEAL = (45, 212, 191)
GREEN = (34, 197, 94)
RED = (239, 68, 68)


def _dollar_yticks(values):
    """Set Y-axis ticks formatted as dollars."""
    if not values:
        return
    max_val = max(abs(v) for v in values)
    min_val = min(values)

    def fmt(v):
        if max_val >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        elif max_val >= 10_000:
            return f"${v / 1_000:.0f}k"
        elif max_val >= 1_000:
            return f"${v / 1_000:.1f}k"
        return f"${v:,.0f}"

    span = max_val - min_val
    if span == 0:
        plt.yticks([max_val], [fmt(max_val)])
        return
    step = span / 4
    ticks = [min_val + step * i for i in range(5)]
    plt.yticks(ticks, [fmt(v) for v in ticks])


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
    """Render a bar chart, return Rich Text."""
    if not values:
        return Text("No data")
    plt.clear_figure()
    plt.theme("dark")
    plt.bar(labels, values, color=color)
    _dollar_yticks(values)
    plt.plotsize(width, height)
    canvas = plt.build()
    return Text.from_ansi(canvas)
