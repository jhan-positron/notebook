#!/usr/bin/env bash
# vnnik5-20260916: reproduce the CI lint job's clang-format check for the C++ files a
# commit changes relative to origin/main, without touching any worktree: the file
# content is read from the shared repository (git show) and piped through clang-format-19
# of the project's nix shell with the project's .clang-format. Usage (on delphi-3bda):
# format-check.sh <commit>
set -u
COMMIT=$1
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-vnnik5
NIX=/home/jhan/.nix-profile/bin/nix
cd "$WT" || exit 1
FILES=$(git -C "$REPO" diff --name-only origin/main "$COMMIT" -- 'h/*' 'src/*' 't/*' | grep -E '\.(hpp|cpp|h|i)$')
echo "files: $(echo "$FILES" | wc -l)"
"$NIX" develop --command bash -c '
  clang-format-19 --version
  bad=0
  for f in '"$(echo $FILES | tr '\n' ' ')"'; do
    if ! git -C '"$REPO"' show '"$COMMIT"':$f > /tmp/cf_in.$$ 2>/dev/null; then echo "MISSING $f"; bad=$((bad+1)); continue; fi
    clang-format-19 --style=file:'"$WT"'/.clang-format --assume-filename=$f < /tmp/cf_in.$$ > /tmp/cf_out.$$
    if cmp -s /tmp/cf_in.$$ /tmp/cf_out.$$; then echo "OK   $f"; else echo "DIFF $f"; diff /tmp/cf_in.$$ /tmp/cf_out.$$ | head -12; bad=$((bad+1)); fi
  done
  rm -f /tmp/cf_in.$$ /tmp/cf_out.$$
  echo "format check: $bad file(s) differ from clang-format-19"'
