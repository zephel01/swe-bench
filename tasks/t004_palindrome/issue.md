# Bug: is_palindrome() fails on mixed case and punctuation

The docstring says case, spaces and punctuation are ignored, but
`is_palindrome("A man, a plan, a canal: Panama")` returns False.
Plain lowercase palindromes work.
