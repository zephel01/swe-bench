"""Baseline tests — pass on both the buggy and the gold implementation."""
from __future__ import annotations

from delim_detect import detect_delimiter
from newline_detect import detect_newline
from quote_detect import detect_quotechar


def test_quote_double_quotes_clean() -> None:
    sample = '"name","age"\n"alice","30"\n"bob","25"'
    assert detect_quotechar(sample) == '"'


def test_quote_single_quotes_clean() -> None:
    sample = "'name','age'\n'alice','30'\n'bob','25'"
    assert detect_quotechar(sample) == "'"


def test_delim_comma_clean() -> None:
    sample = '"a","b","c"\n"1","2","3"'
    assert detect_delimiter(sample, '"') == ','


def test_delim_semicolon_clean() -> None:
    sample = '"a";"b";"c"\n"1";"2";"3"'
    assert detect_delimiter(sample, '"') == ';'


def test_delim_tab_clean() -> None:
    sample = 'a\tb\tc\n1\t2\t3'
    assert detect_delimiter(sample, '"') == '\t'


def test_newline_lf_clean() -> None:
    sample = 'a,b,c\n1,2,3\n4,5,6'
    assert detect_newline(sample) == '\n'


def test_newline_cr_only_clean() -> None:
    sample = 'a,b,c\r1,2,3\r4,5,6'
    assert detect_newline(sample) == '\r'
