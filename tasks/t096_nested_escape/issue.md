# Bug: search link mis-encodes the query across URL and HTML contexts

`render_search_link(query, label)` builds an anchor that points at
`/search?q=<query>` and shows `<label>`. The query value lives in two nested
contexts at once: it is part of a URL query component, which is itself inside
an HTML attribute. Both encodings must be applied so the value stays a single
opaque query parameter and cannot alter the link.

Reported problems:

- `render_search_link("a&b=c", "x")` produces an `href` where `a`, `b` and `c`
  end up looking like separate query parameters instead of one value.
- `render_search_link("a#frag", "x")` produces an `href` where everything after
  `#` is dropped from the query and becomes a fragment.

Ordinary inputs must keep working unchanged:

- `render_search_link("hello", "Home")` yields
  `<a href="/search?q=hello">Home</a>`.
- `render_search_link("abc123", "x")` keeps `q=abc123` (safe characters are not
  needlessly rewritten).
