#!/usr/bin/env python3
"""Is the fitted proxy pairing the same as 'same value of the six low sums' in the table of hash2.py?
usage: check2.py <scratch dir>"""
import re, sys, ast
S = sys.argv[1]
h2 = open(S + '/hash/hash2.out').read()
m = re.search(r'same low hash: (\[.*\])\n', h2)
lowhash = dict(ast.literal_eval(m.group(1)))          # XP on mesh 0 -> XP on mesh 1 with the same low hash
out = open(S + '/refute-proxy/out.txt').read()
sec0 = out.split('reader mesh 0 remote map')[1].split('reader mesh 1 remote map')[0]
sec1 = out.split('reader mesh 1 remote map')[1].split('== B.')[0]
def parse(sec):
    d = {}
    for l in sec.splitlines():
        mm = re.match(r'\s+\((\d),(\d)\)->((?:\(\d,\d\)\|?)+)', l)
        if mm:
            d[(int(mm.group(1)), int(mm.group(2)))] = [tuple(map(int, x)) for x in re.findall(r'\((\d),(\d)\)', mm.group(3))]
    return d
r0, r1 = parse(sec0), parse(sec1)   # r0: home XP on mesh 1 -> proxy XP on mesh 0 ; r1: home XP on mesh 0 -> proxy XP(s) on mesh 1
print('entries', len(lowhash), len(r0), len(r1))
# r0: home on mesh 1 (value side of lowhash) -> proxy on mesh 0 (key side)
inv = {v: k for k, v in lowhash.items()}
print('reader mesh 0: fitted proxy == mesh-0 crosspoint with the same low hash as the home:', sum(r0[h] == [inv[h]] for h in r0), 'of', len(r0))
print('reader mesh 1: mesh-1 crosspoint with the same low hash is in the fitted tie set:', sum(lowhash[h] in r1[h] for h in r1), 'of', len(r1), '; unique fits equal:', sum(r1[h] == [lowhash[h]] for h in r1))
