# Bug: calculator ignores operator precedence and parentheses

`evaluate("1+2*3")` returns `9` instead of `7`: the evaluator folds tokens
strictly left-to-right. It must respect normal precedence (`*` and `/`
bind tighter than `+` and `-`), stay left-associative for equal precedence
(`10-2-3 == 5`), and support parentheses (`(1+2)*3 == 9`). Integers and the
`/` operator are allowed. Do not use `eval`.

File: `calc.py`.
