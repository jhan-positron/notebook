from pathlib import Path
import base64
import json
import os
import shlex
import stat
import subprocess
import tempfile

repo=Path('/home/jhan/workspace/random')
pwsh=Path('/tmp/phoenix-script-tools/pwsh/pwsh')
root=Path(tempfile.mkdtemp(prefix='cases-',dir='/tmp/phoenix-access-tests'))
mockbin=root/'bin'
mockbin.mkdir()
ssh=mockbin/'ssh'
ssh.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
log=Path(os.environ['PHOENIX_TEST_LOG'])
with log.open('a') as f: f.write(json.dumps(args)+'\\n')
mode=os.environ.get('PHOENIX_TEST_MODE','install')
if 'arm@192.168.2.45' in args:
 if mode=='admin-fails': sys.exit(42)
 Path(os.environ['PHOENIX_TEST_MARKER']).touch()
 sys.exit(0)
if any(a.endswith('@sw-dev-01') for a in args): sys.exit(0)
if mode=='already': sys.exit(0)
if 'BatchMode=yes' in args:
 sys.exit(0 if Path(os.environ['PHOENIX_TEST_MARKER']).exists() and mode!='verify-fails' else 255)
sys.exit(255)
''')
ssh.chmod(0o755)
idmock=mockbin/'id'
idmock.write_text('#!/bin/sh\nif [ "$1" = -un ]; then echo positron-perf; else /usr/bin/id "$@"; fi\n')
idmock.chmod(0o755)
baseenv=os.environ.copy()
baseenv['PATH']=str(mockbin)+os.pathsep+baseenv['PATH']
clients=[('bash', ['bash'], 'setup-phoenix-access.sh', 'key_path="$HOME/.ssh/id_ed25519"', 'key_path="$PHOENIX_TEST_KEY_PATH"'),
 ('powershell', [str(pwsh),'-NoLogo','-NoProfile','-File'], 'setup-phoenix-access.ps1', "$KeyPath = Join-Path $HOME '.ssh/id_ed25519'", '$KeyPath = $env:PHOENIX_TEST_KEY_PATH')]
payloads={}
passed=0

def run(args,env,expected=0):
 r=subprocess.run(args,env=env,text=True,capture_output=True,timeout=30)
 if (r.returncode==0)!=(expected==0):
  raise AssertionError(f'{args}: unexpected exit {r.returncode}\n{r.stdout}\n{r.stderr}')
 return r

for name,prefix,filename,key_assignment,test_assignment in clients:
 case=root/name
 case.mkdir()
 key=case/"keys with spaces and ' quote"/'id_ed25519'
 env=baseenv|{'PHOENIX_TEST_LOG':str(case/'calls.jsonl'),'PHOENIX_TEST_MARKER':str(case/'installed'), 'PHOENIX_TEST_KEY_PATH':str(key)}
 source=(repo/filename).read_text()
 assert source.count(key_assignment)==1
 assert 'sw-dev-01' not in source and 'PublicKeyOnly' not in source and 'public-key-only' not in source
 # Only the key path changes in the test copy. HOME remains unchanged.
 fixture=case/filename
 fixture.write_text(source.replace(key_assignment,test_assignment))
 cmd=prefix+[str(fixture)]
 missing=run(cmd,env,1)
 assert 'ssh-keygen -t ed25519' in missing.stdout
 assert not key.exists() and not key.parent.exists()
 assert not (case/'calls.jsonl').exists()
 passed+=1
 key.parent.mkdir()
 subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
 private=key.read_bytes()
 publicfile=key.with_name(key.name+'.pub')
 public=publicfile.read_bytes()
 for mode in ('install','admin-fails','verify-fails'):
  (case/'calls.jsonl').unlink(missing_ok=True)
  (case/'installed').unlink(missing_ok=True)
  result=run(cmd,env|{'PHOENIX_TEST_MODE':mode},0 if mode=='install' else 1)
  calls=[json.loads(line) for line in (case/'calls.jsonl').read_text().splitlines()]
  admins=[c for c in calls if 'arm@192.168.2.45' in c]
  assert len(admins)==1
  if mode=='install':
   assert 'SUCCESS: passwordless login verified.' in result.stdout
   assert 'BatchMode=yes' in calls[-1] and 'IdentitiesOnly=yes' in calls[-1]
   assert 'ControlPath=none' in calls[-1]
   remote=admins[0][-1]
   assert remote.endswith('| base64 -d | sudo -H -u positron-perf bash')
   payloads[name]=base64.b64decode(shlex.split(remote)[2]).decode()
   assert 'PRIVATE KEY' not in payloads[name]
  else:
   assert 'SUCCESS:' not in result.stdout
  if mode=='admin-fails': assert len(calls)==1
  assert key.read_bytes()==private and publicfile.read_bytes()==public
  passed+=1
 for suffix in (b'',b'\r\n'):
  publicfile.write_bytes(public.rstrip()+suffix)
  run(cmd,env)
  assert publicfile.read_bytes()==public.rstrip()+suffix
  passed+=1
 (case/'calls.jsonl').unlink()
 publicfile.write_text('not a valid SSH public key\n')
 run(cmd,env,1)
 assert not (case/'calls.jsonl').exists()
 assert key.read_bytes()==private
 passed+=1

# Both clients must send the same installer, apart from the generated public key.
assert payloads['bash'].split('\n',1)[1] == payloads['powershell'].split('\n',1)[1]
passed+=1
body=payloads['bash']
keydata=body.split("'",2)[1]
for scenario in ('new','preserve','restricted','symlink'):
 remotehome=root/('remote-'+scenario)
 remotehome.mkdir()
 fixture=remotehome/'.ssh'
 if scenario=='symlink':
  outside=root/'outside'
  outside.mkdir()
  sentinel=outside/'authorized_keys'
  sentinel.write_text('do not touch\n')
  fixture.symlink_to(outside,target_is_directory=True)
 else:
  fixture.mkdir(mode=0o755)
  if scenario=='preserve': (fixture/'authorized_keys').write_text('# other keys\nssh-ed25519 AAAA other-key-without-final-newline')
  if scenario=='restricted': (fixture/'authorized_keys').write_text(f'from="192.0.2.1",no-port-forwarding ssh-ed25519 {keydata} existing-comment\n')
 target=fixture/'authorized_keys'
 before=target.read_bytes() if target.exists() else b''
 installer=body.replace('cd /home/positron-perf','cd '+shlex.quote(str(remotehome)))
 script=root/(scenario+'.sh')
 script.write_text(installer)
 r=run(['bash',str(script)],baseenv,1 if scenario=='symlink' else 0)
 if scenario=='symlink':
  assert sentinel.read_bytes()==before
 else:
  after=target.read_bytes()
  assert after.startswith(before)
  assert after.decode().count(keydata)==1
  assert stat.S_IMODE(fixture.stat().st_mode)==0o700
  assert stat.S_IMODE(target.stat().st_mode)==0o600
  run(['bash',str(script)],baseenv)
  assert target.read_bytes()==after
 passed+=1
print(f'PASS: {passed} checks for Bash/PowerShell clients and shared installer.')
print('Checks used real ssh-keygen, simulated SSH responses, and temporary authorized_keys files.')
print('PowerShell ran on Linux. Native Windows execution and actual laptop-to-Phoenix access were not exercised.')
print('Test artifacts:',root)
