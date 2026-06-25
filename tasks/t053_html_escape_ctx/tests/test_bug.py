from render import render_attr, render_tag


def test_attribute_quote_escaped():
    out = render_attr("title", 'a"b')
    assert out == 'title="a&quot;b"'
    assert '"b"' not in out.replace('title="', "", 1)


def test_attribute_injection_neutralized():
    payload = '" onerror="alert(1)'
    out = render_tag("img", {"src": payload}, "")
    # the closing quote of the payload must be escaped, so no stray attribute
    assert "&quot;" in out
    assert ' onerror="alert(1)"' not in out


def test_single_quote_escaped():
    assert render_attr("data", "x'y") == "data=\"x&#x27;y\""
