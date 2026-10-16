#!/bin/bash
# Commit the 2026-10-15 review-thread edits of PR-2 (#4887) over ssh on delphi-3bda, where the pre-commit hook's
# lefthook exists. usage: bash commit-on-3bda.sh   (stages exactly the 9 edited files, commits with msg.txt, prints the head)
set -e
W=/home/jhan/workspace/ai-runs/tron-split-pr2
MSG=/home/jhan/workspace/intel-AMX/exec/pr2-20261011/review-20261015/msg.txt
FILES="h/tron/kernels/amx_attn_iface.hpp h/tron/kernels/k_vnni.hpp h/tron/models/kv_cache.hpp h/tron/models/self_attention.hpp h/tron/tensor/k_vnni.hpp src/tron/kernels/amx_attn.cpp t/t_amx_dispatch_dtype.cpp t/t_amx_numerics.cpp t/t_llama_unit.cpp"
echo "before: $(git -C $W rev-parse --short HEAD), changed files: $(git -C $W status --porcelain | wc -l)"
ssh -o BatchMode=yes delphi-3bda "cd $W && git add -- $FILES && git commit -q -F $MSG && git rev-parse HEAD && git status --porcelain | wc -l" 2>&1 | grep -v '^$' | tail -3
echo "after: $(git -C $W rev-parse --short HEAD)"
git -C $W log -1 --format='%H %s'
