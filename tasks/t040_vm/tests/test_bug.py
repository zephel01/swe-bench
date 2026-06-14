from opcodes import HALT, JZ, PUSH, SUB
from vm import run


def test_subtraction_operand_order():
    # 先に積んだ 10 が被減数: 10 - 3 = 7
    assert run([(PUSH, 10), (PUSH, 3), (SUB,), (HALT,)]) == 7


def test_jz_jumps_only_when_zero():
    # スタック先頭が 0 のときだけ分岐する
    taken = [(PUSH, 0), (JZ, 4), (PUSH, 99), (HALT,), (PUSH, 7), (HALT,)]
    assert run(taken) == 7
    not_taken = [(PUSH, 1), (JZ, 4), (PUSH, 42), (HALT,), (PUSH, 7), (HALT,)]
    assert run(not_taken) == 42
