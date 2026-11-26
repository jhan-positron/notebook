import json, subprocess, sys
from datetime import datetime, timedelta, timezone

# Lists activity on one GitHub pull request inside the last schedule window. REST only, read-only.
# The scheduled task runs at minute 17 of every hour. A run reports the hour that ended at the
# latest minute 17, so runs that follow each other cover windows that touch and do not overlap.
# Optional argument: a start time (2026-11-20T17:00:00Z) in place of the window start, for tests.
REPO, PR, OWN, MINUTE = 'positron-ai/tron', 5022, 'jhan-positron', 17
SKIP = {'reviewed', 'commented', 'line-commented', 'subscribed', 'unsubscribed', 'mentioned', 'committed'}
FORM = '%Y-%m-%dT%H:%M:%SZ'

now = datetime.now(timezone.utc)
end = now.replace(minute=MINUTE, second=0, microsecond=0)
if end > now:
    end -= timedelta(hours=1)
lo, hi = (end - timedelta(hours=1)).strftime(FORM), end.strftime(FORM)
if len(sys.argv) > 1:
    lo = sys.argv[1]

def get(path):
    items, page = [], 1
    while True:
        url = 'repos/{}/{}?per_page=100&page={}'.format(REPO, path, page)
        p = subprocess.run(['gh', 'api', url], capture_output=True, text=True)
        if p.returncode != 0:
            print('RESULT: FETCH FAILED', path, ' '.join((p.stderr or p.stdout).split())[:300])
            sys.exit(2)
        chunk = json.loads(p.stdout)
        if isinstance(chunk, dict):
            return chunk
        items += chunk
        if len(chunk) < 100:
            return items
        page += 1

def who(user):
    return (user or {}).get('login') or 'nobody'

def inside(t):
    return bool(t) and lo < t <= hi

def short(text):
    flat = ' '.join((text or '').split())
    return flat[:400] + ('...' if len(flat) > 400 else '')

found = []  # (time, author, what, text, quiet)
for r in get('pulls/{}/reviews'.format(PR)):
    t = r.get('submitted_at')
    if inside(t):
        found.append((t, who(r['user']), 'review, state ' + r['state'] + ' ' + r['html_url'], r.get('body'), False))
for c in get('pulls/{}/comments'.format(PR)):
    t = max(c['created_at'], c['updated_at'])
    if inside(t):
        kind = 'reply in a thread' if c.get('in_reply_to_id') else 'new thread'
        where = '{}:{}'.format(c['path'], c.get('line') or c.get('original_line'))
        found.append((t, who(c['user']), 'inline comment, {}, at {} {}'.format(kind, where, c['html_url']), c.get('body'), False))
for c in get('issues/{}/comments'.format(PR)):
    t = max(c['created_at'], c['updated_at'])
    if inside(t):
        edited = c['created_at'] <= lo
        quiet = edited and who(c['user']) == 'cursor[bot]'  # this bot rewrites its summary at every push
        found.append((t, who(c['user']), 'conversation comment{} {}'.format(' (edited)' if edited else '', c['html_url']), c.get('body'), quiet))
for e in get('issues/{}/timeline'.format(PR)):
    t = e.get('created_at')
    if e.get('event') in SKIP or not inside(t):
        continue
    detail = (e.get('requested_reviewer') or {}).get('login') or (e.get('requested_team') or {}).get('slug') or (e.get('label') or {}).get('name') or ''
    found.append((t, who(e.get('actor')), ('event ' + e['event'] + ' ' + detail).strip(), '', False))

pr = get('pulls/{}'.format(PR))
now_pr = 'merged' if pr.get('merged') else pr['state']
merge = pr.get('mergeable_state') or 'unknown'
conflict = merge == 'dirty' and end.hour == 17  # one reminder per day, in the run of 17:17 UTC

found.sort(key=lambda f: f[0])
others = [f for f in found if f[1] != OWN and not f[4]]
print('RESULT:', 'ALERT' if others or conflict else 'NOTHING TO REPORT')
print('WINDOW: after {} up to {}'.format(lo, hi))
print('STATE: {}, merge state {}, head {}'.format(now_pr, merge, pr['head']['sha'][:10]))
if conflict:
    print('CONFLICT: the pull request has a merge conflict with its base branch')
for t, author, what, text, quiet in found:
    tag = 'OWN' if author == OWN else 'QUIET' if quiet else 'ITEM'
    print('{} {} {}: {}'.format(tag, t, author, what))
    if text and tag == 'ITEM':
        print('     TEXT: ' + short(text))
