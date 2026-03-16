# tests/test_charts.py
from rich.text import Text


def test_render_line_chart_basic():
    from simledge.tui.charts import render_line_chart

    result = render_line_chart([100, 200, 150, 300], ["Jan", "Feb", "Mar", "Apr"])
    assert isinstance(result, Text)
    assert len(result) > 0


def test_render_line_chart_empty():
    from simledge.tui.charts import render_line_chart

    result = render_line_chart([], [])
    assert isinstance(result, Text)


def test_render_line_chart_single():
    from simledge.tui.charts import render_line_chart

    result = render_line_chart([100], ["Jan"])
    assert isinstance(result, Text)


def test_render_bar_chart_basic():
    from simledge.tui.charts import render_bar_chart

    result = render_bar_chart([100, 200, 150], ["Jan", "Feb", "Mar"])
    assert isinstance(result, Text)
    assert len(result) > 0


def test_render_bar_chart_empty():
    from simledge.tui.charts import render_bar_chart

    result = render_bar_chart([], [])
    assert isinstance(result, Text)


def test_dollar_yticks():
    from simledge.tui.charts import render_line_chart

    result = render_line_chart([50000, 100000, 75000], ["Jan", "Feb", "Mar"])
    assert isinstance(result, Text)
    assert len(result) > 0


def test_render_data_table():
    from simledge.tui.charts import render_data_table

    result = render_data_table(["Jan", "Feb", "Mar"], [1000, 2000, 1500])
    assert "Jan" in result
    assert "Feb" in result
    assert len(result) > 0


def test_render_data_table_empty():
    from simledge.tui.charts import render_data_table

    assert render_data_table([], []) == ""


def test_render_bar_chart_with_labels():
    from simledge.tui.charts import render_bar_chart

    result = render_bar_chart([100, 200, 150], ["Jan", "Feb", "Mar"])
    assert isinstance(result, Text)
    assert len(result) > 0


def test_render_stacked_bar_basic():
    from simledge.tui.charts import render_stacked_bar

    segments = [
        ("Food", 500.0, "#fb923c"),
        ("Housing", 1200.0, "#60a5fa"),
        ("Transport", 300.0, "#a78bfa"),
    ]
    result = render_stacked_bar(segments, width=40)
    assert "\u2588" in result  # contains bar blocks
    assert "Food" in result
    assert "Housing" in result
    assert "Transport" in result
    assert "$500.00" in result
    assert "$1,200.00" in result
    assert "\u25cf" in result  # legend dots


def test_render_stacked_bar_empty():
    from simledge.tui.charts import render_stacked_bar

    result = render_stacked_bar([])
    assert "No data" in result


def test_render_stacked_bar_single():
    from simledge.tui.charts import render_stacked_bar

    result = render_stacked_bar([("Groceries", 400.0, "#f59e0b")], width=20)
    assert "Groceries" in result
    assert "$400.00" in result
    assert "100.0%" in result


def test_render_stacked_bar_collapse_small():
    from simledge.tui.charts import render_stacked_bar

    segments = [
        ("Housing", 1000.0, "#60a5fa"),
        ("Food", 500.0, "#fb923c"),
        ("Tiny", 5.0, "#aaaaaa"),  # <2% of total
        ("Micro", 3.0, "#bbbbbb"),  # <2% of total
    ]
    result = render_stacked_bar(segments, width=40)
    assert "Housing" in result
    assert "Food" in result
    assert "Other" in result
    # The collapsed categories should not appear by name
    assert "Tiny" not in result
    assert "Micro" not in result
