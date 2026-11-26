#!/usr/bin/env python3
# Round 3, lens claims: every use of control I, F72d12, asmread and T72I* on the page, with the label check.
import re
D='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/claims/'
lines=open(D+'r3_page_text.txt',encoding='utf-8').read().split('\n')
tt=[l for l in open(D+'r3_svg_titles.txt',encoding='utf-8').read().split('\n') if l.startswith(('TT:','T:','ARIA:'))]
def sentences(l): return re.split(r'(?<=[.:;])\s+(?=[A-Z"\[])', l)
def check(name, pat, lab, src):
    miss=0; tot=0
    for i,l in enumerate(src):
        if re.search(pat,l):
            tot+=1
            if not re.search(lab,l):
                miss+=1; print(f'[{name}] UNLABELLED block {i+1}: {l[:300]}')
    print(f'[{name}] blocks with term: {tot}, without label in the same block: {miss}')
check('controlI page', r'[Cc]ontrol I\b|T72I', r'added after the first numbers were seen|added after the first|Control I\s*$', lines)
check('F72 page', r'F72d12', r'not part of the rerun|earlier run of the same boot', lines)
check('controlI svg', r'[Cc]ontrol I\b|T72I', r'added after the first numbers were seen|added after the first', tt)
check('F72 svg', r'F72d12', r'not part of the rerun', tt)
# sentence-level: sentences naming control I without the label in the same sentence
for name,pat,lab in (('controlI',r'[Cc]ontrol I\b',r'added after the first numbers were seen'),('F72',r'F72d12',r'not part of the rerun|earlier run of the same boot')):
    for i,l in enumerate(lines):
        for s in sentences(l):
            if re.search(pat,s) and not re.search(lab,s): print(f'[{name} sentence] block {i+1}: {s[:260]}')
