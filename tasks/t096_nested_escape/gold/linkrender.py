import html
import urllib.parse


def render_search_link(query, label):
    # Inner context first: percent-encode the value for the URL query
    # component so characters like "&", "#", "=" and spaces stay part of the
    # single q value. Outer context second: HTML-attribute-escape the finished
    # href. Doing only one of the two leaves the value able to break out of its
    # context.
    encoded = urllib.parse.quote(query, safe="")
    href = "/search?q=" + encoded
    return (
        f'<a href="{html.escape(href, quote=True)}">'
        f"{html.escape(label, quote=True)}</a>"
    )
