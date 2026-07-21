# Email formatter is misbehaving in three separate ways

The plain-text/HTML email formatter that ships with our newsletter
tooling has started producing broken output in production. Three of
our QA scenarios fail; simple happy-path tests are still green, which
is why the regression slipped through the last release.

## Symptoms

1. **Escaped template markup.** When a template contains real HTML
   markup around a `{{ }}` placeholder, the surrounding tags come out
   as `&lt;p&gt;...&lt;/p&gt;` in the rendered body. Templates that
   contain no HTML tags render normally, so an in-line message like
   `Hi {{ name }}!` still works fine.

2. **Reply chains lose paragraph breaks.** A first-level `> ` quote
   works, but taking a body that already contains a `>`-quoted block
   and requoting it drops the paragraph break between the quoted
   paragraphs. The blank line between paragraphs is left blank in
   the second-level reply instead of being requoted with a bare `>`.

3. **CR artefacts in normalised bodies.** Bodies pasted in with mixed
   line endings (a lone `\r` between two lines, or an old-Mac style
   body using only `\r`) come out of `normalize_body` with the `\r`
   characters still embedded, even though bodies that only ever
   contained `\r\n` or `\n` normalise cleanly.

A single-line template rendered against plain text values with LF-only
line endings does not exhibit any of the three problems.
