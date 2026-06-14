"""スタックマシン。program は (op, *args) のタプル列."""

from __future__ import annotations

from opcodes import ADD, DUP, HALT, JMP, JZ, MUL, PUSH, SUB


def run(program: list[tuple]):
    stack: list = []
    ip = 0
    while ip < len(program):
        op = program[ip]
        name = op[0]
        if name == PUSH:
            stack.append(op[1])
            ip += 1
        elif name == ADD:
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            ip += 1
        elif name == SUB:
            a = stack.pop()
            b = stack.pop()
            stack.append(a - b)   # (誤り) オペランド順が逆
            ip += 1
        elif name == MUL:
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            ip += 1
        elif name == DUP:
            stack.append(stack[-1])
            ip += 1
        elif name == JMP:
            ip = op[1]
        elif name == JZ:
            ip = op[1] if stack.pop() != 0 else ip + 1
        elif name == HALT:
            break
        else:
            raise ValueError(f"bad opcode: {name}")
    return stack[-1] if stack else None
