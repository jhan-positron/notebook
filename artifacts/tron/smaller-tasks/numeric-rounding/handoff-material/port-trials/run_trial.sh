#!/usr/bin/env bash
# Usage: run_trial.sh <trial-name> <base-commit> <commit> [<commit> ...]
# Runs "git cherry-pick" of each commit in turn on a fresh branch trial/<name>
# in the scratch clone. Stops at the first cherry-pick that fails, records the
# state, copies the conflicted files, then aborts the cherry-pick.
set -u
S=/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/port-trials
T="$S/tron-trial"
export GIT_LFS_SKIP_SMUDGE=1
name=$1; base=$2; shift 2
out="$S/results/$name"
rm -rf "$out"; mkdir -p "$out"
g() { git -C "$T" -c core.hooksPath=/dev/null "$@"; }

{
  echo "### trial $name  base=$base  commits=$*"
  # clean start
  g cherry-pick --abort >/dev/null 2>&1
  g reset -q --hard >/dev/null 2>&1
  echo "\$ git checkout -q -f -B trial/$name $base"
  g checkout -q -f -B "trial/$name" "$base"; echo "exit=$?"
  g clean -fdxq
  echo "HEAD=$(g rev-parse --short=10 HEAD)  status-lines=$(g status --porcelain | wc -l)"
  for c in "$@"; do
    echo
    echo "\$ git cherry-pick $c"
    g cherry-pick "$c" > "$out/cherry-pick-$c.log" 2>&1
    rc=$?
    echo "exit=$rc"
    sed 's/^/    | /' "$out/cherry-pick-$c.log"
    if [ $rc -ne 0 ]; then
      echo
      echo "\$ git status --porcelain"
      g status --porcelain | tee "$out/status-$c.txt" | sed 's/^/    /'
      echo
      echo "conflict regions per file (count of lines starting with '<<<<<<<'):"
      g status --porcelain | grep -E '^(UU|AA|DU|UD|AU|UA|DD) ' | while read -r code path; do
        if [ -f "$T/$path" ]; then
          n=$(grep -c '^<<<<<<<' "$T/$path")
          mkdir -p "$out/conflicted/$(dirname "$path")"
          cp "$T/$path" "$out/conflicted/$path"
        else
          n="(file absent in work tree)"
        fi
        echo "    $code $path : $n"
      done
      echo
      # optional: keep copies of auto-merged files named in $EXTRA
      for path in ${EXTRA:-}; do
        if [ -f "$T/$path" ]; then
          mkdir -p "$out/automerged/$(dirname "$path")"
          cp "$T/$path" "$out/automerged/$path"
          echo "    kept auto-merged copy: $path"
        fi
      done
      echo "\$ git status (long form, unmerged section)"
      g status | sed -n '/Unmerged paths/,/^$/p' | sed 's/^/    /'
      echo "\$ git cherry-pick --abort"
      g cherry-pick --abort; echo "exit=$?"
      echo "STOPPED at $c"
      break
    else
      echo "applied: HEAD=$(g rev-parse --short=10 HEAD)  status-lines=$(g status --porcelain | wc -l)"
    fi
  done
  echo "final HEAD of trial/$name = $(g rev-parse --short=10 HEAD)"
} 2>&1 | tee "$out/log.txt"
