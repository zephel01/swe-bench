from linkrender import render_search_link


def test_ampersand_stays_in_value():
    out = render_search_link("a&b=c", "x")
    assert "q=a%26b%3Dc" in out
    assert "&amp;b" not in out


def test_hash_stays_in_value():
    out = render_search_link("a#frag", "x")
    assert "q=a%23frag" in out
    assert "#frag" not in out


def test_quote_and_space_encoded():
    out = render_search_link('a b"', "x")
    assert "q=a%20b%22" in out


def test_plain_value_not_over_encoded():
    assert render_search_link("hello", "Home") == (
        '<a href="/search?q=hello">Home</a>'
    )
