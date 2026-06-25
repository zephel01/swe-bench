from render import escape_text, render_tag


def test_text_escaped():
    assert escape_text("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_render_plain_tag():
    assert render_tag("p", {}, "hello") == "<p>hello</p>"
