#!/usr/bin/env python3
"""Post one checker's comments on one PR as reviews of at most --max comments each, spaced by --sleep seconds,
with secondary-rate-limit backoff and a landed-check after a 502.

usage: post_checker2.py --pr N --checker A|B --comments all.json --head SHA --base SHA [--exclude posted.json]
       [--part-offset K] [--total-parts N] [--max 25] [--sleep 90] [--initial-wait 0] [--post]
"""
import argparse, json, subprocess, os, collections, sys, time
ap = argparse.ArgumentParser()
for k in ['pr', 'checker', 'comments', 'head', 'base']: ap.add_argument('--' + k, required=True)
ap.add_argument('--exclude'); ap.add_argument('--part-offset', type=int, default=0); ap.add_argument('--total-parts', type=int, default=0)
ap.add_argument('--max', type=int, default=25); ap.add_argument('--sleep', type=int, default=90); ap.add_argument('--initial-wait', type=int, default=0)
ap.add_argument('--post', action='store_true')
a = ap.parse_args()
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def log(*x): print(time.strftime('%H:%M:%S'), *x, flush=True)
comments = json.load(open(a.comments)); n_total = len(comments)
if a.exclude:
    ex = {(c['path'], c['line'], c['body'][:80]) for c in json.load(open(a.exclude))}
    comments = [c for c in comments if (c['path'], c['line'], c['body'][:80]) not in ex]
comments.sort(key=lambda c: (c['path'], c['line']))
tmpl = open(f'{S}/bodies/{a.checker}.tmpl.md').read()
RULE_B = {'1': 'Rule 1 (the name carries it)', '2': 'Rule 2 (restates identifiers)', '3': 'Rule 3 (one-line contract)',
          '4': 'Rule 4 (lines that map to no code)', '5': 'Rule 5 (call-site comment says only why here)', '6': 'Rule 6 (idiom comment)'}
RULE_A = {'bare-literal-argument': 'bare literal as a call argument', 'bare-literal-aggregate': 'bare literal in positional aggregate initialization',
          'bare-literal-template-argument': 'bare literal as a template argument', 'named-constant-not-argument': 'named constant outside an argument position'}
parts, cur = [], []
for path in sorted({c['path'] for c in comments}):
    for c in [c for c in comments if c['path'] == path]:
        if len(cur) >= a.max: parts.append(cur); cur = []
        cur.append(c)
if cur: parts.append(cur)
n = a.total_parts or (a.part_offset + len(parts))
allc = json.load(open(a.comments))
rules = collections.Counter(c['rule'] for c in allc); files = collections.Counter(c['path'] for c in allc)
rn = RULE_B if a.checker == 'B' else RULE_A
by_rule = '; '.join(f"{rn.get(r, r)}: {k}" for r, k in sorted(rules.items(), key=lambda x: -x[1]))
by_file = '; '.join(f"`{p}`: {k}" for p, k in sorted(files.items(), key=lambda x: -x[1]))
total_line = f"{n_total} inline comments in total on this PR, in {n} review{'s' if n > 1 else ''}.\n\nBy rule: {by_rule}.\n\nBy file: {by_file}."
os.makedirs(f'{S}/post', exist_ok=True)
def gh(args, inp=None):
    return subprocess.run(['gh', 'api'] + args + (['--input', inp] if inp else []), capture_output=True, text=True)
def landed(marker):
    r = gh([f'repos/positron-ai/tron/pulls/{a.pr}/reviews', '--paginate'])
    if r.returncode != 0: return None
    for rv in json.loads(r.stdout):
        if rv.get('user', {}).get('login') == 'jhan-positron' and marker in (rv.get('body') or ''): return rv['id']
    return None
if a.initial_wait and a.post: log(f'initial wait {a.initial_wait}s'); time.sleep(a.initial_wait)
for i, part in enumerate(parts, 1):
    k = a.part_offset + i
    pfiles = sorted({c['path'] for c in part})
    marker = f"This is part {k} of {n}: {len(part)} comments on " + ', '.join(f'`{p}`' for p in pfiles) + '.'
    count_line = total_line + (f"\n\n{marker}" if n > 1 else '')
    body = tmpl.replace('{{HEAD}}', a.head).replace('{{BASE}}', a.base).replace('{{COUNT_LINE}}', count_line)
    if a.checker == 'B':
        body = body.replace('Every finding was checked by three independent agents with different lenses', 'Every finding was checked by independent agents with different lenses')
    bf = f'{S}/post/body-{a.pr}-{a.checker}-{k}.md'; cf = f'{S}/post/comments-{a.pr}-{a.checker}-{k}.json'; pf = f'{S}/post/payload-{a.pr}-{a.checker}-{k}.json'
    open(bf, 'w').write(body); json.dump(part, open(cf, 'w'), indent=1)
    r = subprocess.run(['python3', '-I', f'{S}/tools/post_review.py', '--pr', a.pr, '--commit', a.head, '--lines', f'{S}/annot/{a.pr}/_lines.json',
                        '--comments', cf, '--body', bf, '--out', pf], capture_output=True, text=True)
    log(f'part {k}/{n} payload:', r.stdout.strip().replace('\n', ' | '))
    if not a.post: continue
    if n > 1 and landed(marker): log(f'part {k}/{n} already posted, skipping'); continue
    for attempt in range(1, 7):
        r = gh(['-X', 'POST', f'repos/positron-ai/tron/pulls/{a.pr}/reviews'], pf)
        if r.returncode == 0:
            d = json.loads(r.stdout); log(f'part {k}/{n} POSTED review {d.get("id")} {d.get("html_url")}'); break
        err = (r.stderr + r.stdout)[:300].replace('\n', ' ')
        if 'HTTP 502' in err or 'HTTP 504' in err:
            time.sleep(30); rid = landed(marker) if n > 1 else None
            if rid: log(f'part {k}/{n} landed as review {rid} despite the gateway error'); break
            log(f'part {k}/{n} gateway error, not landed, retry {attempt}: {err}'); time.sleep(120); continue
        if 'secondary rate limit' in err or 'HTTP 403' in err or 'HTTP 429' in err:
            wait = 300 * attempt; log(f'part {k}/{n} rate limited, waiting {wait}s (attempt {attempt}): {err[:120]}'); time.sleep(wait); continue
        log(f'part {k}/{n} FAILED: {err}'); sys.exit(1)
    else:
        log(f'part {k}/{n} gave up after retries'); sys.exit(1)
    if i < len(parts): time.sleep(a.sleep)
log('done')
