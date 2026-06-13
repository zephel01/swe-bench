# Bug: binary_search() returns an index for values that are absent

`binary_search([1, 3, 5], 2)` should return -1, but returns 1.
Present elements are found correctly. It looks like the "not found"
case returns an insertion position instead of -1.
