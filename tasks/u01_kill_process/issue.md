# Linux process management

A long-running daemon on a Linux server has stopped responding. It ignores `SIGTERM`,
it is still holding its TCP port open, and a rolling restart is blocked until it is gone.
You need the operating system to terminate the process immediately, without giving it a
chance to run cleanup handlers.

Name the POSIX signal that does this — the one a process cannot catch, block, or ignore —
and give the exact `kill` command that sends it to process ID 4821.

Output your final answer after a line containing exactly `--- ANSWER ---`.
For multiple choice, give just the letter. For short answer, give the term.
