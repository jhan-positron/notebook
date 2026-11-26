#!/usr/bin/env python3
"""gdn-impl-20261121: the two best scores of each generated step, per arm, from the lines that logit-margin.sh kept.

Words: logits = the scores of all vocabulary words for the next token; top-k = the k best of them, sorted;
bf16 = a 16-bit float format with 8 significant bits; one bf16 step at a value x = 2^(floor(log2|x|) - 7);
generated token g = the g-th token after the prompt, counted from 0. The log names a step by the position of the
token that the model scored, so generated token g of a prompt of P tokens is "token P - 1 + g".

Input : tokens/logits-p<prompt>-l<len>__<arm>.txt (lines "Top-k Logits of token N (K): v1 v2 ..." and
        "Top-k Token IDs for Logits of token N (K): id1 id2 ...")
Output: one line per arm and step on stdout:
        prompt P len L arm A generated G: best ID1 SCORE1, second ID2 SCORE2, margin M = S bf16 steps
Usage : python3 logit_summary.py <tokens folder> <prompt> <len> <arm> [<arm> ...]
"""
import math
import re
import sys


def bf16_step(x):
    return 2.0 ** (math.floor(math.log2(abs(x))) - 7) if x else 0.0


def read(path):
    rows = {}
    for line in open(path, errors="replace"):
        m = re.search(r"Top-k (Logits|Token IDs for Logits) of token (\d+) \(\d+\):(.*)", line)
        if m:
            rows.setdefault(int(m.group(2)), {})["v" if m.group(1) == "Logits" else "id"] = m.group(3).split()
    return rows


def main():
    folder, prompt, length, arms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    for arm in arms:
        try:
            rows = read(f"{folder}/logits-p{prompt}-l{length}__{arm}.txt")
        except FileNotFoundError:
            print(f"prompt {prompt} len {length} arm {arm}: no file")
            continue
        for tok in sorted(rows):
            r = rows[tok]
            if "v" not in r or "id" not in r or len(r["v"]) < 2:
                continue
            v1, v2 = float(r["v"][0]), float(r["v"][1])
            step = bf16_step(v1)
            print(f"prompt {prompt} len {length} arm {arm} generated {tok - (prompt - 1)}: best {r['id'][0]} {v1:g}, second {r['id'][1]} {v2:g}, "
                  f"margin {v1 - v2:g} = {(v1 - v2) / step:g} bf16 steps")


if __name__ == "__main__":
    main()
