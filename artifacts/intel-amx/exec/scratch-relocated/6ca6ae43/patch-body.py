import json, subprocess, sys
S='/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-sync-tensor-type-2-PR4424/6ca6ae43-c95c-4694-a9b9-f7448886a646/scratchpad'
def fetch():
    out = subprocess.run(['gh','api','repos/positron-ai/tron/pulls/4424'], capture_output=True, text=True, check=True).stdout
    return json.loads(out)['body']
norm = lambda s: s.replace('\r\n','\n').rstrip('\n')
last = open(f'{S}/live-body.md', encoding='utf-8').read()
live_now = fetch()
if norm(live_now) != norm(last):
    open(f'{S}/live-body.changed.md','w', encoding='utf-8').write(live_now)
    print('ABORT: the live body changed since the last fetch; saved to live-body.changed.md'); sys.exit(2)
new = open(f'{S}/new-body.md', encoding='utf-8').read()
json.dump({'body': new}, open(f'{S}/payload.json','w', encoding='utf-8'), ensure_ascii=False)
if '--dry-run' in sys.argv:
    print('dry run: live body unchanged; payload.json written'); sys.exit(0)
subprocess.run(['gh','api','-X','PATCH','repos/positron-ai/tron/pulls/4424','--input',f'{S}/payload.json'], capture_output=True, text=True, check=True)
after = fetch()
ok = norm(after) == norm(new)
open(f'{S}/live-body.md','w', encoding='utf-8').write(after)
print('PATCHED; re-fetched body matches new-body.md:', ok, '| lines', after.count('\n')+1)
sys.exit(0 if ok else 3)
