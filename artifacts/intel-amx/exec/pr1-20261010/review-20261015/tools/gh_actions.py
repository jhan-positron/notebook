#!/usr/bin/env python3
"""GitHub actions after the push. usage:
  gh_actions.py resolve <decisions.json> <applied-ids.txt>   # resolve the threads of the applied items
  gh_actions.py reply <comment_id> <body-file>              # reply in a review thread
  gh_actions.py comment <body-file>                         # PR comment
"""
import json, subprocess, sys, time
PR = 4868; REPO = 'positron-ai/tron'
def gql(q, **vars):
    args = ['gh', 'api', 'graphql', '-f', f'query={q}']
    for k, v in vars.items(): args += ['-f', f'{k}={v}']
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode: raise SystemExit(f'gql failed: {r.stderr[:500]}')
    return json.loads(r.stdout)
cmd = sys.argv[1]
if cmd == 'resolve':
    dec = json.load(open(sys.argv[2])); ids = set(open(sys.argv[3]).read().split())
    work = json.load(open(sys.argv[4]))  # work.json: id -> thread_id
    tid = {w['id']: w['thread_id'] for w in work}
    done = 0
    for fid in sorted(ids):
        t = tid[fid]
        d = gql('mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}', id=t)
        ok = d['data']['resolveReviewThread']['thread']['isResolved']; done += ok
        print(fid, t, 'resolved' if ok else 'NOT resolved'); time.sleep(1.0)
    print('resolved', done, 'of', len(ids))
elif cmd == 'reply':
    cid, body = sys.argv[2], open(sys.argv[3]).read()
    r = subprocess.run(['gh', 'api', f'repos/{REPO}/pulls/{PR}/comments/{cid}/replies', '-f', f'body={body}'], capture_output=True, text=True)
    print(r.returncode, r.stdout[:300], r.stderr[:300])
elif cmd == 'comment':
    r = subprocess.run(['gh', 'pr', 'comment', str(PR), '--repo', REPO, '--body-file', sys.argv[2]], capture_output=True, text=True)
    print(r.returncode, r.stdout[:300], r.stderr[:300])
