"""Install shared skill links without changing any CODEX_HOME assignment."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

stage = Path(__file__).resolve().parent
shared = Path('/home/jhan/.codex/skills')
active = Path('/home/jhan/codex-home-claude-agentsrv')
helper = Path('/home/jhan/.local/bin/codex-share-skills')
startup = Path('/home/jhan/home/jibin.bashrc.positron')
homes = [Path(item) for item in json.loads((stage / 'homes.json').read_text())]
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

expected = (stage / 'startup-expected-sha256').read_text().strip()
if hashlib.sha256(startup.read_bytes()).hexdigest() != expected:
    raise SystemExit('Startup file changed since review; refusing to overwrite it.')
if helper.exists() or helper.is_symlink():
    raise SystemExit('Helper path already exists: ' + str(helper))
if shared.is_symlink() or not shared.is_dir():
    raise SystemExit('Expected a real shared skills directory.')

def command(home, apply=False):
    args = ['python3', str(stage / 'share-skills.py'), '--codex-home', str(home),
            '--shared', str(shared)]
    if apply:
        args.append('--apply')
    return args

# Inspect every existing source before changing any directory.
for home in homes:
    subprocess.run(command(home), check=True)

def install_file(source, destination, mode):
    fd, temporary = tempfile.mkstemp(prefix='.' + destination.name + '-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(source.read_bytes())
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), mode)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

install_file(stage / 'share-skills.py', helper, 0o755)

# Keep one complete built-in version, not a mixture from different hosts.
# Retain the previous shared version and every per-host original as backups.
system_backup = shared.parent / ('skills.system.backup-' + stamp)
if system_backup.exists():
    raise SystemExit('System-skill backup already exists: ' + str(system_backup))
with tempfile.TemporaryDirectory(prefix='.skills-system-', dir=shared.parent) as directory:
    candidate = Path(directory) / '.system'
    shutil.copytree(active / 'skills/.system', candidate, symlinks=True)
    (shared / '.system').rename(system_backup)
    try:
        candidate.rename(shared / '.system')
    except OSError:
        system_backup.rename(shared / '.system')
        raise
print('Preserved previous built-in skills:', system_backup)

for home in homes:
    subprocess.run(command(home, apply=True), check=True)
    if (home / 'skills').resolve() != shared:
        raise SystemExit('Shared link verification failed: ' + str(home))

if hashlib.sha256(startup.read_bytes()).hexdigest() != expected:
    raise SystemExit('Startup file changed during migration; shared links are ready but automatic setup was not installed.')
startup_backup = startup.with_name(startup.name + '.bak-shared-skills-' + stamp)
shutil.copy2(startup, startup_backup)
install_file(stage / 'jibin.bashrc.positron.proposed', startup, stat.S_IMODE(startup.stat().st_mode))
print('Startup backup:', startup_backup)
print('Shared custom skills:', ', '.join(sorted(item.name for item in shared.iterdir() if not item.name.startswith('.'))))
print('CODEX_HOME assignments and container mounts were not changed.')
