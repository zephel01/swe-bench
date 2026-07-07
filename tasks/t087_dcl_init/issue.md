# Bug: lazily-initialized resource is sometimes built more than once

`Lazy` builds an expensive object on first use and is supposed to cache it so the
factory runs exactly once, no matter how many callers ask for it. In a single
thread it works. Under concurrent first-use, however, the factory occasionally
runs twice and different callers can receive different objects, which breaks code
that assumes the resource is a unique singleton (e.g. a shared connection).

The factory must run exactly once even if many threads call `get()` for the very
first time simultaneously, and every caller must observe the same object.
