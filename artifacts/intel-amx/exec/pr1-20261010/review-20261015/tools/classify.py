import json, re, sys, collections
d=json.load(open(sys.argv[1]))
mine_reviews={5528432895,5528452495,5528464379,5528474853,5528495418}
rows=[]
for t in d['threads']:
    cs=t['comments']['nodes']
    first=cs[0]
    is_mine = first['pullRequestReview'] and first['pullRequestReview']['databaseId'] in mine_reviews
    kind = 'named-bool' if first['body'].startswith('**[named bool]') else ('comments' if first['body'].startswith('**[comments]') else 'other')
    replies=[c for c in cs[1:]]
    rows.append(dict(id=t['id'], path=t['path'], line=t['line'], startLine=t['startLine'], origLine=t['originalLine'], resolved=t['isResolved'], outdated=t['isOutdated'],
        mine=bool(is_mine), kind=kind, review=first['pullRequestReview'] and first['pullRequestReview']['databaseId'],
        first_id=first['databaseId'], title=first['body'].split('\n')[0][:110], nreplies=len(replies),
        replies=[dict(author=c['author']['login'], body=c['body'], id=c['databaseId'], at=c['createdAt']) for c in replies]))
json.dump(rows,open(sys.argv[2],'w'),indent=1)
c=collections.Counter((r['mine'],r['kind'],r['resolved']) for r in rows)
for k,v in sorted(c.items()): print(k,v)
print('--- replies on my threads:')
for r in rows:
    if r['mine'] and r['nreplies']:
        print(f"{r['path']}:{r['line']} resolved={r['resolved']} outdated={r['outdated']} | {r['title']}")
        for rp in r['replies']:
            print(f"    <{rp['author']}> {rp['body'][:300]!r}")
print('--- not mine:')
for r in rows:
    if not r['mine']:
        print(f"{r['path']}:{r['line']} resolved={r['resolved']} review={r['review']} n={1+r['nreplies']} | {r['title']}")
