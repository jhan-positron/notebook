#!/bin/bash
# Status line converted from ~/.bashrc PS1 (color_prompt branch):
#   PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
# \u@\h -> user@host (green), \w -> current dir (blue), trailing \$ dropped.

input=$(cat)
cwd=$(printf '%s' "$input" | jq -r '.workspace.current_dir')
cwd="${cwd/#$HOME/\~}"

user=$(whoami)
host=$(hostname -s)

chroot=""
if [ -n "${debian_chroot:-}" ]; then
    chroot="(${debian_chroot}) "
elif [ -r /etc/debian_chroot ]; then
    chroot="($(cat /etc/debian_chroot)) "
fi

model=$(printf '%s' "$input" | jq -r '.model.display_name // empty')
model_id=$(printf '%s' "$input" | jq -r '.model.id // empty')

effort=$(printf '%s' "$input" | jq -r '.effort.level // empty')
if [ -z "$effort" ] && [ -r "$HOME/.claude/settings.json" ]; then
    effort=$(jq -r --arg id "$model_id" '(.modelSettings[$id].effortLevel // .effortLevel) // empty' "$HOME/.claude/settings.json" 2>/dev/null)
fi

used=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')

printf '%s\033[01;32m%s@%s\033[00m:\033[01;34m%s\033[00m' "$chroot" "$user" "$host" "$cwd"
[ -n "$model" ] && printf ' \033[01;35m%s\033[00m' "$model"
[ -n "$effort" ] && printf ' \033[01;33meffort:%s\033[00m' "$effort"
[ -n "$used" ] && printf ' \033[01;36mctx:%.0f%%\033[00m' "$used"
# A hidden item above must not turn into a failed exit code of the script.
exit 0
