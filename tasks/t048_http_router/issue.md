# Bug: path params are not typed and wildcards shadow specific routes

Two problems in the router:

- `/users/{id:int}` matching `/users/42` yields the string `"42"` instead of
  the integer `42`; declared param types are ignored.
- A wildcard route like `/files/{path:*}` registered before `/files/readme`
  wins, even though the literal route is more specific.

Specific routes must beat wildcards (wildcards are tried last), a wildcard may
only appear as the final segment, and params must be converted to their
declared type. Static routes already match.
