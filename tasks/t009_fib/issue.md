# Bug: fibonacci() produces a shifted sequence

Expected: fib(0)=0, fib(1)=1, fib(2)=1, fib(3)=2, fib(10)=55.
Actual: fib(2)=2, fib(3)=3, fib(10)=89 — every value from fib(2)
onward is wrong. The memoized recursion's base case looks suspicious.
