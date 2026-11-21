from pathlib import Path
import hashlib
import json

root = Path('/home/jhan/workspace/titan/cache-perf/asimov')
state = Path('/tmp/codex-hop-latency-review/monitor.json')
old = json.loads(state.read_text()) if state.exists() else {}
new = {}
for name in ['measure-hop-latency.md', 'codex-review-measure-hop-latency.md']:
    path = root / name
    data = path.read_bytes() if path.exists() else None
    new[name] = hashlib.sha256(data).hexdigest() if data is not None else None
    if new[name] != old.get(name):
        print('CHANGED', name)
        print(data.decode() if data is not None else 'MISSING')
    else:
        print(name, 'missing' if data is None else 'unchanged')
state.write_text(json.dumps(new))
