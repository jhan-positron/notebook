import html, os, re
P='parts/'
brief=open('/home/jhan/workspace/random/input-2-ai/internalize-concepts.md','rb').read()
GLOSS=[
 ('K/V','The key and value vectors of attention, stored per token, layer, and KV head.'),
 ('ranged mask, visible()','Sorted list of token_id spans with SW_REQUIRED and HW_AVAILABLE bitmasks; visible(job) tests their union.'),
 ('minibatch, items[], batch_job_ix','A subset of this pass\'s queries; items[] lists their token_job_ids; batch_job_ix is a query\'s slot inside it.'),
]
rows='\n'.join(f"<tr><td>{html.escape(t)}</td><td>{html.escape(d)}</td></tr>" for t,d in GLOSS)
app=open(P+'short/p5s.html').read().replace('{{GLOSSARY}}',rows).replace('{{BRIEF}}',html.escape(brief.decode())).replace('{{BRIEF_BYTES}}',str(len(brief)))
head=open(P+'p1_head.html').read().replace('<title>TRON attention concepts</title>','<title>TRON attention concepts (short)</title>')
js=open(P+'p4a.js').read()+open(P+'p4b.js').read()+open(P+'p4c.js').read()
def guard(old,new):
    global js
    assert js.count(old)==1, ('guard miss', old[:70], js.count(old)); js=js.replace(old,new)
guard("  const svg = $('#svg-p2'); clear(svg);", "  const svg = $('#svg-p2'); if (!svg) return; clear(svg);")
guard("  const svg = $('#svg-size'); clear(svg);", "  const svg = $('#svg-size'); if (!svg) return; clear(svg);")
guard("  const svg = $('#svg-sched'); clear(svg);", "  const svg = $('#svg-sched'); if (!svg) return; clear(svg);")
guard("renderStrips($('#fig-strips0 [data-role=svg]'), MOCK.INF);", "{ const s0 = $('#fig-strips0 [data-role=svg]'); if (s0) renderStrips(s0, MOCK.INF); }")
guard("makeWalker($('#fig-walk0'), { layer: '0', mb: '0', q: '0' });", "if ($('#fig-walk0')) makeWalker($('#fig-walk0'), { layer: '0', mb: '0', q: '0' });")
guard("  $('#contrast-line').textContent = ", "  const _cl = $('#contrast-line'); if (_cl) _cl.textContent = ")
guard("  const d = $('#dumb-table'); const t = document.createElement('table'); t.className = 'small';", "  const d = $('#dumb-table'); if (!d) return; const t = document.createElement('table'); t.className = 'small';")
guard("    const d = $('#mask-table'); const t = document.createElement('table'); t.className = 'small';", "    const d = $('#mask-table'); if (!d) return; const t = document.createElement('table'); t.className = 'small';")
out=head+open(P+'short/p2s.html').read()+open(P+'short/p3s.html').read()+app+js+'</body>\n</html>\n'
dst='/home/jhan/workspace/random/from-claude/TRON-concepts-claude-short.html'
open(dst,'w').write(out)
# word count of visible text
nos=re.sub(r'<script.*?</script>','',out,flags=re.S); nos=re.sub(r'<style.*?</style>','',nos,flags=re.S)
vis=html.unescape(re.sub(r'<[^>]+>',' ',nos))
print('wrote',dst,len(out),'bytes; visible words:',len(vis.split()))
# per-section words
secs=re.split(r'(?=<h2 )', nos)
for s in secs:
    m=re.search(r'<h2[^>]*>(.*?)</h2>', s); name=re.sub(r'<[^>]+>','',m.group(1)) if m else 'head'
    print(f"  {len(html.unescape(re.sub(r'<[^>]+>',' ',s)).split()):5d}  {name[:60]}")
