from trie import Trie


def test_exact_vs_prefix():
    t = Trie()
    t.insert("apple")
    assert t.search("apple") is True
    assert t.search("app") is False
    assert t.starts_with("app") is True
    assert t.search("apples") is False
    assert t.starts_with("apx") is False


def test_add_prefix_word():
    t = Trie()
    t.insert("apple")
    t.insert("app")
    assert t.search("app") is True
    assert t.search("apple") is True


def test_empty_trie():
    t = Trie()
    assert t.search("x") is False
    assert t.starts_with("") is True
