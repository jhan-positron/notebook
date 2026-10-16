import collections
import datetime
import hashlib
import html
import json
import pathlib
import re
import shutil
import tarfile

ROOT = pathlib.Path('/tmp/wade-review-refresh')
WORK = pathlib.Path('/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525')
OUT = WORK / 'evidence/wade-review-refresh-20261006'
OUT.mkdir(parents=True, exist_ok=True)
corpus = json.loads((ROOT / 'corpus.json').read_text())
ledger = [x for i in range(3) for x in json.loads((ROOT / f'classification-{i}.json').read_text())]
lookup = {(x['repo'], x['number']): x for x in ledger}
assert len(lookup) == len(corpus) == 191
for pr in corpus:
    assert sorted(lookup[(pr['repo'], pr['number'])]['read_wade_ids']) == sorted(x['id'] for x in pr['wade'])
counts = collections.Counter(x['kind'] for p in corpus for x in p['wade'])
dates = [x['date'] for p in corpus for x in p['wade'] if x['date']]
manifest = {
    'reviewer': 'Wado-posi',
    'refresh_date': '2026-10-06',
    'assembled_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'search_queries': ['is:pr reviewed-by:Wado-posi', 'is:pr commenter:Wado-posi'],
    'search_totals': {'reviewed': 182, 'commented': 191},
    'search_incomplete_results': False,
    'unique_prs': len(corpus),
    'wade_authored_prs': sum(p['author'] == 'Wado-posi' for p in corpus),
    'other_authored_prs': sum(p['author'] != 'Wado-posi' for p in corpus),
    'record_counts': dict(counts),
    'total_records': sum(counts.values()),
    'text_bearing_records': sum(bool(x['body'].strip()) for p in corpus for x in p['wade']),
    'first_record_at': min(dates),
    'last_record_at': max(dates),
    'paginated_endpoint_collections': len(list((ROOT / 'raw').glob('*.json'))),
    'fetch_errors': json.loads((ROOT / 'fetch-errors.json').read_text()),
    'reading_ledger_all_record_ids_verified': True,
    'scope_limit': 'Accessible search results for Wado-posi at collection time; excludes deleted, inaccessible, unsubmitted, other-account, and later material.',
    'validation': {'skill_schema': 'passed', 'citation_membership': 'passed', 'local_reference_links': 'passed', 'ui_metadata': 'passed'},
}
for name in ['reviewed-search.json', 'commented-search.json', 'prs.json', 'corpus.json', 'fetch-errors.json', 'fetch_corpus.py']:
    shutil.copy2(ROOT / name, OUT / name)
for i in range(3):
    shutil.copy2(ROOT / f'analysis-{i}.md', OUT / f'analysis-{i}.md')
    shutil.copy2(ROOT / f'classification-{i}.json', OUT / f'classification-{i}.json')
shutil.copytree(ROOT / 'backup', OUT / 'previous-skill', dirs_exist_ok=True)
shutil.copytree(ROOT / 'staged', OUT / 'updated-skill', dirs_exist_ok=True)
for name in ['forward-test-cases.md', 'forward-test-result.md', 'forward-test-assessment.json']:
    if (ROOT / name).exists():
        shutil.copy2(ROOT / name, OUT / name)
if (ROOT / 'forward-test-assessment.json').exists():
    manifest['validation']['behavioral_review'] = json.loads((ROOT / 'forward-test-assessment.json').read_text())
with tarfile.open(OUT / 'raw-github-responses.tar.gz', 'w:gz') as archive:
    archive.add(ROOT / 'raw', arcname='raw')
(OUT / 'reading-ledger.json').write_text(json.dumps(ledger, indent=2))
manifest['updated_skill_sha256'] = {str(f.relative_to(ROOT / 'staged')): hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT / 'staged').rglob('*') if f.is_file()}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))

esc = html.escape
repo_rows = []
for repo in sorted({p['repo'] for p in corpus}, key=lambda r: (-sum(p['repo'] == r for p in corpus), r)):
    prs = [p for p in corpus if p['repo'] == repo]
    c = collections.Counter(x['kind'] for p in prs for x in p['wade'])
    repo_rows.append(f'<tr><th>{esc(repo)}</th><td>{len(prs)}</td><td>{sum(p["author"] != "Wado-posi" for p in prs)}</td><td>{c["reviews"]}</td><td>{c["inline"]}</td><td>{c["discussion"]}</td></tr>')
