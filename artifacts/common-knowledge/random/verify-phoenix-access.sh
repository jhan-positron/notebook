#!/usr/bin/env bash
# Run on Jeremy's laptop after Jibin authorizes its public key on Phoenix.
set -euo pipefail

key_path="$HOME/.ssh/id_ed25519"
if [[ ! -f "$key_path.pub" ]]; then
    printf 'Missing %s.pub\nGenerate a key, then rerun this script:\n' "$key_path"
    printf '  ssh-keygen -t ed25519 -f %q\n' "$key_path"
    exit 1
fi

# Trust a previously unknown host key. Reject a changed host key.
if ! ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes \
    -o ConnectTimeout=15 -o ControlPath=none -o IdentitiesOnly=yes \
    -i "$key_path" positron-perf@192.168.2.45 \
    'test "$(id -un)" = positron-perf && id'; then
    printf 'Login failed. Check the SSH error above.\n' >&2
    printf '%s\n' "Jibin must first authorize this laptop's public key on Phoenix." >&2
    printf 'If your private key has a passphrase, load it with: ssh-add %q\n' "$key_path" >&2
    exit 1
fi

printf '\nSUCCESS: passwordless login verified. Connect with:\n'
printf '  ssh positron-perf@192.168.2.45\n'
