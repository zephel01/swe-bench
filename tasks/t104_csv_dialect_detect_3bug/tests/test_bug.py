"""Bug reproducers. Each targets exactly one of the three symptoms."""
from __future__ import annotations

from delim_detect import detect_delimiter
from newline_detect import detect_newline
from quote_detect import detect_quotechar

# --- Symptom A ---

def test_quote_brackets_default_to_double() -> None:
    sample = '[a,b,c]\n[1,2,3]\n[4,5,6]'
    assert detect_quotechar(sample) == '"'


def test_quote_hash_headers_default_to_double() -> None:
    sample = '#col1,col2\n#col3,col4\n1,2,3\n4,5,6'
    assert detect_quotechar(sample) == '"'


def test_quote_colon_lines_default_to_double() -> None:
    sample = 'key: value\nother: thing\nmore: stuff\nlast: one'
    assert detect_quotechar(sample) == '"'


def test_quote_result_is_always_a_real_quote() -> None:
    sample = '(a,b,c)\n(1,2,3)\n{d,e,f}\n<x,y,z>'
    assert detect_quotechar(sample) in ('"', "'")


# --- Symptom B ---

def test_delim_semicolon_with_commas_in_quotes() -> None:
    sample = (
        '"a,b,c";"d,e,f"\n'
        '"1,2,3";"4,5,6"\n'
        '"7,8,9";"0,1,2"'
    )
    assert detect_delimiter(sample, '"') == ';'


def test_delim_tab_with_commas_in_quotes() -> None:
    sample = (
        '"list,of,things"\tvalue\n'
        '"more,commas,here"\tanother\n'
        '"final,one"\tlast'
    )
    assert detect_delimiter(sample, '"') == '\t'


def test_delim_semicolon_with_pipes_in_quotes() -> None:
    sample = (
        '"a|b|c";"x|y|z"\n'
        '"1|2|3";"4|5|6"\n'
        '"7|8|9";"m|n|o"'
    )
    assert detect_delimiter(sample, '"') == ';'


def test_delim_comma_with_semicolons_in_quotes() -> None:
    sample = (
        '"a;b;c","x;y;z"\n'
        '"1;2;3","4;5;6"\n'
        '"7;8;9","m;n;o"'
    )
    assert detect_delimiter(sample, '"') == ','


# --- Symptom C ---

def test_newline_crlf_short() -> None:
    sample = 'a,b\r\n1,2\r\n3,4'
    assert detect_newline(sample) == '\r\n'


def test_newline_crlf_long() -> None:
    rows = [f'col{i},val{i}' for i in range(10)]
    sample = '\r\n'.join(rows)
    assert detect_newline(sample) == '\r\n'


def test_newline_crlf_with_trailing_terminator() -> None:
    sample = 'header1,header2\r\nrow1a,row1b\r\nrow2a,row2b\r\n'
    assert detect_newline(sample) == '\r\n'


def test_newline_crlf_from_tmp_file(tmp_path) -> None:
    p = tmp_path / 'sample.csv'
    p.write_bytes(b'a,b\r\n1,2\r\n3,4\r\n')
    # Read raw bytes to preserve CRLF (open(newline='') keeps line endings)
    sample = p.read_bytes().decode('utf-8')
    assert detect_newline(sample) == '\r\n'
