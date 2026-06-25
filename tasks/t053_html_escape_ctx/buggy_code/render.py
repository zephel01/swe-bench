def escape_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_attr(name, value):
    return f'{name}="{escape_text(value)}"'


def render_link(text, href):
    return f'<a href="{escape_text(href)}">{escape_text(text)}</a>'
