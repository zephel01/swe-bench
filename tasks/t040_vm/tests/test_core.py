from opcodes import ADD, DUP, HALT, JMP, MUL, PUSH
from vm import run


def test_add_mul():
    assert run([(PUSH, 2), (PUSH, 3), (ADD,), (HALT,)]) == 5
    assert run([(PUSH, 4), (PUSH, 5), (MUL,), (HALT,)]) == 20


def test_dup():
    assert run([(PUSH, 7), (DUP,), (ADD,), (HALT,)]) == 14


def test_jmp():
    assert run([(PUSH, 5), (JMP, 3), (PUSH, 99), (HALT,)]) == 5
