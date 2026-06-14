# Bug: chained exponentiation gives the wrong result

`evaluate("2**3**2")` returns `64`, but the expected value is `512`. Chained
`**` is being grouped the wrong way. Single powers, precedence with `+ - * /`,
unary minus (`-2**2 == -4`), variables and parentheses are all correct.
