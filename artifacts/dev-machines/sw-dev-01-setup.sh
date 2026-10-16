# Per-host shell setup for sw-dev-01, sourced by jibin.bashrc.positron.dev.
# podman on sw-dev-01 must not use the shared ~/.config/containers/storage.conf
# (that one is alpha's, fuse-overlayfs at /usr/bin). claude-box exports the
# same variable itself; this makes plain podman commands work in shells.
export CONTAINERS_STORAGE_CONF="$HOME/.config/containers/storage-sw-dev-01.conf"

if [[ $- == *i* && -t 0 && ${_HERDR_LOGIN_PID:-} != "$$" ]] && shopt -q login_shell; then
    _HERDR_LOGIN_PID=$$
    read -r -p 'run claude-dev to start container and start herdr? Y/* ' _herdr_reply
    [[ $_herdr_reply == [yY] ]] && "$HOME/claude-container/claude-box" start && podman exec -it -e IS_SANDBOX=1 -w /home/jhan claude-dev bash -lic 'herdr --session "$(hostname)"; exec bash -l'
    unset _herdr_reply
fi
