# Bug: is_leap_year() is wrong for century years

`is_leap_year(1900)` returns True but 1900 was NOT a leap year.
`is_leap_year(2000)` correctly returns True. The Gregorian rules
(divisible by 4, except centuries unless divisible by 400) are not applied.
This also breaks `days_in_month(1900, 2)` which returns 29 instead of 28.
