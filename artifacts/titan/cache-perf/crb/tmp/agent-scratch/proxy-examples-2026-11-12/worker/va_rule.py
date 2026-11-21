#!/usr/bin/env python3
"""Apply the mesh rule (XOR of the even address bits 6 to 36) to the physical and to the
virtual address of every line of the root-run buffer, and count the lines where the rule
gives a mesh other than the measured one.
usage: va_rule.py <results dir with full/homes.csv and full/chunks.csv>"""
import csv, sys
R = sys.argv[1]
homes = [int(r['mesh']) for r in csv.DictReader(open(R + '/full/homes.csv'))]
ch = list(csv.DictReader(open(R + '/full/chunks.csv')))
par = lambda a: sum((a >> b) & 1 for b in range(6, 37, 2)) & 1
bad_pa = bad_va = 0
for i, m in enumerate(homes):
    c, off = divmod(i, 32768)
    off *= 64
    bad_pa += par(int(ch[c]['pfn_hex'], 16) * 4096 + off) != m
    bad_va += par(int(ch[c]['virt_hex'], 16) + off) != m
print('lines', len(homes))
print('rule on the physical address: wrong mesh for', bad_pa, 'lines')
print('rule on the virtual address: wrong mesh for', bad_va, 'lines; with the result inverted:', len(homes) - bad_va)
