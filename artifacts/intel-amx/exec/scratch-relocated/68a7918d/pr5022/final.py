import json, collections, statistics, datetime as dt
def ts(s): return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
rows = [json.loads(l) for l in open('isaac_all_comments.jsonl')]
revs = json.load(open('isaac_reviews.json'))
mine = sorted([r for r in rows if r['pr'] == 5022], key=lambda r: (r['created_at'], r['id']))
tot = sum(len(r['body']) for r in mine)
span = (ts(mine[-1]['created_at']) - ts(mine[0]['created_at'])).total_seconds()
print("PR 5022: comments", len(mine), "chars", tot, "span_s", span, "chars/s", round(tot/span, 1), "mean chars", round(tot/len(mine)), "min", min(len(r['body']) for r in mine), "max", max(len(r['body']) for r in mine))
print("mean gap s", round(span/(len(mine)-1), 2))
hold = ts('2026-10-23T15:42:07Z') - ts(mine[-1]['created_at'])
print("hold from last draft comment to publish:", hold, "=", round(hold.total_seconds()/3600, 2), "h")
print("review opened 04:20:45 -> first comment", (ts(mine[0]['created_at']) - ts('2026-10-23T04:20:45Z')).total_seconds(), "s")
wk = [r for r in rows if ts(r['created_at']) >= dt.datetime(2026,11,16)]
print("week of 2026-11-16: comments", len(wk), "with trailer", sum('Checked by:' in r['body'] for r in wk), "chars", sum(len(r['body']) for r in wk), "days", sorted({r['created_at'][:10] for r in wk}))
print("all: comments", len(rows), "PRs", len({r['pr'] for r in rows}), "trailer", sum('Checked by:' in r['body'] for r in rows), "date range", min(r['created_at'] for r in rows), max(r['created_at'] for r in rows))
bodies = [r for r in revs if (r['body'] or '').strip()]
print("summaries:", len(bodies), "with 'Coverage gaps':", sum('Coverage gaps' in r['body'] for r in bodies), "with agent id tag:", sum(('@glm' in r['body'] or '@fable' in r['body'] or '@astra' in r['body'] or '@grok' in r['body'] or '@gemini' in r['body']) for r in bodies))
hrs = collections.Counter(ts(r['submitted_at']).hour for r in bodies if r.get('submitted_at'))
print("summary-bearing publishes between 05:00 and 14:59 UTC:", sum(hrs[h] for h in range(5,15)), "of", sum(hrs.values()))
print("  at hour 15:", hrs[15], " hour 04:", hrs[4])
# PR 4958 review
r4958 = [r for r in revs if r['pr']==4958 and r.get('submitted_at','').startswith('2026-10-23T15:42')]
print("PR 4958 review:", [(r['id'], r['submitted_at'], r['state'], len(r['body'] or '')) for r in r4958])
c4958 = sorted([r for r in rows if r['pr']==4958 and r['review']==r4958[0]['id']], key=lambda r: r['created_at'])
print("  comments", len(c4958), c4958[0]['created_at'], c4958[-1]['created_at'])
