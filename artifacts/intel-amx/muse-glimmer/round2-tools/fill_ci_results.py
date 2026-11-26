#!/usr/bin/env python3
"""Fill the CI results into the description draft and into the reply template of tron PR 5022.

Usage: fill_ci_results.py VALUES.json DRAFT.md REPLY_TEMPLATE.md OUT_BODY.md OUT_REPLY.md
VALUES.json holds the seven names in capitals: RUN_ID_NIX, RUN_ID_CMAKE, N_PASS, N_TOTAL, RUNNER_NAME,
CPU_MODEL and ATTEMPT_N. ATTEMPT_N "1" drops the attempt number from the description row.
The script writes nothing to GitHub. It stops when a name in capitals is left or when the description has
2,000 words or more.
"""
import json
import re
import sys

vals_path, draft_path, tmpl_path, out_body, out_reply = sys.argv[1:6]
vals = json.load(open(vals_path, encoding='utf-8'))
NAMES = ['RUN_ID_NIX', 'RUN_ID_CMAKE', 'N_PASS', 'N_TOTAL', 'RUNNER_NAME', 'CPU_MODEL', 'ATTEMPT_N']
assert sorted(vals) == sorted(NAMES), sorted(vals)
for k in ('RUN_ID_NIX', 'RUN_ID_CMAKE', 'N_PASS', 'N_TOTAL', 'ATTEMPT_N'):
    assert re.fullmatch(r'\d+', vals[k]), (k, vals[k])


def fill(text, names):
    for k in names:
        text = text.replace(k, vals[k])
    return text


body = open(draft_path, encoding='utf-8').read()
if vals['ATTEMPT_N'] == '1':
    old = '(Xeon CPU_MODEL, attempt ATTEMPT_N)'
    assert body.count(old) == 1
    body = body.replace(old, '(Xeon CPU_MODEL)')
counts = {k: body.count(k) for k in NAMES}
body = fill(body, NAMES)
reply = open(tmpl_path, encoding='utf-8').read()
reply_counts = {k: reply.count(k) for k in NAMES}
reply = fill(reply, NAMES)

for name, text in (('description', body), ('reply', reply)):
    left = sorted(set(re.findall(r'\b[A-Z]+(?:_[A-Z]+)+\b', text)) - {'TRON_AMX_DISPATCH', 'TRON_AMX_DISABLE',
                                                                     'TRON_AMX_K_MIRROR', 'TRON_AMX_PV_TRUNC'})
    left = [w for w in left if w in NAMES or w.startswith(('RUN_', 'N_', 'RUNNER', 'CPU_', 'ATTEMPT'))]
    assert not left, (name, left)
n_words = len(body.split())
assert n_words < 2000, n_words
open(out_body, 'w', encoding='utf-8').write(body)
open(out_reply, 'w', encoding='utf-8').write(reply)
print('names replaced in the description:', counts)
print('names replaced in the reply:', reply_counts)
print(f'description: {n_words} words -> {out_body}')
print(f'reply: {len(reply.split())} words -> {out_reply}')
