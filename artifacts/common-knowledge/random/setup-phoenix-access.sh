#!/usr/bin/env bash
# Run on the laptop. Initial setup requires arm SSH and sudo credentials.
set -euo pipefail

key_path="$HOME/.ssh/id_ed25519"
if [[ ! -f "$key_path.pub" ]]; then
    printf 'Missing %s.pub\nGenerate a key, then rerun this script:\n' "$key_path"
    printf '  ssh-keygen -t ed25519 -f %q\n' "$key_path"
    exit 1
fi

ssh-keygen -l -f "$key_path.pub" >/dev/null
read -r key_type key_data _ <<< "$(cat "$key_path.pub")"
if [[ "$key_type" != ssh-ed25519 || ! "$key_data" =~ ^[A-Za-z0-9+/]+={0,2}$ ]]; then
    printf 'Expected an Ed25519 public key in %s.pub\n' "$key_path" >&2
    exit 1
fi

installer=$(cat <<'REMOTE_INSTALLER'
set -euo pipefail
umask 077
cd /home/positron-perf
[[ ! -L .ssh && ! -L .ssh/authorized_keys ]] || { echo 'SSH path is a symbolic link.' >&2; exit 1; }
mkdir -p .ssh
chmod 700 .ssh
if [[ ! -e .ssh/authorized_keys ]]; then
    (set -o noclobber; : > .ssh/authorized_keys)
fi
[[ -f .ssh/authorized_keys ]] || { echo 'authorized_keys is not a regular file.' >&2; exit 1; }
chmod 600 .ssh/authorized_keys
# Preserve existing keys and any restrictions attached to a matching key.
if ! awk -v key="$key_data" '{ for (i=1; i<=NF; i++) if ($i == key) found=1 } END { exit !found }' .ssh/authorized_keys; then
    printf '\nssh-ed25519 %s positron-perf@phoenix\n' "$key_data" >> .ssh/authorized_keys
fi
REMOTE_INSTALLER
)
payload=$(printf "key_data='%s'\n%s\n" "$key_data" "$installer" | base64 | tr -d '\r\n')
ssh_options=(-o ConnectTimeout=15 -o StrictHostKeyChecking=ask -o ControlPath=none)

printf 'Installing the public key. Enter arm SSH/sudo credentials if prompted.\n'
# sudo reads its password from the terminal. Only the installer uses the pipe.
ssh -t "${ssh_options[@]}" arm@192.168.2.45 \
    "printf %s $payload | base64 -d | sudo -H -u positron-perf bash"

printf 'Verifying login with password prompts disabled...\n'
if ! ssh "${ssh_options[@]}" -o BatchMode=yes -o IdentitiesOnly=yes -i "$key_path" \
    positron-perf@192.168.2.45 'test "$(id -un)" = positron-perf && id'; then
    printf 'Login verification failed. If your key has a passphrase, load it first:\n' >&2
    printf '  ssh-add %q\n' "$key_path" >&2
    exit 1
fi
printf '\nSUCCESS: passwordless login verified. Connect with:\n'
printf '  ssh -i %q positron-perf@192.168.2.45\n' "$key_path"
