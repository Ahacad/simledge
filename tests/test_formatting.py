def test_format_dollar_normal():
    from simledge.tui.formatting import format_dollar
    assert format_dollar(1234.56) == "$1,234.56"
    assert format_dollar(-50.00) == "$-50.00"
    assert format_dollar(0) == "$0.00"


def test_format_dollar_masked():
    from simledge.tui.formatting import format_dollar
    result = format_dollar(1234.56, masked=True)
    assert "$" in result
    assert "1234" not in result
    assert "•" in result


def test_format_dollar_signed():
    from simledge.tui.formatting import format_dollar
    assert "+" in format_dollar(100, signed=True)
    assert format_dollar(-100, signed=True).startswith("$-")


def test_format_dollar_signed_masked():
    from simledge.tui.formatting import format_dollar
    result = format_dollar(100, signed=True, masked=True)
    assert "•" in result
    assert "100" not in result
