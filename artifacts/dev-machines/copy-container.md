# Fix Codex `codex_apps` and bubblewrap startup warnings

This guide addresses these two messages on Linux or WSL2:

```text
MCP startup interrupted. The following servers were not initialized: codex_apps

Codex could not find bubblewrap on PATH. Install bubblewrap with your OS
package manager. Codex will use the bundled bubblewrap in the meantime.
```

They normally describe separate problems:

- The bubblewrap warning concerns the local command sandbox. It is non-fatal because Codex can fall back to a bundled helper.
- The `codex_apps` warning means the managed MCP server for plugins and connectors did not initialize. This can prevent services such as Slack or Notion from being available.

## 1. Install bubblewrap

### Ubuntu or Debian

```bash
sudo apt update
sudo apt install bubblewrap
```

### Fedora

```bash
sudo dnf install bubblewrap
```

Verify that the executable is available:

```bash
command -v bwrap
bwrap --version
```

If `command -v bwrap` prints nothing, check that `/usr/bin` is on `PATH`:

```bash
printf '%s\n' "$PATH"
ls -l /usr/bin/bwrap
```

Restart Codex after installation.

Official reference: [Codex sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing#prerequisites)

## 2. Update Codex and run diagnostics

```bash
codex --version
codex update
codex doctor --all
codex login status
```

Focus on failures under authentication, reachability, DNS, HTTP, WebSocket, and plugins. A WebSocket warning by itself may still allow an HTTPS fallback, but an HTTP reachability failure must be fixed.

## 3. Eliminate mixed authentication as a test

The apps system expects a ChatGPT login. If the shell also exports `OPENAI_API_KEY`, launch Codex once without that variable:

```bash
env -u OPENAI_API_KEY codex
```

If `codex_apps` starts this way, only export `OPENAI_API_KEY` in shells that need API-key authentication. Do not delete a needed key from another application.

If the ChatGPT login is missing or expired, authenticate again:

```bash
codex logout
codex login
codex login status
```

## 4. Check network access

If `codex doctor --all` reports DNS, HTTP, or WebSocket failures:

1. Retry without a VPN or restrictive proxy.
2. Confirm that DNS works for `chatgpt.com` and `api.openai.com`.
3. Check whether a firewall, corporate gateway, or custom certificate authority blocks HTTPS or WebSockets.
4. Restart Codex after changing the network configuration.

Useful reachability checks:

```bash
getent hosts chatgpt.com
getent hosts api.openai.com
curl -I https://chatgpt.com
curl -I https://api.openai.com/v1/models
```

An HTTP `401 Unauthorized` response from the final command still proves that DNS, TLS, and HTTP connectivity are working; it only means that request did not include valid API authentication.

## 5. Install and connect Slack or Notion

Fixing `codex_apps` makes plugin tools possible, but it does not install or authorize individual services.

Inside Codex, open the plugin browser:

```text
/plugins
```

Install the Slack or Notion plugin, complete its account authorization, and then start a new Codex session. The connector can access only the workspaces, channels, pages, and actions granted during authorization.

Official reference: [Using plugins in Codex](https://learn.chatgpt.com/docs/plugins)

## 6. Confirm the result

Restart Codex and verify that neither startup warning returns. Then run:

```bash
codex doctor --all
codex plugin list
```

Expected results:

- `command -v bwrap` returns an executable path.
- Sandbox diagnostics no longer report missing bubblewrap.
- `codex_apps` initializes without an MCP startup warning.
- The desired Slack or Notion plugin is installed and connected.

## If the problem persists

Save a redacted diagnostic report:

```bash
codex doctor --json > codex-doctor.json
```

Review the report before sharing it, especially for paths, account details, proxy configuration, or other sensitive information. Include the Codex version, operating system, exact startup warning, and whether the problem reproduces with:

```bash
env -u OPENAI_API_KEY codex
```
