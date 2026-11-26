#!/usr/bin/env python3
"""dump_session.py FILE [--users] [--ssh] [--since ISO] : print user messages and ssh commands of a session record."""
import json, sys
path = sys.argv[1]
want_users = '--users' in sys.argv
want_ssh = '--ssh' in sys.argv
since = None
if '--since' in sys.argv:
    since = sys.argv[sys.argv.index('--since') + 1]
maxlen = 1500
if '--max' in sys.argv:
    maxlen = int(sys.argv[sys.argv.index('--max') + 1])
with open(path, errors='replace') as f:
    for n, line in enumerate(f, 1):
        try:
            o = json.loads(line)
        except Exception:
            continue
        ts = o.get('timestamp', '')
        if since and ts and ts < since:
            continue
        t = o.get('type')
        msg = o.get('message') or {}
        content = msg.get('content')
        if t == 'user' and want_users and not o.get('isSidechain'):
            if isinstance(content, str):
                txt = content
            elif isinstance(content, list):
                txt = '\n'.join(c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text')
            else:
                txt = ''
            txt = txt.strip()
            if txt and not txt.startswith('<system-reminder>') and 'tool_result' not in txt[:30]:
                print(f'--- L{n} {ts} USER: {txt[:maxlen]}')
        if t == 'assistant' and want_ssh and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Bash':
                    cmd = (c.get('input') or {}).get('command', '')
                    if '192.168.2.45' in cmd or 'ssh ' in cmd:
                        print(f'--- L{n} {ts} SSH: {cmd[:maxlen]}')
