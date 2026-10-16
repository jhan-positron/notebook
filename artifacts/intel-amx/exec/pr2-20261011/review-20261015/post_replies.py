#!/usr/bin/env python3
"""Reply to the applied review threads of PR #4887 and resolve them.
usage: post_replies.py <sha> [--dry]   (reads threads.json next to this file)"""
import json, subprocess, sys, time, pathlib
sha = sys.argv[1]; dry = '--dry' in sys.argv
here = pathlib.Path(__file__).parent
d = json.load(open(here / 'threads.json'))
nodes = d['data']['repository']['pullRequest']['reviewThreads']['nodes']
SETTLE = {'h/tron/kernels/k_vnni.hpp:8'}
log = open(here / 'post_replies.log', 'a')
for n in nodes:
    if n['isResolved']: continue  # the two "Reject proposed" threads
    first = n['comments']['nodes'][0]; key = f"{n['path']}:{n['line']}"
    replies = [c for c in n['comments']['nodes'][1:]]
    if key in SETTLE: body = f"Applied your wording in {sha}."
    else: body = f"Applied in {sha}."
    print(key, '->', body, '(answered)' if replies else '(no answer: accept)')
    if dry: continue
    r = subprocess.run(['gh','api','-X','POST',f"repos/positron-ai/tron/pulls/4887/comments/{first['databaseId']}/replies",'-f',f'body={body}'],capture_output=True,text=True)
    log.write(f"{key} reply rc={r.returncode} {r.stdout[:80]!r} {r.stderr[:200]!r}\n"); log.flush()
    if r.returncode: print('  REPLY FAILED', r.stderr[:200]); continue
    q = 'mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
    r = subprocess.run(['gh','api','graphql','-f',f'query={q}','-f',f"id={n['id']}"],capture_output=True,text=True)
    log.write(f"{key} resolve rc={r.returncode} {r.stdout[:80]!r} {r.stderr[:200]!r}\n"); log.flush()
    if r.returncode: print('  RESOLVE FAILED', r.stderr[:200])
    time.sleep(4)
