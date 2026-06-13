"""Tiny arithmetic expression evaluator (+ - * / and parentheses)."""


def _tokenize(expr):
    tokens = []
    s = expr.replace(" ", "")
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "+-*/":
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


def evaluate(expr):
    # BUG: folds left-to-right, ignoring precedence and parentheses
    tokens = _tokenize(expr)
    result = tokens[0]
    i = 1
    while i < len(tokens):
        op, val = tokens[i], tokens[i + 1]
        if op == "+":
            result += val
        elif op == "-":
            result -= val
        elif op == "*":
            result *= val
        elif op == "/":
            result /= val
        i += 2
    return result
