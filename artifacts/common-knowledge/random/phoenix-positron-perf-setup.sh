#!/usr/bin/env bash
set -euo pipefail
umask 077

perf_account=positron-perf
perf_home=/home/positron-perf

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

(( EUID == 0 )) || fail 'Run this script with sudo on Phoenix.'
(( $# <= 1 )) || fail 'Usage: bash phoenix-positron-perf-setup.sh [Jeremy-public-key-file]'
if getent passwd "$perf_account" >/dev/null; then
    fail 'positron-perf already exists. Inspect it before changing its access.'
fi
if getent group "$perf_account" >/dev/null; then
    fail 'The positron-perf group already exists. Inspect it before proceeding.'
fi
[[ ! -e "$perf_home" && ! -L "$perf_home" ]] || fail "$perf_home already exists."

if (( $# == 1 )); then
    perf_key=$(cat -- "$1")
else
    IFS= read -r -p "Paste Jeremy's public SSH key, then press Enter: " perf_key
fi
perf_key=${perf_key%$'\r'}
[[ -n "$perf_key" && "$perf_key" != *$'\n'* ]] || fail 'Supply exactly one public key line.'
case "${perf_key%% *}" in
    ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com) ;;
    *) fail 'Expected an OpenSSH public key without authorized_keys options.' ;;
esac

perf_temp=$(mktemp -d)
trap 'rm -rf -- "$perf_temp"' EXIT
printf '%s\n' "$perf_key" > "$perf_temp/jeremy.pub"
ssh-keygen -l -E sha256 -f "$perf_temp/jeremy.pub" || fail 'The public key is invalid.'

# Check the existing server configuration without changing or restarting it.
/usr/sbin/sshd -T > "$perf_temp/sshd-config"
grep -qx 'pubkeyauthentication yes' "$perf_temp/sshd-config" || fail 'Public-key authentication is not enabled.'
grep -qx 'usepam yes' "$perf_temp/sshd-config" || fail 'Review locked-password login behavior with the administrator.'
awk '
    $1 == "authorizedkeysfile" {
        for (i = 2; i <= NF; i++) {
            if ($i == ".ssh/authorized_keys" || $i == "%h/.ssh/authorized_keys") {
                found = 1
            }
        }
    }
    END { exit !found }
' "$perf_temp/sshd-config" || fail 'The server uses a different authorized-keys location.'

useradd --create-home --user-group --home-dir "$perf_home" \
    --shell /bin/bash --comment 'SDK performance tests' "$perf_account"
printf 'Created %s. No SSH key has been installed yet.\n' "$perf_account"

perf_password_state=$(passwd -S "$perf_account")
[[ $(awk '{print $2}' <<< "$perf_password_state") == L ]] || fail 'The new account password is not locked.'
[[ $(id -Gn "$perf_account") == "$perf_account" ]] || fail 'Unexpected supplementary groups on the new account.'

if LC_ALL=C sudo -n -l -U "$perf_account" > "$perf_temp/sudo-policy" 2>&1; then
    cat "$perf_temp/sudo-policy"
    fail 'The new account has a sudo policy. No SSH key was installed; administrator review is needed.'
fi
if ! grep -Fq 'is not allowed to run sudo' "$perf_temp/sudo-policy"; then
    cat "$perf_temp/sudo-policy"
    fail 'Could not verify that sudo access is denied. No SSH key was installed.'
fi

chmod 750 "$perf_home"
install -d -o "$perf_account" -g "$perf_account" -m 700 "$perf_home/.ssh"
install -d -o "$perf_account" -g "$perf_account" -m 750 "$perf_home/work"
install -o "$perf_account" -g "$perf_account" -m 600 \
    "$perf_temp/jeremy.pub" "$perf_home/.ssh/authorized_keys"

printf '\nAccount setup completed.\n'
id "$perf_account"
passwd -S "$perf_account"
cat "$perf_temp/sudo-policy"
stat -c '%U:%G %a %n' "$perf_home" "$perf_home/.ssh" \
    "$perf_home/.ssh/authorized_keys" "$perf_home/work"
ssh-keygen -l -E sha256 -f "$perf_home/.ssh/authorized_keys"
printf '\nJeremy must verify: ssh positron-perf@192.168.2.45\n'
printf 'Work directory: %s/work\n' "$perf_home"
