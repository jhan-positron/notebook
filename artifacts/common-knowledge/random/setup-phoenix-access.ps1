#Requires -Version 5.1
# Run on the laptop. Initial setup requires arm SSH and sudo credentials.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$KeyPath = Join-Path $HOME '.ssh/id_ed25519'

if (-not (Test-Path -LiteralPath "$KeyPath.pub" -PathType Leaf)) {
    Write-Host "Missing $KeyPath.pub"
    Write-Host 'Generate a key, then rerun this script:'
    Write-Host '  ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519"'
    exit 1
}

try {
    & ssh-keygen -l -f "$KeyPath.pub" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'The public-key file is invalid.' }
    $PublicKey = (Get-Content -LiteralPath "$KeyPath.pub" -Raw).Trim()
    if ($PublicKey -notmatch '^ssh-ed25519[ \t]+([A-Za-z0-9+/]+={0,2})(?:[ \t]+[^\r\n]*)?$') {
        throw "Expected an Ed25519 public key in $KeyPath.pub"
    }
    $KeyData = $Matches[1]
    $Installer = @'
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
'@
    $Installer = $Installer.Replace("`r`n", "`n")
    $PayloadText = "key_data='$KeyData'`n$Installer`n"
    $Payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($PayloadText))
    $SshOptions = @('-o', 'ConnectTimeout=15', '-o', 'StrictHostKeyChecking=ask', '-o', 'ControlPath=none')

    Write-Host 'Installing the public key. Enter arm SSH/sudo credentials if prompted.'
    # sudo reads its password from the terminal. Only the installer uses the pipe.
    $RemoteCommand = "printf %s $Payload | base64 -d | sudo -H -u positron-perf bash"
    & ssh -t @SshOptions arm@192.168.2.45 $RemoteCommand
    if ($LASTEXITCODE -ne 0) { throw 'Public-key installation failed.' }

    Write-Host 'Verifying login with password prompts disabled...'
    & ssh @SshOptions -o BatchMode=yes -o IdentitiesOnly=yes -i $KeyPath positron-perf@192.168.2.45 'test $(id -un) = positron-perf && id'
    if ($LASTEXITCODE -ne 0) {
        throw 'Login verification failed. If your key has a passphrase, load it with: ssh-add "$HOME/.ssh/id_ed25519"'
    }
    Write-Host "`nSUCCESS: passwordless login verified. Connect with:"
    Write-Host '  ssh -i "$HOME/.ssh/id_ed25519" positron-perf@192.168.2.45'
}
catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
