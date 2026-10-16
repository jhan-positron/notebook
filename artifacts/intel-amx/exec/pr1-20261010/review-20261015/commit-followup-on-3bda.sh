#!/bin/bash
# Commit the 2026-10-15 review-thread edits of PR-1 over ssh on delphi-3bda, where the pre-commit hook's lefthook exists.
# usage: bash commit-on-3bda.sh   (stages exactly the 12 edited files, commits with msg-followup.txt, prints the new head)
set -e
W=/home/jhan/workspace/ai-runs/tron-split-pr1
MSG=/home/jhan/workspace/intel-AMX/exec/pr1-20261010/review-20261015/msg-followup.txt
FILES="h/tron/kernels/k_vnni.hpp h/tron/models/self_attention.hpp h/tron/scheduler/full.hpp"
echo "before: $(git -C $W rev-parse --short HEAD), changed files: $(git -C $W status --porcelain | wc -l)"
ssh -o BatchMode=yes delphi-3bda "cd $W && git add -- $FILES && git commit -q -F $MSG && git rev-parse HEAD && git status --porcelain | wc -l" 2>&1 | grep -v '^$' | tail -3
echo "after: $(git -C $W rev-parse --short HEAD)"
git -C $W log -1 --format='%H %s'
