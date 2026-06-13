from word_freq import word_frequencies


def test_case_insensitive():
    assert word_frequencies("Dog dog DOG.") == {"dog": 3}


def test_punctuation():
    assert word_frequencies("hello, world! hello.") == {"hello": 2, "world": 1}


def test_empty():
    assert word_frequencies("") == {}


def test_only_punct():
    assert word_frequencies("... !!!") == {}
