#!/usr/bin/env python3
"""Extract assistant chat text (main sessions only) since START, with the user prompt that preceded it."""
import json, glob, os, sys, datetime, re
START = datetime.datetime(2026, 10, 20, tzinfo=datetime.timezone.utc)
ROOT = '/home/jhan/.claude/projects'
out = open(sys.argv[1], 'w')
n = 0
for path in glob.glob(ROOT + '/*/*.jsonl'):
    base = os.path.basename(path)
    if base.startswith(('journal', 'agent-')) or os.path.getmtime(path) < START.timestamp():
        continue
    proj = path[len(ROOT)+1:].split('/')[0].replace('-home-jhan-workspace-', '')
    last_user = ''
    with open(path, errors='replace') as f:
        for line in f:
            if '"type":"user"' in line or '"type": "user"' in line:
                try: d = json.loads(line)
                except Exception: continue
                if d.get('type') == 'user' and not d.get('isMeta') and not d.get('isSidechain'):
                    c = (d.get('message') or {}).get('content')
                    t = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text') if isinstance(c, list) else ''
                    if t.strip() and not t.startswith('<') :
                        last_user = t
                continue
            if '"assistant"' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            if d.get('type') != 'assistant' or d.get('isSidechain'): continue
            ts = d.get('timestamp')
            if not ts: continue
            when = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if when < START: continue
            m = d.get('message') or {}
            for blk in m.get('content') or []:
                if isinstance(blk, dict) and blk.get('type') == 'text' and blk.get('text', '').strip():
                    out.write(json.dumps(dict(proj=proj, session=base, when=ts, text=blk['text'], model=m.get('model'),
                                              asked=bool(re.search(r'short(er)? sentence|bullet', last_user, re.I)),
                                              prompt=last_user[:400])) + '\n')
                    n += 1
print('chat text blocks:', n)
