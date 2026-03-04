"""Formatting helpers for TUI display."""

MASK = "$•••••"


def format_dollar(amount, masked=False, signed=False):
    """Format a dollar amount, optionally masked for privacy."""
    if masked:
        if signed:
            prefix = "+" if amount >= 0 else "-"
            return f"{prefix}{MASK[1:]}"
        return MASK
    if signed:
        return f"${amount:+,.2f}"
    return f"${amount:,.2f}"
