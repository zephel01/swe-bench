from blocks import render


def test_consecutive_items_form_one_list():
    assert render("- a\n- b\n- c") == "<ul><li>a</li><li>b</li><li>c</li></ul>"
