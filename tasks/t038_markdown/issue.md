# Bug: consecutive bullet lines render as separate lists

`render("- a\n- b\n- c")` produces three separate `<ul>` elements, one per line,
instead of a single `<ul>` containing three `<li>` items
(`<ul><li>a</li><li>b</li><li>c</li></ul>`).

Headings, paragraphs, inline formatting and a one-line list all render correctly.
