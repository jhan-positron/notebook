#!/usr/bin/env python3
"""pr5606-check-20261123: compare the instructions of two builds of gen/t_amx_dispatch_dtype.

Input: two disassembly listings made with `objdump -d --no-show-raw-insn`.
The linker fills addresses in, and the two build trees have path names of different length, so data moves.
The compare therefore masks every address: the address column of each line, and every hexadecimal number of
four or more digits in the operands. Function names (the "<name>:" lines) are kept as they are.
It prints the count of lines, of functions, and of lines that differ after masking.
Usage: bincmp.py <listing A> <listing B>
"""
import hashlib
import re
import sys

HEXNUM = re.compile(r"\b(?:0x)?[0-9a-f]{4,}\b")
ADDR = re.compile(r"^\s*[0-9a-f]+:\s*")
FUNC = re.compile(r"^[0-9a-f]+ <(.*)>:$")
SYMOFF = re.compile(r"<([^>]*?)\+0x[0-9a-f]+>")


def norm(path):
    out = []
    funcs = 0
    for line in open(path, errors="replace"):
        line = line.rstrip("\n")
        if not line or line.startswith(("Disassembly of section", "/")) or "file format" in line:
            continue
        m = FUNC.match(line)
        if m:
            funcs += 1
            out.append("<" + m.group(1) + ">:")
            continue
        line = ADDR.sub("", line)
        out.append(HEXNUM.sub("X", line))
    return out, funcs


a, fa = norm(sys.argv[1])
b, fb = norm(sys.argv[2])
print(f"A: {len(a)} lines, {fa} functions, sha256 of the masked listing {hashlib.sha256(chr(10).join(a).encode()).hexdigest()[:16]}")
print(f"B: {len(b)} lines, {fb} functions, sha256 of the masked listing {hashlib.sha256(chr(10).join(b).encode()).hexdigest()[:16]}")
if len(a) != len(b):
    print("the listings have different lengths; a line-by-line compare is not valid")
    sys.exit(0)
diff = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
print(f"lines that differ after masking: {len(diff)} of {len(a)}")
for i, x, y in diff[:10]:
    print(f"  line {i}: A [{x[:150]}]")
    print(f"  line {i}: B [{y[:150]}]")
