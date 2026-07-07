import html


def render_search_link(query, label):
    href = "/search?q=" + query
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a>'
