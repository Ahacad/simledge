"""Category -> color mapping for consistent display across the TUI."""

CATEGORY_COLORS = {
    "Groceries": "#f59e0b",
    "Food": "#fb923c",
    "Housing": "#60a5fa",
    "Transport": "#a78bfa",
    "Shopping": "#f472b6",
    "Entertainment": "#c084fc",
    "Health": "#34d399",
    "Travel": "#38bdf8",
    "Personal": "#fbbf24",
    "Finance": "#94a3b8",
    "Income": "#22c55e",
    "Transfer": "#6b7280",
}

FALLBACK_PALETTE = [
    "#e879f9",
    "#fb7185",
    "#a3e635",
    "#67e8f9",
    "#fda4af",
    "#d8b4fe",
    "#86efac",
    "#fde68a",
    "#7dd3fc",
    "#fdba74",
    "#c4b5fd",
    "#6ee7b7",
    "#fca5a5",
    "#93c5fd",
    "#bef264",
    "#f0abfc",
]


def get_category_color(category):
    """Return a hex color for a category string.

    Extracts parent from "Food:Dining" -> "Food", looks up in curated map,
    falls back to deterministic hash into FALLBACK_PALETTE.
    """
    if not category or category == "\u2014":
        return "#6b7280"
    parent = category.split(":", 1)[0]
    if parent in CATEGORY_COLORS:
        return CATEGORY_COLORS[parent]
    return FALLBACK_PALETTE[hash(parent) % len(FALLBACK_PALETTE)]
