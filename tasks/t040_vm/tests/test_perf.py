from opcodes import ADD, HALT, PUSH
from vm import run


def test_throughput():
    n = 100_000
    prog = [(PUSH, 1)] * n + [(ADD,)] * (n - 1) + [(HALT,)]
    assert run(prog) == n
