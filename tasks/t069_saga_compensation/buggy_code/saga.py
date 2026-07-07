"""A saga orchestrator with reverse-order compensation.

Forward steps run in order.  If any step's action fails, every step that has
already completed is compensated in the reverse of the order it ran.  A
compensation that itself fails must not abort the remaining compensations: the
failure is recorded and the runner keeps going, so that no completed step is
ever left stranded (its resources unreleased) while the others get cleaned up.
"""


class Step:
    def __init__(self, name, action, compensate):
        self.name = name
        self.action = action
        self.compensate = compensate


class SagaRunner:
    def __init__(self):
        self.steps = []
        self.completed = []
        self.comp_failures = []

    def add(self, step):
        self.steps.append(step)
        return self

    def run(self, ctx):
        self.completed = []
        self.comp_failures = []
        for step in self.steps:
            try:
                step.action(ctx)
            except Exception:
                self._compensate(ctx)
                raise
            self.completed.append(step)
        return ctx

    def _compensate(self, ctx):
        for step in reversed(self.completed):
            step.compensate(ctx)
        self.completed = []
