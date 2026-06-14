# Bug: template output is wrong for HTML content and for loop variables

Two rendering problems show up:

1. Values emitted via `{{ ... }}` are not HTML-escaped. Rendering `{{ v }}` with
   `v = '<b>&"x"'` yields the raw text instead of `&lt;b&gt;&amp;&quot;x&quot;`.
2. A `{% for x in ... %}` loop leaks its loop variable into the surrounding
   scope. Rendering `{% for x in xs %}{{ x }}{% endfor %}{{ x }}` with
   `xs = ["1", "2"]` and an outer `x = "OUT"` gives `122` instead of `12OUT` —
   after the loop, `x` should be back to its outer value.

Plain text, simple substitution and basic loops are fine.
