# Bug: discounted total is tiny — customers pay almost nothing

With items worth 100.0 and code SAVE10 (10% off), `total_with_discount`
should return 90.0 but returns 10.0. It appears the method returns the
discount amount itself instead of the discounted total.
Files: `cart.py` uses rates from `discounts.py` (the rate table is correct).
