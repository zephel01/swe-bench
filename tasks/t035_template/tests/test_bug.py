from renderer import render


def test_variable_output_is_html_escaped():
    out = render("{{ v }}", {"v": '<b>&"x"'})
    assert out == "&lt;b&gt;&amp;&quot;x&quot;"


def test_loop_variable_does_not_leak_outer_scope():
    # ループ変数 x はループ内に閉じ、ループ後は外側の値に戻るべき
    out = render("{% for x in xs %}{{ x }}{% endfor %}{{ x }}",
                 {"xs": ["1", "2"], "x": "OUT"})
    assert out == "12OUT"
