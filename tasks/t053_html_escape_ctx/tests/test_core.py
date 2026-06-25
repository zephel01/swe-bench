from render import escape_text, render_link


def test_text_escaped():
    assert escape_text("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_safe_http_url():
    assert render_link("home", "https://example.com") == (
        '<a href="https://example.com">home</a>'
    )
