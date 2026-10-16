Yes: the finding is about the `(void)dest;` line itself, not a comment. Rule 6 of the comment skill has two halves: no comment on a language idiom, and no warning-silencing idiom unless a compile with the project's warning flags shows the warning. The title says "cut" because the proposal is to delete the `(void)dest;` line.

Measured now on the real translation unit, src/tron/scheduler/full.cpp, compiled syntax-only with the project's flags (`-Wall -Wextra -Wpedantic -Wconsumed`, clang 19.1.7) and with the line removed: 0 warnings in both the TRON_AMX_DISPATCH on and off trees, the same count as with the line. `dest` is used in the other `if constexpr` branch (`k_destination_row(dest)` and `return dest`), and a name used in a discarded branch counts as used.

Not applied in the comment commit: this thread is a question, not an acceptance. Say the word and I cut the line.
