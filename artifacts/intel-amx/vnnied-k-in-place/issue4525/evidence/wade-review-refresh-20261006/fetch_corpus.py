import concurrent.futures
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path('/tmp/wade-review-refresh')
PRS = json.loads((ROOT / 'prs.json').read_text())
(ROOT / 'raw').mkdir(exist_ok=True)

def fetch(job):
    pr, kind = job
    stem = pr['repo'].replace('/', '__') + '__' + str(pr['number'])
    dest = ROOT / 'raw' / (stem + '__' + kind + '.json')
    if dest.exists():
        return 'cached', dest.name
    endpoint = ('issues' if kind == 'discussion' else 'pulls')
    tail = 'reviews' if kind == 'reviews' else 'comments'
    url = f"repos/{pr['repo']}/{endpoint}/{pr['number']}/{tail}?per_page=100"
    for attempt in range(3):
        run = subprocess.run(['gh', 'api', url, '--paginate', '--slurp'], capture_output=True, text=True)
        if run.returncode == 0:
            pages = json.loads(run.stdout)
            if not all(isinstance(p, list) for p in pages):
                raise ValueError(f'Unexpected response: {url}')
            dest.write_text(json.dumps([x for p in pages for x in p], indent=2))
            return 'fetched', dest.name
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
    return 'error', {'endpoint': url, 'stderr': run.stderr}

jobs = [(pr, kind) for pr in PRS for kind in ('reviews', 'inline', 'discussion')]
errors = []
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for i, (state, detail) in enumerate(pool.map(fetch, jobs), 1):
        if state == 'error':
            errors.append(detail)
        if i % 60 == 0 or i == len(jobs):
            print(f'{i}/{len(jobs)} endpoints complete, {len(errors)} errors', flush=True)
(ROOT / 'fetch-errors.json').write_text(json.dumps(errors, indent=2))
if errors:
    raise SystemExit(1)
