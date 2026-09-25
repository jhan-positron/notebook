#!/bin/bash
# Light syntax check of the rebased tip on delphi-3bda while the CI lease is busy:
# five translation units, -fsyntax-only, pinned to 2 CPUs of our half, nice 19.
cd /var/tmp/jhan/tron-issue4525 || exit 2
python3 - <<'PY' > /var/tmp/jhan/tron-issue4525-rebase-syntax.cmds
import json, shlex
cc = json.load(open("gen/compile_commands.json"))
want = ["src/tron/kernels/amx_attn.cpp", "t/t_amx_dispatch_dtype.cpp",
        "t/t_amx_numerics.cpp", "t/heterogeneous_scheduler_compile.cpp",
        "t/t_llama_unit.cpp"]
for w in want:
    for e in cc:
        if e["file"].endswith("/" + w):
            args = shlex.split(e["command"])
            out = []; skip = False
            for a in args:
                if skip: skip = False; continue
                if a in ("-o", "-MT", "-MF"): skip = True; continue
                if a in ("-c", "-MD"): continue
                out.append(a)
            out.append("-fsyntax-only")
            print(shlex.join(out))
PY
echo "commands: $(wc -l < /var/tmp/jhan/tron-issue4525-rebase-syntax.cmds)"
rc_all=0
while IFS= read -r cmd; do
  f=$(echo "$cmd" | grep -o '[^ ]*\.cpp' | tail -1)
  echo "=== $(date -u +%T) syntax-check $f"
  s=$(date +%s)
  taskset -c 140,141 nice -n 19 bash -c "$cmd"; rc=$?
  echo "=== rc=$rc  $(( $(date +%s) - s )) s  $f"
  [ "$rc" -ne 0 ] && rc_all=1
done < /var/tmp/jhan/tron-issue4525-rebase-syntax.cmds
echo "=== $(date -u +%T) clang-format check"
FILES="h/tron/kernels/amx_attn_iface.hpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp h/tron/models/self_attention.hpp h/tron/scheduler/full.hpp h/tron/tensor/kv_cache_fwd.hpp h/tron/tensor/v_vnni.hpp src/tron/kernels/amx_attn.cpp t/heterogeneous_scheduler_compile.cpp t/t_amx_dispatch_dtype.cpp t/t_amx_numerics.cpp t/t_llama_unit.cpp"
taskset -c 140,141 nice -n 19 clang-format-19 --dry-run -Werror $FILES; fmt=$?
echo "=== clang-format rc=$fmt"
echo "=== $(date -u +%T) lint-notes"
taskset -c 140,141 nice -n 19 make lint-notes > /var/tmp/jhan/tron-issue4525-rebase-lintnotes.log 2>&1; ln=$?
echo "=== lint-notes rc=$ln (log /var/tmp/jhan/tron-issue4525-rebase-lintnotes.log)"
[ "$fmt" -ne 0 ] && rc_all=1
[ "$ln" -ne 0 ] && rc_all=1
echo "ALL rc=$rc_all $(date -u +%T)"
