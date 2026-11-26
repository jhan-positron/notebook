#!/usr/bin/env python3
"""Measure the outputs of the skill-wording experiment (experiment/out/TASK_ARM_REP.json)."""
import collections, glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/proposed/scripts')
import check_lengths as C

OUT = sys.argv[1] if len(sys.argv) > 1 else ROOT + '/experiment/out'
FACTS_T2 = ['412', '409', '118', '119', '2140', '870', '9800', '3100', '61.2', '66.9', '31', '40', '5.7', '9.3',
            '4f1c2aa', 'logrotate', 'ycsb-a', 'NUMA', 'staging', 'capacity']
FACTS_T1 = ['16', '64-byte', '7', '160', '32', '9', '12', 'eight', 'section 8', 'bit-6', 'Insufficient data', 'L3']
runs = collections.defaultdict(list)
for p in sorted(glob.glob(OUT + '/*.json')):
    task, arm, rep = os.path.basename(p)[:-5].rsplit('_', 2)
    try:
        d = json.load(open(p))
    except Exception as e:
        print('unreadable', p, e)
        continue
    if d.get('is_error') or not d.get('result'):
        print('error run', p, str(d.get('result'))[:100])
        continue
    text = d['result']
    # The rewrite tasks (T1, T4) return the rewritten prose inside code fences. The checker skips
    # fenced text, so the fence lines are removed first. T2 and T3 keep their fences: they hold charts.
    measured = re.sub(r'(?m)^[ \t]*(```|~~~)[^\n]*\n?', '', text) if task[:2] in ('T1', 'T4') else text
    bl = C.analyse(measured, 'md')
    facts = FACTS_T2 if task.startswith('T2') else FACTS_T1 if task.startswith('T1') else []
    kept = sum(1 for f in facts if f.lower() in text.lower())
    runs[(task, arm)].append(dict(blocks=bl, text=text, cost=d.get('total_cost_usd') or 0,
                                  out_tokens=(d.get('usage') or {}).get('output_tokens') or 0,
                                  seconds=(d.get('duration_ms') or 0) / 1000,
                                  facts=(kept, len(facts)), rep=rep,
                                  viol=len(C.violations(bl, max_words=20, soft_words=20)),
                                  allwords=len(text.split())))


def line(label, rs):
    bl = [b for r in rs for b in r['blocks']]
    s = C.stats(bl)
    per = [C.stats(r['blocks'])['over20'] for r in rs]
    fk, ft = sum(r['facts'][0] for r in rs), sum(r['facts'][1] for r in rs)
    sem = sum(1 for b in bl if b['kind'] in ('para', 'bullet') for x in b['sents'] if x['semicolon'])
    print(f"{label:16s} runs={len(rs)} words/run={s['words'] / len(rs):6.0f} sentences={s['sentences']:4d} mean={s['mean']:4.1f} "
          f"max={s['max']:3d} >20w={s['over20']:4.1f}% (n={s['n_over20']:3d}; per run {' '.join('%.0f' % x for x in per)}) "
          f">25w={s['over25']:4.1f}% | paras={s['paras']:3d} >3s={s['n_para_over3']:2d} | bullets={s['bullets']:3d} "
          f">3s={s['n_bullet_over3']:2d} | bullet share={s['bullet_word_share']:4.1f}% | semicolons={sem:2d} | "
          f"checker lines/run={sum(r['viol'] for r in rs) / len(rs):4.1f}"
          + (f" | facts kept={fk}/{ft}" if ft else ''))
    return s


res = {}
tasks = sorted(set(t for t, _ in runs))
arms = [a for a in ('NONE', 'OLD', 'CUR', 'NEW', 'NEW2', 'CODEX', 'V3', 'SKILL', 'SKILLSLASH') if any(k[1] == a for k in runs)]
for t in tasks:
    print('==', t)
    for a in arms:
        if (t, a) in runs:
            res[f'{t}/{a}'] = line(a, runs[(t, a)])
print('== ALL TASKS (T1 to T3; T4 is the boundary task and is listed apart)')
for a in arms:
    rs = [r for (t, x), v in runs.items() if x == a and not t.startswith('T4') for r in v]
    if not rs:
        continue
    res[f'ALL/{a}'] = line(a, rs)
    res[f'ALL/{a}']['cost'] = sum(r['cost'] for r in rs)
    res[f'ALL/{a}']['runs'] = len(rs)
arms = [a for a in arms if f'ALL/{a}' in res]
print('cost by arm, T1 to T3:', {a: round(res[f'ALL/{a}']['cost'], 2) for a in arms})

print()
print('== side effects and structure, T1 to T3, 9 runs per version ==')
for a in arms:
    rs = [r for (t, x), v in runs.items() if x == a and not t.startswith('T4') for r in v]
    n = len(rs)
    S = [s for r in rs for b in r['blocks'] if b['kind'] in ('para', 'bullet') for s in b['sents'] if s['words']]
    J = [s for s in S if s['join'] >= 1]
    x = dict(out_tokens=sum(r['out_tokens'] for r in rs) / n, seconds=sum(r['seconds'] for r in rs) / n,
             cost_per_run=sum(r['cost'] for r in rs) / n, visible_words=sum(r['allwords'] for r in rs) / n,
             join=C.pct(len(J), len(S)), join_short=C.pct(sum(s['words'] <= 20 for s in J), len(S)),
             n_join=len(J), n_join_short=sum(s['words'] <= 20 for s in J),
             sub=C.pct(sum(s['sub'] >= 1 for s in S), len(S)),
             commas3=C.pct(sum(s['commas'] >= 3 for s in S), len(S)),
             paren_over8=sum(s['paren_max'] > 8 for s in S),
             tiny=C.pct(sum(s['words'] <= 6 for s in S), len(S)),
             band21_25=C.pct(sum(21 <= s['words'] <= 25 for s in S), len(S)))
    res[f'ALL/{a}'].update(x)
    print(f"{a:6s} runs={n} out tokens/run={x['out_tokens']:6.0f} seconds/run={x['seconds']:4.0f} cost/run=${x['cost_per_run']:.2f} "
          f"visible words/run={x['visible_words']:5.0f} | joins={x['join']:4.1f}% ({x['n_join']}), within 20 words={x['join_short']:4.1f}% "
          f"({x['n_join_short']}) | subordinating word={x['sub']:4.1f}% | 3+ commas={x['commas3']:4.1f}% | parentheses over 8 words={x['paren_over8']} | "
          f"sentences of 6 words or fewer={x['tiny']:4.1f}% | 21 to 25 words={x['band21_25']:4.1f}%")
allruns = [r for v in runs.values() for r in v]
print(f"total: {len(allruns)} runs, ${sum(r['cost'] for r in allruns):.2f}")
json.dump(res, open(ROOT + '/data/experiment_stats' + ('' if len(sys.argv) < 3 else '_' + sys.argv[2]) + '.json', 'w'), indent=1)
