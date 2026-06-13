"""Tiny arithmetic expression evaluator (+ - * / and parentheses)."""


def _tokenize(expr):
    tokens = []
    s = expr.replace(" ", "")
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "+-*/()":
            tokens.append(ch)
            i += 1
        elif ch.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(int(s[i:j]))
            i = j
        else:
            raise ValueError(f"bad character: {ch!r}")
    return tokens


def _parse_expr(tokens, pos):
    value, pos = _parse_term(tokens, pos)
    while pos < len(tokens) and tokens[pos] in ("+", "-"):
        op = tokens[pos]
        rhs, pos = _parse_term(tokens, pos + 1)
        value = value + rhs if op == "+" else value - rhs
    return value, pos


def _parse_term(tokens, pos):
    value, pos = _parse_factor(tokens, pos)
    while pos < len(tokens) and tokens[pos] in ("*", "/"):
        op = tokens[pos]
        rhs, pos = _parse_factor(tokens, pos + 1)
        value = value * rhs if op == "*" else value / rhs
    return value, pos


def _parse_factor(tokens, pos):
    tok = tokens[pos]
    if tok == "(":
        value, pos = _parse_expr(tokens, pos + 1)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError("missing closing parenthesis")
        return value, pos + 1
    if isinstance(tok, int):
        return tok, pos + 1
    raise ValueError(f"unexpected token: {tok!r}")


def evaluate(expr):
    tokens = _tokenize(expr)
    value, pos = _parse_expr(tokens, 0)
    if pos != len(tokens):
        raise ValueError("unexpected trailing tokens")
    return value
