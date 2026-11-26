#!/usr/bin/env python3
"""Checks for the claims review (key: claims). usage: check1.py <results dir> <scratch dir>"""
import csv, sys, json, re
R, S = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(R + '/full/homes.csv')))
mesh = [int(r['mesh']) for r in rows]; node = [int(r['node_id_hex'], 16) for r in rows]
ch = list(csv.DictReader(open(R + '/full/chunks.csv')))
par = lambda a: sum((a >> b) & 1 for b in range(6, 37, 2)) & 1
# 1. VA rule per chunk
print('1. VA rule, wrong lines per 2 MiB chunk (of 32768):')
wr = []
for c in range(16):
    va = int(ch[c]['virt_hex'], 16)
    wr.append(sum(par(va + o * 64) != mesh[c * 32768 + o] for o in range(32768)))
print('  ', wr, 'chunks all wrong', sum(w == 32768 for w in wr), 'all right', sum(w == 0 for w in wr), 'mixed', sum(0 < w < 32768 for w in wr))
# same-chunk relative prediction from VA: mesh(line) xor mesh(first line of chunk) == par(va offset bits 6..20)
bad = 0
for c in range(16):
    for o in range(32768):
        bad += (mesh[c * 32768 + o] ^ mesh[c * 32768]) != par(o * 64)
print('   lines where [mesh XOR mesh of the first line of the same chunk] != XOR of even VA offset bits 6..20:', bad, 'of', len(mesh))
# same home node relation inside a chunk predicted from offsets? count distinct (offset -> home xor pattern) : does "same home as line 0 of chunk" depend only on the offset?
sets = []
for c in range(16):
    base = (mesh[c*32768], node[c*32768])
    sets.append(frozenset(o for o in range(32768) if (mesh[c*32768+o], node[c*32768+o]) == base))
print('   set of offsets that share the home of the first line of their chunk: identical in all 16 chunks:', len(set(sets)) == 1, 'size', len(sets[0]))
# 2. balance of small windows
pre = [0]
for m in mesh: pre.append(pre[-1] + m)
print('2. largest |lines on mesh 1 - lines on mesh 0| over every window of n consecutive lines inside one chunk:')
for n in (2, 3, 4, 8, 16, 64, 1024, 4096, 32768):
    worst = 0
    for c in range(16):
        b = c * 32768
        for s in range(0, 32768 - n + 1):
            d = abs(2 * (pre[b + s + n] - pre[b + s]) - n)
            if d > worst: worst = d
    print('   n =', n, 'lines (', n * 64, 'B ): worst imbalance', worst, 'lines')
al = sum(mesh[i] == mesh[i + 1] for i in range(0, len(mesh), 2))
print('   aligned pairs (lines 2k, 2k+1) on the same mesh:', al, 'of', len(mesh) // 2)
# 4. PA distance A to C
A, C = 0x21dd7e00000, 0x211c3c00000
print('4. PA(A) - PA(C) =', A - C, 'B =', (A - C) / 2**30, 'GiB')
# 3. pairing vs same low hash
T = json.load(open(S + '/hash/table.json'))
print('3. table.json keys:', list(T)[:6] if isinstance(T, dict) else type(T))
