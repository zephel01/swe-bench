# Bug: registered plugins cannot be called

Plugins are registered with the `@register("name")` decorator from
`registry.py`, then looked up with `registry.get(name)` and called.
But `registry.get("shout")("hi")` raises `TypeError: 'str' object is not
callable` — the registry is storing the wrong thing. The plugin functions
in `plugins.py` are correct; the bug is in the registry itself.

Files: `registry.py` (buggy), `plugins.py` (uses the decorator).
