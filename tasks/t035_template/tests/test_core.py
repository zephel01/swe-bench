from renderer import render


def test_plain_text():
    assert render("hello world", {}) == "hello world"


def test_variable_safe_content():
    assert render("hi {{ name }}!", {"name": "Bob"}) == "hi Bob!"


def test_for_loop():
    out = render("{% for x in xs %}[{{ x }}]{% endfor %}", {"xs": ["a", "b"]})
    assert out == "[a][b]"
