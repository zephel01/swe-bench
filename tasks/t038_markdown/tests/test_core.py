from blocks import render


def test_heading_and_paragraph():
    assert render("# Title\n\nhello") == "<h1>Title</h1><p>hello</p>"


def test_inline_bold_and_code():
    assert render("a **b** `c`") == "<p>a <strong>b</strong> <code>c</code></p>"


def test_escape():
    assert render("1 < 2 & 3") == "<p>1 &lt; 2 &amp; 3</p>"


def test_single_item_list():
    assert render("- one") == "<ul><li>one</li></ul>"
