#!/usr/bin/env python3
"""Extract prose that Claude wrote after the skill's last edit.

Sources, per session transcript:
  - chat:  assistant text blocks (what the user reads in the terminal)
  - write: Write tool calls to .html / .md files (reports)
Output: one JSON line per document in docs.jsonl
"""
import json, glob, os, sys, datetime

CUTOFF = datetime.datetime(2026, 11, 15, 22, 51, tzinfo=datetime.timezone.utc)  # 14:51 PST
ROOT = '/home/jhan/.claude/projects'
OUT = sys.argv[1]

def ts(d):
    t = d.get('timestamp')
    if not t:
        return None
    try:
        return datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    except Exception:
        return None

n_files = 0
docs = []
for path in glob.glob(ROOT + '/**/*.jsonl', recursive=True):
    base = os.path.basename(path)
    if base.startswith('journal'):
        continue
    if os.path.getmtime(path) < CUTOFF.timestamp():
        continue
    n_files += 1
    proj = path[len(ROOT)+1:].split('/')[0].replace('-home-jhan-workspace-', '')
    is_agent = base.startswith('agent-')
    skill_used = False
    with open(path, errors='replace') as f:
        for line in f:
            if '"assistant"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get('type') != 'assistant':
                continue
            when = ts(d)
            m = d.get('message') or {}
            for blk in m.get('content') or []:
                if not isinstance(blk, dict):
                    continue
                if blk.get('type') == 'tool_use':
                    inp = blk.get('input') or {}
                    if blk.get('name') == 'Skill' and 'plain-english' in str(inp.get('skill', '')):
                        skill_used = True
                    if blk.get('name') == 'Write' and when and when >= CUTOFF:
                        fp = str(inp.get('file_path', ''))
                        if fp.endswith(('.html', '.md')):
                            docs.append(dict(kind='write', proj=proj, session=base, agent=is_agent,
                                             when=when.isoformat(), path=fp,
                                             text=inp.get('content', ''), skill_called=skill_used,
                                             model=m.get('model')))
                elif blk.get('type') == 'text' and when and when >= CUTOFF and not is_agent:
                    t = blk.get('text', '')
                    if t.strip():
                        docs.append(dict(kind='chat', proj=proj, session=base, agent=False,
                                         when=when.isoformat(), path='', text=t,
                                         skill_called=skill_used, model=m.get('model')))

with open(OUT, 'w') as f:
    for d in docs:
        f.write(json.dumps(d) + '\n')
print('transcripts scanned:', n_files)
print('documents:', len(docs))
import collections
c = collections.Counter((d['kind'], d['agent']) for d in docs)
print(c)
