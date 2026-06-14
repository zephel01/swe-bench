# Bug: SUB subtracts backwards and JZ branches on the wrong condition

Two opcodes misbehave:

- `PUSH 10; PUSH 3; SUB` yields `-7` instead of `7`. The value pushed first
  should be the minuend (`10 - 3`).
- `JZ target` jumps when the popped value is non-zero. It should jump only when
  the value is exactly zero, and fall through otherwise.

ADD, MUL, DUP, JMP and HALT are correct.
