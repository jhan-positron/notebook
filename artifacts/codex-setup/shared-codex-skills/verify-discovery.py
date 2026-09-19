"""Check skill discovery through a linked skills root in an isolated test home."""
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time

shared = Path('/home/jhan/.codex/skills')
expected = {'cpp-coding-guide', 'plain-english', 'goal'}
with tempfile.TemporaryDirectory(prefix='codex-shared-skills-check-') as directory:
    test_home = Path(directory)
    (test_home / 'skills').symlink_to(shared, target_is_directory=True)
    env = os.environ.copy()
    env['CODEX_HOME'] = str(test_home)
    process = subprocess.Popen(['codex', 'app-server', '--stdio'], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    messages = queue.Queue()
    def read_output():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                pass
    threading.Thread(target=read_output, daemon=True).start()
    def send(message):
        process.stdin.write(json.dumps(message) + '\n')
        process.stdin.flush()
    def response(identifier):
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            message = messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if message.get('id') == identifier:
                if 'error' in message:
                    raise RuntimeError('App-server request failed: ' + str(message['error'].get('message')))
                return message['result']
        raise RuntimeError('Timed out waiting for the local app server')
    try:
        send({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'shared-skills-check', 'version': '1.0'},
            'capabilities': {'experimentalApi': True}}})
        response(1)
        send({'method': 'initialized'})
        send({'id': 2, 'method': 'skills/list', 'params': {
            'cwds': ['/home/jhan/workspace/random'], 'forceReload': True}})
        result = response(2)
        found = {}
        errors = []
        for group in result.get('data', []):
            errors.extend(group.get('errors', []))
            for skill in group.get('skills', []):
                if skill.get('name') in expected:
                    found[skill['name']] = Path(skill['path']).resolve()
        if set(found) != expected:
            raise RuntimeError('Missing shared skills: ' + ', '.join(sorted(expected - set(found))))
        for name, path in sorted(found.items()):
            if path != shared / name / 'SKILL.md':
                raise RuntimeError('Skill resolved outside the shared directory: ' + name)
            print('Codex discovered:', name, '->', path)
        if errors:
            raise RuntimeError('Codex reported skill loading errors: ' + str(len(errors)))
        print('No skill loading errors. The actual CODEX_HOME configuration was not changed.')
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
