"""Fibonacci numbers with memoization."""


def fibonacci(n, _memo=None):
    """Return the n-th Fibonacci number (fib(0)=0, fib(1)=1)."""
    if _memo is None:
        _memo = {}
    if n in _memo:
        return _memo[n]
    if n <= 2:
        return n
    result = fibonacci(n - 1, _memo) + fibonacci(n - 2, _memo)
    _memo[n] = result
    return result
