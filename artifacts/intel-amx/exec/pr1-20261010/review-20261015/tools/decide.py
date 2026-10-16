import json, re, sys, collections
d=json.load(open(sys.argv[1]))
mine_reviews={5528432895,5528452495,5528464379,5528474853,5528495418}
out=[]
for t in d['threads']:
    cs=t['comments']['nodes']; first=cs[0]
    if not (first['pullRequestReview'] and first['pullRequestReview']['databaseId'] in mine_reviews): continue
    replies=[c for c in cs[1:]]
    reply='\n---\n'.join(c['body'] for c in replies)
    r=reply.strip().lower()
    if t['isResolved']: dec='skip-resolved'
    elif not replies: dec='accept-proposed'
    elif r.startswith('accept proposed'): dec='accept-proposed'
    elif r.startswith('accept the cut'): dec='accept-cut'
    elif r.startswith("let's settle"): dec='settle'
    elif r.startswith('just cut the comment') or r.startswith('just remove the inline comment'): dec='cut-instead'
    else: dec='question'
    m=re.search(r'```(?:cpp)?\s*\n(.*?)```', reply, re.S) if dec=='settle' else None
    body=first['body']
    pm=re.search(r'Proposed:\n```cpp\n(.*?)```', body, re.S)
    title=body.split('\n')[0]
    action = 'cut' if ('Proposed: cut the comment.' in body) else ('shorten/move/literal')
    out.append(dict(thread_id=t['id'], comment_id=first['databaseId'], path=t['path'], line=t['line'], start_line=t['startLine'],
        kind='A' if title.startswith('**[named bool]') else 'B', title=title, body=body, proposed=(pm.group(1) if pm else None),
        action=action, reply=reply, decision=dec, settle_text=(m.group(1) if m else None)))
out.sort(key=lambda x:(x['path'],x['line']))
json.dump(out,open(sys.argv[2],'w'),indent=1)
print(collections.Counter((o['kind'],o['decision']) for o in out))
print(collections.Counter(o['path'] for o in out))
for o in out:
    if o['decision'] in ('question','settle','cut-instead','skip-resolved'): print(o['decision'], o['path'], o['start_line'], o['line'], o['title'][:60])
