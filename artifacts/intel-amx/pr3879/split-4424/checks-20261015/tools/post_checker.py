#!/usr/bin/env python3
"""Post one checker's comments on one PR as reviews of at most MAX comments each (grouped by file).

usage: post_checker.py --pr N --checker A|B --comments file.json --head SHA --base SHA [--post] [--max 60]
"""
import argparse, json, subprocess, os, collections, sys
ap = argparse.ArgumentParser()
for k in ['pr', 'checker', 'comments', 'head', 'base']: ap.add_argument('--' + k, required=True)
ap.add_argument('--post', action='store_true'); ap.add_argument('--max', type=int, default=60)
a = ap.parse_args()
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
comments = json.load(open(a.comments))
comments.sort(key=lambda c: (c['path'], c['line']))
tmpl = open(f'{S}/bodies/{a.checker}.tmpl.md').read()
RULE_B = {'1': 'Rule 1 (the name carries it)', '2': 'Rule 2 (restates identifiers)', '3': 'Rule 3 (one-line contract)',
          '4': 'Rule 4 (lines that map to no code)', '5': 'Rule 5 (call-site comment says only why here)', '6': 'Rule 6 (idiom comment)'}
RULE_A = {'bare-literal-argument': 'bare literal as a call argument', 'bare-literal-aggregate': 'bare literal in positional aggregate initialization',
          'bare-literal-template-argument': 'bare literal as a template argument', 'named-constant-not-argument': 'named constant outside an argument position'}
# chunk by file, at most a.max per review
parts, cur = [], []
for path, grp in collections.OrderedDict((p, [c for c in comments if c['path'] == p]) for p in sorted({c['path'] for c in comments})).items():
    for c in grp:
        if len(cur) >= a.max: parts.append(cur); cur = []
        cur.append(c)
if cur: parts.append(cur)
n = len(parts)
rules = collections.Counter(c['rule'] for c in comments); files = collections.Counter(c['path'] for c in comments)
rn = RULE_B if a.checker == 'B' else RULE_A
by_rule = '; '.join(f"{rn.get(r, r)}: {k}" for r, k in sorted(rules.items(), key=lambda x: -x[1]))
by_file = '; '.join(f"`{p}`: {k}" for p, k in sorted(files.items(), key=lambda x: -x[1]))
total_line = f"{len(comments)} inline comments in total on this PR, in {n} review{'s' if n > 1 else ''} of at most {a.max} comments each.\n\nBy rule: {by_rule}.\n\nBy file: {by_file}."
results = []
for i, part in enumerate(parts, 1):
    pfiles = sorted({c['path'] for c in part})
    count_line = total_line + (f"\n\nThis is part {i} of {n}: {len(part)} comments on " + ', '.join(f'`{p}`' for p in pfiles) + '.' if n > 1 else '')
    body = tmpl.replace('{{HEAD}}', a.head).replace('{{BASE}}', a.base).replace('{{COUNT_LINE}}', count_line)
    if a.checker == 'B':
        body = body.replace('Every finding was checked by three independent agents with different lenses', 'Every finding was checked by independent agents with different lenses')
    os.makedirs(f'{S}/post', exist_ok=True)
    bf = f'{S}/post/body-{a.pr}-{a.checker}-{i}.md'; cf = f'{S}/post/comments-{a.pr}-{a.checker}-{i}.json'; pf = f'{S}/post/payload-{a.pr}-{a.checker}-{i}.json'
    open(bf, 'w').write(body); json.dump(part, open(cf, 'w'), indent=1)
    cmd = ['python3', '-I', f'{S}/tools/post_review.py', '--pr', a.pr, '--commit', a.head, '--lines', f'{S}/annot/{a.pr}/_lines.json',
           '--comments', cf, '--body', bf, '--out', pf] + (['--post'] if a.post else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"part {i}/{n}:", r.stdout.strip().replace('\n', ' | '), r.stderr.strip()[:300])
    if r.returncode != 0:
        print("STOPPING: part failed"); sys.exit(1)
