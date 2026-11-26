#!/usr/bin/env python3
"""Range of the two decode options of section 5.7 (est.): fewer passes over the state per decode token.

Input: design-checks/verify-cost/verify_numbers.out, check C16. One decode token costs about 17,108 to 20,786 cycles
per value head for the scan and the two loops (from the lowest and the highest traced decode GDN step).
Option (a) does the state part of the check for invalid values inside the first loop: one pass over the state less.
Option (b) also stores the state in column halves: two passes less.
One pass moves the 1,024 cache lines of a 64 KiB matrix, at 1.8 to 2.96 cycles per line (design_numbers.py LINE_LO, LINE_HI).
"""
LINES = 1024
for line in (1.8, 2.96):
    one = LINES * line
    for today in (17108, 20786):
        print(f"{line} cycles per line, today {today} cycles: (a) {today / (today - one):.2f} times; (a)+(b) {today / (today - 2 * one):.2f} times")
