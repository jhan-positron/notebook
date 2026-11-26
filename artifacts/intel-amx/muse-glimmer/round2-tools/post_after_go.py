#!/usr/bin/env python3
"""Save the new description of tron PR 5022 and post the reply to Isaac, each with checks before and a read-back after.

Usage: post_after_go.py check | save-body | post-reply
  check      : runs every check of both steps and writes nothing to GitHub.
  save-body  : step 9. Replaces the PR description with pr5022-body.final.md and reads it back.
  post-reply : step 10. Posts reply.final.md as one conversation comment and reads it back.
Records go to the folder E below. Both write steps were approved by jhan on 2026-11-24 ("go"). Do not run them again.
"""
import json
import subprocess
import sys

REPO = 'positron-ai/tron'
PR = 5022
HEAD = '90a9110be5d2c6552267322c472902984dca8e0f'
E = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/after-go'
EXPECT = {'reviews': 5, 'inline': 56, 'conversation': 3}   # state after the automated review of the new head


def gh(args, payload=None):
    p = subprocess.run(['gh', 'api'] + args, input=None if payload is None else json.dumps(payload),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f'gh api {args[:3]} failed: {p.stderr[:400]}')
    return json.loads(p.stdout)


def text(name):
    t = open(f'{E}/{name}', encoding='utf-8').read()
    assert t.endswith('\n'), name
    return t[:-1]                # the file holds the text plus one newline that jq or the editor added


def same(a, b):
    """Equal, where newlines at the very end do not count (GitHub may trim them on save)."""
    return a.rstrip('\n') == b.rstrip('\n')


def state():
    pr = gh([f'repos/{REPO}/pulls/{PR}'])
    n = {'reviews': len(gh([f'repos/{REPO}/pulls/{PR}/reviews?per_page=100'])),
         'inline': len(gh([f'repos/{REPO}/pulls/{PR}/comments?per_page=100'])),
         'conversation': len(gh([f'repos/{REPO}/issues/{PR}/comments?per_page=100']))}
    return pr, n


def check_body(pr, n):
    assert pr['state'] == 'open' and pr['head']['sha'] == HEAD, (pr['state'], pr['head']['sha'])
    assert pr['body'] == text('pr5022-body-live-before-edit.md'), 'the live description changed since the copy was taken'
    assert n == EXPECT, f'new activity on the pull request: {n}'
    final = text('pr5022-body.final.md')
    words = len(final.split())
    assert words < 2000, words
    for name in ('RUN_ID', 'RUNNER_NAME', 'CPU_MODEL', 'ATTEMPT_N', 'N_PASS', 'N_TOTAL'):
        assert name not in final, name
    print(f'body checks hold: head {HEAD[:10]}, live description unchanged, counts {n}, final description {words} words')
    return final


def check_reply(pr, n, body_must_be_final):
    assert pr['state'] == 'open' and pr['head']['sha'] == HEAD, (pr['state'], pr['head']['sha'])
    if body_must_be_final:
        assert pr['body'] == text('pr5022-body.final.md'), 'the live description is not the final one'
    assert n == EXPECT, f'new activity on the pull request: {n}'
    reply = text('reply.final.md')
    for name in ('RUN_ID', 'RUNNER_NAME', 'CPU_MODEL', 'ATTEMPT_N', 'N_PASS', 'N_TOTAL'):
        assert name not in reply, name
    print(f'reply checks hold: head {HEAD[:10]}, counts {n}, reply {len(reply.split())} words')
    return reply


mode = sys.argv[1]
pr, n = state()
if mode == 'check':
    check_body(pr, n)
    check_reply(pr, n, body_must_be_final=False)
elif mode == 'save-body':
    final = check_body(pr, n)
    out = gh(['-X', 'PATCH', f'repos/{REPO}/pulls/{PR}', '--input', '-'], {'body': final})
    back = gh([f'repos/{REPO}/pulls/{PR}'])
    json.dump({'updated_at': back['updated_at'], 'html_url': back['html_url'], 'words': len(final.split()),
               'head': back['head']['sha'], 'body': back['body']}, open(f'{E}/posted-body.json', 'w'), indent=1)
    assert same(back['body'], final), 'read-back differs from the text sent'
    print(f'description saved and read back: {back["updated_at"]}, {len(final.split())} words, equal to the text sent')
elif mode == 'post-reply':
    reply = check_reply(pr, n, body_must_be_final=True)
    out = gh(['-X', 'POST', f'repos/{REPO}/issues/{PR}/comments', '--input', '-'], {'body': reply})
    back = gh([f'repos/{REPO}/issues/comments/{out["id"]}'])
    json.dump({'id': back['id'], 'html_url': back['html_url'], 'created_at': back['created_at'],
               'user': back['user']['login'], 'body': back['body']}, open(f'{E}/posted-reply.json', 'w'), indent=1)
    assert same(back['body'], reply), 'read-back differs from the text sent'
    print(f'reply posted and read back: {back["html_url"]} at {back["created_at"]}, equal to the text sent')
else:
    raise SystemExit(__doc__)
