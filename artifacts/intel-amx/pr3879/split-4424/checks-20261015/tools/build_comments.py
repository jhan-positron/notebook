#!/usr/bin/env python3
"""Turn the workflow result (result.json) into per-PR per-checker comment lists.

Writes <out>/<pr>-<A|B>.json: [{path, line, start_line, body, rule, action, votes}], and <out>/dropped.json, <out>/summary.md.
"""
import json, sys, os, collections
res_path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
res = json.load(open(res_path))
RULE_B = {'1': 'Rule 1, the name carries it', '2': 'Rule 2, restates identifiers', '3': 'Rule 3, the one-line contract',
          '4': 'Rule 4, comment lines that map to no code line', '5': 'Rule 5, a call-site comment says only why here',
          '6': 'Rule 6, no comment on a language idiom'}
RULE_A = {'bare-literal-argument': 'bare true/false passed as an argument',
          'bare-literal-aggregate': 'bare true/false in positional aggregate initialization',
          'bare-literal-template-argument': 'bare true/false as a template argument',
          'named-constant-not-argument': 'named constant used outside an argument position'}
kept = collections.defaultdict(list); dropped = []
stats = collections.Counter()
for u in res['units']:
    pr = u['pr']
    for j in u['judged']:
        f, votes = j['f'], j['votes']
        n = len(votes); notref = [x for x in votes if x['v'] and not x['v']['refuted']]
        ok = (n >= 2 and len(notref) >= 2) if f['checker'] == 'B' else (n >= 1 and len(notref) == n)
        stats[(pr, f['checker'], 'judged')] += 1
        if not ok:
            dropped.append({'pr': pr, 'path': f['path'], 'line': f['line'], 'checker': f['checker'], 'rule': f['rule'], 'code': f['code'][:80],
                            'votes': [{'lens': x['lens'], 'refuted': x['v']['refuted'], 'reason': x['v']['reason']} for x in votes if x['v']]})
            continue
        stats[(pr, f['checker'], 'kept')] += 1
        # corrections from non-refuting votes
        line, start = f['line'], f.get('start_line', f['line'])
        proposed, rule = f['proposed'], f['rule']
        pref_line = 'diff-scope' if f['checker'] == 'B' else 'code-context'
        for x in sorted(notref, key=lambda x: 0 if x['lens'] == pref_line else 1):
            v = x['v']
            if v.get('corrected_line'): line = v['corrected_line']; 
            if v.get('corrected_start_line'): start = v['corrected_start_line']
            break
        for x in notref:
            if x['lens'] == 'code-context' and x['v'].get('corrected_proposed', '').strip():
                proposed = x['v']['corrected_proposed']; break
        for x in notref:
            if x['lens'] == 'rule-text' and x['v'].get('better_rule', '').strip():
                rule = x['v']['better_rule'].strip(); break
        if f['checker'] == 'B':
            rname = RULE_B.get(rule, f'Rule {rule}')
            title = f"**[comments] {rname}: {f['action']}**"
            body = [title, '', f['reason'].strip()]
            if f['action'] == 'cut' and not proposed.strip():
                body += ['', 'Proposed: cut the comment.']
            else:
                body += ['', 'Proposed:', '```cpp', proposed.rstrip(), '```']
            if f.get('mapping', '').strip() and len(f['mapping']) < 600:
                body += ['', 'Line-to-code mapping (Rule 4):', f['mapping'].strip()]
        else:
            rname = RULE_A.get(rule, rule)
            title = f"**[named bool] {rname}**"
            body = [title, '', f['reason'].strip(), '', 'Proposed:', '```cpp', proposed.rstrip(), '```']
        kept[(pr, f['checker'])].append({'path': f['path'], 'line': line, 'start_line': start, 'rule': rule, 'action': f['action'],
                                          'code': f['code'], 'body': '\n'.join(body), 'hits': f.get('hits', 1),
                                          'votes': [{'lens': x['lens'], 'refuted': x['v']['refuted'], 'conf': x['v']['confidence']} for x in votes if x['v']]})
for (pr, ch), lst in kept.items():
    lst.sort(key=lambda c: (c['path'], c['line']))
    json.dump(lst, open(f'{out}/{pr}-{ch}.json', 'w'), indent=1)
json.dump(dropped, open(f'{out}/dropped.json', 'w'), indent=1)
with open(f'{out}/summary.md', 'w') as o:
    o.write('| PR | checker | judged | kept | dropped |\n|---|---|---|---|---|\n')
    for pr in ['4824', '4868', '4887']:
        for ch in ['A', 'B']:
            j, k = stats[(pr, ch, 'judged')], stats[(pr, ch, 'kept')]
            o.write(f'| {pr} | {ch} | {j} | {k} | {j-k} |\n')
    o.write('\nfinders: ' + ', '.join(f"{u['pr']}:{u['path'].split('/')[-1]} {u['finders_ok']}/{u['finders_expected']}" for u in res['units'] if u['finders_ok'] != u['finders_expected']) + '\n')
    o.write(f"\ndropped units: {res.get('dropped')}\n")
    rc = collections.Counter((pr, ch, c['rule']) for (pr, ch), lst in kept.items() for c in lst)
    o.write('\n| PR | checker | rule | kept |\n|---|---|---|---|\n')
    for (pr, ch, r), n in sorted(rc.items()): o.write(f'| {pr} | {ch} | {r} | {n} |\n')
print(open(f'{out}/summary.md').read())
