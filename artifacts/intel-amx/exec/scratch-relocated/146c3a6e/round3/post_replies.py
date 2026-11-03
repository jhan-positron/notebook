# Post the round-3 replies: python3 -I post_replies.py <draft.md> <sha> [--post] [--resolve]
import json, re, subprocess, sys, pathlib
draft, sha = pathlib.Path(sys.argv[1]).read_text(), sys.argv[2]
post, resolve = '--post' in sys.argv, '--resolve' in sys.argv
subs = {
 'COMMIT': f'[{sha[:10]}](https://github.com/positron-ai/tron/commit/{sha})',
 'KILLSWITCH_LINE': '`test cases: 4 | 2 passed | 2 skipped`, `assertions: 4111 | 4111 passed`, exit code 0',
 'DISPATCH_LINE': 't_amx_dispatch_dtype 3,694 assertions / 1 case pass',
 'NUMERICS_LINE': 't_amx_numerics 17,425 / 4 pass',
 'QFILL_LINES': '143-152', 'ALIAS_LINES': '138-141', 'GH_LINE': '85', 'REQ_LINES': '207-209',
 'QK_CMT': '162-163', 'PV_CMT': '218-219', 'SEC_LINES': '303-306', 'KV32_LINES': '117-122',
 'PAD_LINES': '1551-1552', 'ZERO_LINE': '150',
}
threads = {  # root comment id -> (reply body, thread node id to resolve or None)
}
for m in re.finditer(r'^## (\d{10}) [^\n]*\n(.*?)(?=^## |\Z)', draft, re.S | re.M):
    body = m.group(2).strip()
    for k in sorted(subs, key=len, reverse=True): body = body.replace(k, subs[k])
    assert not any(k in body for k in subs) and 'COMMIT' not in body, body
    threads[m.group(1)] = body
RESOLVE = {'4308443056': 'PRRT_kwDOKStajs6tt0Hw', '4308443061': 'PRRT_kwDOKStajs6tt0Hx', '4308443185': 'PRRT_kwDOKStajs6tt0I-',
           '4308443205': 'PRRT_kwDOKStajs6tt0JH', '4308443322': 'PRRT_kwDOKStajs6tt0KM', '4308443331': 'PRRT_kwDOKStajs6tt0KR',
           '4308443490': 'PRRT_kwDOKStajs6tt0L3', '4308443569': 'PRRT_kwDOKStajs6tt0Mp', '4308444165': 'PRRT_kwDOKStajs6tt0S9',
           '4308444171': 'PRRT_kwDOKStajs6tt0TB'}
posted = {}
for cid, body in threads.items():
    print('=' * 10, cid); print(body); print()
    if post:
        r = subprocess.run(['gh', 'api', f'repos/positron-ai/tron/pulls/5015/comments/{cid}/replies', '-f', f'body={body}'],
                           capture_output=True, text=True)
        if r.returncode: print('POST FAILED', cid, r.stderr); continue
        posted[cid] = json.loads(r.stdout)['id']; print('posted', posted[cid])
if resolve:
    for cid, node in RESOLVE.items():
        q = 'mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
        r = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={q}', '-f', f'id={node}'], capture_output=True, text=True)
        print('resolve', cid, 'ok' if r.returncode == 0 and '"isResolved":true' in r.stdout else r.stdout + r.stderr)
pathlib.Path('posted.json').write_text(json.dumps(posted, indent=1))
