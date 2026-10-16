#!/usr/bin/env bash
# print every conflict hunk (with 8 lines of context) of the UU files in the worktree $1
W=$1
git -C "$W" status --porcelain | grep -v '^??'
for f in $(git -C "$W" diff --name-only --diff-filter=U); do
  echo "##### $f"
  grep -n '^<<<<<<<\|^=======\|^>>>>>>>' "$W/$f"
  awk '/^<<<<<<</{p=1; s=NR-8} p{print NR": "$0} /^>>>>>>>/{p=0; e=NR+6} !p && NR>=s && NR<=e {print NR": "$0}' "$W/$f"
done
