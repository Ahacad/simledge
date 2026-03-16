"""Tests for category color mapping."""

from simledge.colors import CATEGORY_COLORS, FALLBACK_PALETTE, get_category_color


def test_known_categories_return_curated_colors():
    for cat, expected in CATEGORY_COLORS.items():
        assert get_category_color(cat) == expected


def test_subcategory_inherits_parent_color():
    assert get_category_color("Food:Dining") == CATEGORY_COLORS["Food"]
    assert get_category_color("Housing:Rent") == CATEGORY_COLORS["Housing"]
    assert get_category_color("Income:Salary") == CATEGORY_COLORS["Income"]


def test_unknown_category_returns_consistent_fallback():
    color = get_category_color("Widgets")
    assert color in FALLBACK_PALETTE
    # Same input always returns same color
    assert get_category_color("Widgets") == color


def test_different_unknown_categories_can_differ():
    # Not guaranteed to differ, but with enough variety they should
    colors = {get_category_color(f"Cat{i}") for i in range(20)}
    assert len(colors) > 1


def test_empty_and_dash_return_gray():
    assert get_category_color("") == "#6b7280"
    assert get_category_color("—") == "#6b7280"
    assert get_category_color(None) == "#6b7280"
