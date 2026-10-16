import datetime
import json
import pathlib
import subprocess
import time

state_dir = pathlib.Path('/tmp/tron-pr1-review-state-20261010')
state_dir.mkdir(exist_ok=True)
command = [
    'gh', 'pr', 'list', '--repo', 'positron-ai/tron',
    '--author', 'jhan-positron', '--head', 'jhan-vnnik-1-layout',
    '--state', 'all', '--limit', '20', '--json',
    'number,title,url,isDraft,headRefName,baseRefName,headRefOid,state,createdAt,updatedAt',
]
while True:
    checked_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=40)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        matches = json.loads(result.stdout)
        state = {'checked_at': checked_at, 'matches': matches}
        (state_dir / 'monitor.json').write_text(json.dumps(state, indent=2) + '\n')
        if matches:
            print(json.dumps({'event': 'found', **state}), flush=True)
            break
        print(json.dumps({'event': 'waiting', 'checked_at': checked_at}), flush=True)
    except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as error:
        state = {'checked_at': checked_at, 'error': str(error)}
        (state_dir / 'monitor.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps({'event': 'error', **state}), flush=True)
    time.sleep(55)