pr_rows = []
for pr in corpus:
    entry = lookup[(pr['repo'], pr['number'])]
    role = entry.get('evidence_role', entry.get('role', 'context reviewed'))
    if entry['approval_only']:
        role = 'approval only'
    record_links = ' '.join(f'<a href="{esc(x["url"])}">{esc(x["kind"])} {x["id"]}</a>' for x in pr['wade'])
    pr_rows.append(f'<tr><td><a href="{esc(pr["url"])}">{esc(pr["repo"])}#{pr["number"]}</a><br>{esc(pr["title"])}</td><td>{esc(pr["author"])}</td><td>{len(pr["wade"])}</td><td>{esc(role.replace("_", " "))}<br>{esc(entry["summary"])}<details><summary>Source records</summary><div class="records">{record_links}</div></details></td></tr>')

report = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wade review history · 2026-10-06</title>
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#182330;background:#f5f7fa}body{max-width:1150px;margin:0 auto;padding:32px 22px;line-height:1.55}h1{font-size:2rem;line-height:1.2}h2{font-size:1.25rem;margin-top:32px}p{max-width:920px}a{color:#00689f}section,figure{background:#fff;border:1px solid #d6dde5;border-radius:10px;padding:20px;margin:18px 0}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:10px;border-bottom:1px solid #dde3ea;text-align:left;vertical-align:top}thead{background:#edf2f7}svg{width:100%;height:auto;max-width:930px}.muted,figcaption{color:#475668}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.cards section{margin:0}li{margin-bottom:8px}.records{display:flex;flex-wrap:wrap;gap:8px;font-size:.8rem}.scroll{overflow:auto}input{font:inherit;padding:10px;width:min(94%,500px);border:1px solid #8b9aa9;border-radius:5px}summary{cursor:pointer}code{background:#edf2f7;padding:2px 4px}footer{font-size:.85rem;color:#475668;margin-top:25px}.kicker{font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;color:#475668}
</style>
<div class="kicker">Codex skill update · 6 October 2026</div>
<h1>Wade’s reviews cover runtime behavior as well as tests and claims</h1>
<p><strong>Short version:</strong> Examined 1,134 review and comment records across all 191 accessible PRs returned by the searches. The revised skill adds ownership, completion, geometry, performance, and instrumentation checks. It preserves later corrections and separates review findings from author replies.</p>
<p><a href="../evidence/wade-review-refresh-20261006/updated-skill/SKILL.md">Updated skill snapshot</a> · <a href="../evidence/wade-review-refresh-20261006/updated-skill/references/review-history.md">Source map</a> · <a href="../evidence/wade-review-refresh-20261006/manifest.json">Exact counts and validation</a></p>
<figure>
<svg viewBox="0 0 900 240" role="img" aria-labelledby="chart-title chart-desc">
<title id="chart-title">PR authorship in the collected history</title><desc id="chart-desc">115 PRs were authored by other people. 76 PRs were authored by Wade. Both groups were read; author replies are distinguished from review findings.</desc>
<text x="12" y="25" font-size="18" font-weight="600">All 191 PRs were read; attribution matters</text>
<g stroke="#dae1e8"><line x1="230" y1="48" x2="230" y2="178"/><line x1="430" y1="48" x2="430" y2="178"/><line x1="630" y1="48" x2="630" y2="178"/><line x1="830" y1="48" x2="830" y2="178"/></g>
<g font-size="15" fill="#182330"><text x="12" y="89">Other PR authors</text><text x="12" y="153">Wade as PR author</text></g>
<rect x="230" y="62" width="575" height="39" fill="#0072b2"/><rect x="230" y="126" width="380" height="39" fill="#d55e00"/>
<g font-size="16" font-weight="700" fill="white"><text x="737" y="88">115 PRs</text><text x="544" y="152">76 PRs</text></g>
<g font-size="13" fill="#475668"><text x="226" y="200">0</text><text x="421" y="200">40</text><text x="621" y="200">80</text><text x="811" y="200">120 PRs</text></g>
</svg>
<figcaption>Authorship alone does not establish comment role. The reading ledger also identifies contributor replies, assisted reviews, and approval-only discussions.</figcaption>
</figure>
<div class="cards">
<section><h2>Runtime and performance</h2><ul><li>Trace physical reads, buffer lifetime, and the exact completion object.</li><li>Check hardware bounds, padding, and alignment at the real consumer.</li><li>Count repeated work; require measurements before claiming a time cost.</li></ul><p><a href="https://github.com/positron-ai/tron/pull/4128#discussion_r3907183627">Batch work review</a> · <a href="https://github.com/positron-ai/tron/pull/2777#discussion_r3277240111">Lock ownership review</a></p></section>
<section><h2>Tests and instrumentation</h2><ul><li>Verify that fakes observe transfer arguments and tests use the changed production route.</li><li>Keep independent expected results and distinct failure observations.</li><li>Check every promised metric path and stable worker identity.</li></ul><p><a href="https://github.com/positron-ai/tron/pull/4128#discussion_r3960538177">Test boundary review</a> · <a href="https://github.com/positron-ai/tron/pull/4596#discussion_r4125033634">Missing timer path</a></p></section>
<section><h2>Corrections and severity</h2><ul><li>Read later replies before treating a suggestion as precedent.</li><li>Keep nits and approved follow-ups separate from defects.</li><li>Replace forced consolidation and inferred approval gates with evidence-based questions.</li></ul><p><a href="https://github.com/positron-ai/tron/pull/4557#issuecomment-6021333114">Later naming qualification</a> · <a href="https://github.com/positron-ai/tron/pull/2011#discussion_r2790148917">Retracted initialization advice</a></p></section>
</div>
<h2>Exact collection record</h2>
<p>600 submitted reviews, 509 inline comments, and 25 conversation comments. Of those 1,134 records, 549 have text and 585 have empty bodies. Counts describe records, not unique findings or theme frequency.</p>
<div class="scroll"><table><thead><tr><th>Repository</th><th>PRs</th><th>Other authors</th><th>Reviews</th><th>Inline</th><th>Conversation</th></tr></thead><tbody>REPO_ROWS</tbody></table></div>
<p class="muted">Searched <code>is:pr reviewed-by:Wado-posi</code> and <code>is:pr commenter:Wado-posi</code>. Both returned complete results. Downloaded all pages of 573 endpoint collections with no fetch errors. Record dates: 25 September 2025 through 6 October 2026.</p>
<h2>Validation</h2><p>Skill schema, local reference links, UI metadata, source citation membership, and complete reading-ledger coverage passed. Behavioral validation results are recorded in the <a href="../evidence/wade-review-refresh-20261006/manifest.json">manifest</a> and <a href="../evidence/wade-review-refresh-20261006/forward-test-result.md">scenario review</a>. The original PR workloads were not rerun.</p>
<h2>PR reading ledger</h2><p>Every collected record is retained. Source links open the original GitHub discussion.</p>
<label for="filter">Filter by repository, PR, or review topic</label><br><input id="filter" type="search" placeholder="For example: 4128, completion, or asim"><p id="count" class="muted">191 PRs shown</p>
<div class="scroll"><table id="ledger"><thead><tr><th>PR</th><th>PR author</th><th>Records</th><th>Reading summary and role</th></tr></thead><tbody>PR_ROWS</tbody></table></div>
<footer>Scope: accessible history for Wado-posi at collection time. Deleted or inaccessible material, unsubmitted reviews, other accounts, and later activity are outside this snapshot. <a href="../evidence/wade-review-refresh-20261006/raw-github-responses.tar.gz">Raw paginated responses</a> · <a href="../evidence/wade-review-refresh-20261006/reading-ledger.json">Machine-readable reading ledger</a> · <a href="../evidence/wade-review-refresh-20261006/previous-skill/SKILL.md">Previous skill snapshot</a></footer>
<script>document.querySelector('#filter').addEventListener('input',event=>{const q=event.target.value.toLowerCase();let count=0;for(const row of document.querySelectorAll('#ledger tbody tr')){row.hidden=!row.textContent.toLowerCase().includes(q);if(!row.hidden)count++;}document.querySelector('#count').textContent=count+' PRs shown';});</script>
</html>'''.replace('REPO_ROWS', ''.join(repo_rows)).replace('PR_ROWS', ''.join(pr_rows))
report_path = WORK / 'status/wade-review-history-20261006.html'
report_path.write_text(report)
print(json.dumps({'report': str(report_path), 'evidence': str(OUT), 'counts': manifest['record_counts'], 'ledger_verified': True}, indent=2))
