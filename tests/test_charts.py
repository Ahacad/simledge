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
