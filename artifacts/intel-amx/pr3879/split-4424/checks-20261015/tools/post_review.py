#!/usr/bin/env python3
"""Build (and optionally post) one GitHub review with inline comments.

usage: post_review.py --pr N --commit SHA --lines annot/N/_lines.json --comments comments.json --body body.md --out payload.json [--post]
Validates every comment line against the RIGHT-side lines of the PR diff; a multi-line range is kept only when every line in it is in the diff.
"""
import argparse, json, subprocess, sys
ap = argparse.ArgumentParser()
for k in ['pr', 'commit', 'lines', 'comments', 'body', 'out']: ap.add_argument('--' + k, required=True)
ap.add_argument('--post', action='store_true')
a = ap.parse_args()
lines = json.load(open(a.lines)); comments = json.load(open(a.comments)); body = open(a.body).read()
payload = {'commit_id': a.commit, 'body': body, 'event': 'COMMENT', 'comments': []}
bad = []
for c in comments:
    right = set(lines.get(c['path'], {}).get('right', [])); added = set(lines.get(c['path'], {}).get('added', []))
    line, start = c['line'], c.get('start_line', c['line'])
    inrange = [l for l in added if start <= l <= line]
    if inrange and (line not in added or start not in added):
        start, line = min(inrange), max(inrange)  # anchor on the added lines of the block
    if line not in right:
        if start in right: line, start = start, start
        else: bad.append((c['path'], c['line'], 'line not in diff')); continue
    entry = {'path': c['path'], 'line': line, 'side': 'RIGHT', 'body': c['body']}
    if start < line and all(l in right for l in range(start, line + 1)):
        entry['start_line'] = start; entry['start_side'] = 'RIGHT'
    if line not in added and start not in added:
        bad.append((c['path'], c['line'], 'WARNING: anchored on a context line, not an added line'))
    payload['comments'].append(entry)
json.dump(payload, open(a.out, 'w'), indent=1)
print(f"PR {a.pr}: {len(payload['comments'])} comments in payload, {len([b for b in bad if 'not in diff' in b[2]])} dropped")
for b in bad: print('  ', b)
if a.post:
    r = subprocess.run(['gh', 'api', '-X', 'POST', f'repos/positron-ai/tron/pulls/{a.pr}/reviews', '--input', a.out], capture_output=True, text=True)
    if r.returncode != 0: print('POST FAILED', r.stderr[:2000], r.stdout[:2000]); sys.exit(1)
    d = json.loads(r.stdout); print('posted review', d.get('id'), d.get('html_url'))
