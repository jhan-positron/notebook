#!/usr/bin/env python3
"""Row F30 of the record and the brief texts of record section 10.6: the two findings of the
brief that repeat the older statements. The brief is generated, so the change is made in the
template of the generator.
Two things differ from the texts of section 10.6 (sweep of this step):
  - line 180 ends with "What limits a pair was not measured."
  - line 181 does not use "credit-stall cycles", "data flits" and powers of ten, because the
    brief has no word list. It gives the share of mesh cycles in which the links waited.
Usage: apply_brief_p.py <make-brief.py> [--write]"""
import sys
P = sys.argv[1]
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n = 0


def whole(k, old, new):
    global n
    assert L[k - 1] == old, (k, L[k - 1][:80])
    assert "\n" not in new and "{" not in new and "}" not in new   # the line is part of an f-string
    L[k - 1] = new; n += 1


whole(180, '<li class="take">Pair port: cores 2k and 2k+1 share one crosspoint port. Two partners together read 78 GB/s from the SLC; two non-partners 134 GB/s.</li>',
      '<li class="take">Pair port: cores 2k and 2k+1 share one crosspoint port. Two partner cores together read 78 GB/s with a buffer of 8 MiB each. '
      'That rate counts the lines from their own L2 too. Two cores of different pairs read 125 to 134 GB/s. What limits a pair was not measured.</li>')
whole(181, "<li>One writer's 73 GB/s limit is inside the core: no L1/L2 allocation (0 refills, 0 write-backs), no credit stalls on its crosspoint links, "
           "and the same port carries 82 GB/s with the partner core, 229 GB/s with 4 writers [sudo-20261102T211150Z/writepath.csv].</li>",
      "<li>What limits one writer at 8 MiB (70 to 73 GB/s) was not measured. Its lines are not allocated in L1 or L2 (0 refills, 0 write-backs). "
      "The mesh links out of its crosspoint waited for the receiver in about 0.001 % of the mesh cycles. "
      "With the partner core on the same port the pair writes 82 GB/s. Four writers on four ports write 229 GB/s. "
      "Hypothesis, not tested: the core keeps only a fixed number of writes unfinished at a time. "
      "At 1 GiB one writer alone (63.0 GB/s) already reaches the rate of the pair (63.2 GB/s) "
      "[sudo-20261102T211150Z/writepath.csv, followup-20261030T194205Z/asm.csv].</li>")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n} edits")
