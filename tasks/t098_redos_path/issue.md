# Bug: label-path validator hangs on some rejected inputs

`is_valid_label_path(s)` accepts a dot-separated path of word labels such as
`"users.profile.name"` and rejects malformed ones. Functionally it looks
correct on small inputs, but for certain **invalid** inputs the call takes
seconds to minutes instead of returning quickly, which lets a single request
pin a CPU.

Reproduction: validating a long run of word characters that ends in one
character which makes the whole string invalid, for example
`"aaaaaaaaaaaaaaaaaaaaaaaaaaaa!"`, does not return promptly. The validator must
answer in linear time regardless of input.

Correct answers must not change:

- `"users.profile.name"`, `"a"`, `"x_1.y_2"` are valid.
- `"a..b"`, `".a"`, `"a b"`, `""` are invalid.
- `"a."` (a trailing dot) is invalid.
