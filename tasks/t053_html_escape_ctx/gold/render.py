_DANGEROUS_SCHEMES = ("javascript:", "data:", "vbscript:")


def escape_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(s):
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def escape_url(value):
    collapsed = value.strip().lower().replace("\t", "").replace("\n", "")
    if collapsed.startswith(_DANGEROUS_SCHEMES):
        return "#"
    return escape_attr(value)


def render_attr(name, value):
    return f'{name}="{escape_attr(value)}"'


def render_link(text, href):
    return f'<a href="{escape_url(href)}">{escape_text(text)}</a>'
