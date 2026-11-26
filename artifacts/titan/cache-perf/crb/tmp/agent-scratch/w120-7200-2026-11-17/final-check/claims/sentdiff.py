#!/usr/bin/env python3
"""Sentence-level diff of two block files written by extract.py.

Usage: sentdiff.py old.blocks new.blocks
Prints: REMOVED sentences (in old only), ADDED sentences (in new only) with the block they stand in.
A sentence is matched as an exact string (multiset).
"""
import re
import sys
from collections import Counter


def sentences(block):
    m = re.match(r'^(<[^>]+>|\[[^\]]+\])\s(.*)$', block)
    tag, text = (m.group(1), m.group(2)) if m else ('', block)
    # split at ". " / "? " / "! " followed by a capital letter, a quote or a bracket; keep [RefN] with its sentence
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"(\[])', text)
    res = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # a "[Ref12]." or "[Ref1, Ref2]" fragment belongs to the previous sentence
        if res and re.fullmatch(r'(\[Ref[^\]]*\][.,;]?\s*)+', p):
            res[-1] += ' ' + p
        else:
            res.append(p)
    return tag, res


def load(path):
    blocks = [l.rstrip('\n') for l in open(path, encoding='utf-8') if l.strip()]
    sents = []
    for i, b in enumerate(blocks):
        tag, ss = sentences(b)
        for s in ss:
            sents.append((i, tag, s))
    return blocks, sents


def main(a, b):
    ba, sa = load(a)
    bb, sb = load(b)
    ca = Counter(s for _, _, s in sa)
    cb = Counter(s for _, _, s in sb)
    removed = ca - cb
    added = cb - ca
    print(f'# old: {len(ba)} blocks, {len(sa)} sentences; new: {len(bb)} blocks, {len(sb)} sentences')
    print(f'# removed sentences: {sum(removed.values())}; added sentences: {sum(added.values())}')
    print('\n==== REMOVED (old only) ====')
    left = Counter(removed)
    for i, tag, s in sa:
        if left[s] > 0:
            left[s] -= 1
            print(f'- [old block {i} {tag}] {s}')
    print('\n==== ADDED (new only) ====')
    left = Counter(added)
    last = None
    for i, tag, s in sb:
        if left[s] > 0:
            left[s] -= 1
            if i != last:
                print(f'\n  ## new block {i} {tag}')
                last = i
            print(f'+ {s}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
