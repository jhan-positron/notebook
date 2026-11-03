#Requires -Version 5.1
# Run on Jeremy's laptop after Jibin authorizes its public key on Phoenix.
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
    # Trust a previously unknown host key. Reject a changed host key.
    $SshOptions = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none',
        '-o', 'IdentitiesOnly=yes', '-i', $KeyPath)
    & ssh @SshOptions positron-perf@192.168.2.45 'test $(id -un) = positron-perf && id'
    if ($LASTEXITCODE -ne 0) {
        throw 'Login failed. Check the SSH error above. Jibin must first authorize this laptop''s public key on Phoenix. If your private key has a passphrase, load it with: ssh-add "$HOME/.ssh/id_ed25519"'
    }
    Write-Host "`nSUCCESS: passwordless login verified. Connect with:"
    Write-Host '  ssh positron-perf@192.168.2.45'
}
catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
