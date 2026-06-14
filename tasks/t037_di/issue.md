# Bug: singletons aren't reused, and a failed resolve breaks later ones

Two defects in the container:

1. A component registered with `singleton=True` is rebuilt on every `resolve`;
   two resolves of the same singleton return different objects instead of one
   shared instance.
2. If a factory raises, the container is left in a bad state: a second `resolve`
   of that same name raises a spurious cycle error (`ValueError`) instead of
   re-running the factory and surfacing the real error again.

Transient resolution, dependency wiring and genuine cycle detection still work.
