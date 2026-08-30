# Per-host shell setup for sw-dev-01, sourced by jibin.bashrc.positron.dev.
# podman on sw-dev-01 must not use the shared ~/.config/containers/storage.conf
# (that one is alpha's, fuse-overlayfs at /usr/bin). claude-box exports the
# same variable itself; this makes plain podman commands work in shells.
export CONTAINERS_STORAGE_CONF="$HOME/.config/containers/storage-sw-dev-01.conf"
