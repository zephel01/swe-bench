from render import render_attr, render_link


def test_attribute_quote_escaped():
    assert render_attr("title", 'a"b') == 'title="a&quot;b"'


def test_attribute_injection_neutralized():
    out = render_attr("src", '" onerror="alert(1)')
    assert "&quot;" in out
    assert ' onerror="alert(1)"' not in out


def test_javascript_url_neutralized():
    out = render_link("x", "javascript:alert(1)")
    assert "javascript:alert(1)" not in out
    assert out == '<a href="#">x</a>'


def test_data_url_neutralized():
    out = render_link("x", "  JavaScript:alert(1)")
    assert out == '<a href="#">x</a>'
