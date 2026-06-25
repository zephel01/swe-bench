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


def render_attr(name, value):
    return f'{name}="{escape_attr(value)}"'


def render_tag(tag, attrs, text):
    rendered = "".join(f" {render_attr(k, v)}" for k, v in attrs.items())
    return f"<{tag}{rendered}>{escape_text(text)}</{tag}>"
