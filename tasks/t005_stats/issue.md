# Bug: average() raises ZeroDivisionError on an empty list

`average([])` should return 0.0 as documented, but raises ZeroDivisionError.
