from linkrender import render_search_link


def test_plain_query():
    assert render_search_link("hello", "Home") == (
        '<a href="/search?q=hello">Home</a>'
    )


def test_safe_chars_not_rewritten():
    assert render_search_link("abc123", "x") == (
        '<a href="/search?q=abc123">x</a>'
    )
