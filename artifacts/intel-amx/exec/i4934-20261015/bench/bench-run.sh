#!/bin/bash
# bench-run.sh: run tail_bench (the tail-row score micro-benchmark) on delphi-3bda.
#   1. wait until the nightly CI releases its lease (poll every 5 min, up to 10 h),
#   2. compile exec/i4934-20261015/bench/tail_bench.cpp inside `nix develop` of the fix tree
#      /var/tmp/jhan/tron-i4934 (b87d20dd81) with the flags of t_k_vnni_layout.cpp,
#   3. pick the two idlest first-hyperthread cores of our half (socket 1, cpus 72-143) whose
#      siblings are idle too, run the benchmark twice (run1, run2) pinned to them,
#   4. write $RES/bench.done (ok | <reason>).
# Env overrides (for a dry run): RES WT NIX SRC DRY=1 (stop before the compile).
set -u
EXEC=${EXEC:-/home/jhan/workspace/intel-AMX/exec}
RES=${RES:-$EXEC/results/i4934-tailbench}
WT=${WT:-/var/tmp/jhan/tron-i4934}
NIX=${NIX:-/home/jhan/.nix-profile/bin/nix}
SRC=${SRC:-$EXEC/i4934-20261015/bench/tail_bench.cpp}
COMMIT=b87d20dd81d5d7b562e5b9eea6656de7a6c6df84
mkdir -p "$RES"
LOG=$RES/run.log
exec >>"$LOG" 2>&1
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
done_with() { echo "$1" >"$RES/bench.done"; echo "$(ts) done: $1"; exit "${2:-1}"; }
echo "=== $(ts) bench-run start pid $$ on $(hostname)"
rm -f "$RES/bench.done"

wait_for_ci_release 36000 || done_with lease-timeout
echo "$(ts) CI lease free"
# another person on the machine: wait up to 1 h, then give up
deadline=$(( $(date +%s) + 3600 ))
while other_user_active; do
  [ "$(date +%s)" -ge "$deadline" ] && done_with other-user-busy
  sleep 120
done
echo "$(ts) no other user active"
[ "${DRY:-0}" = 1 ] && done_with dry-run-stop 0

head=$(git -C "$WT" rev-parse HEAD)
[ "$head" = "$COMMIT" ] || done_with "tree-not-at-commit:$head"

# The compiler and flags of t_k_vnni_layout.cpp (same AMX/VNNI defines, -O3, -march flags),
# without -o, -c and the source file.
read -r CXX FLAGS < <(python3 - <<'PY'
import json, shlex, sys
cc = json.load(open('/var/tmp/jhan/tron-i4934/gen/compile_commands.json'))
for e in cc:
    if e['file'].endswith('t/t_k_vnni_layout.cpp'):
        a = shlex.split(e['command']) if 'command' in e else e['arguments']
        out, skip = [], False
        for x in a[1:]:
            if skip:
                skip = False
                continue
            if x == '-o':
                skip = True
                continue
            if x == '-c' or x.endswith('t_k_vnni_layout.cpp'):
                continue
            out.append(x)
        print(a[0], ' '.join(shlex.quote(x) for x in out))
        break
else:
    sys.exit(1)
PY
) || done_with no-compile-command
echo "$(ts) compiler $CXX"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c 72-143 "$NIX" develop --command bash -c \
    "$CXX $FLAGS -Wno-unused-function -o '$RES/tail_bench' '$SRC' -lpthread -lgcc_s" ) || done_with compile-failed
echo "$(ts) compiled in $(( $(date +%s) - t0 )) s: $(sha256sum "$RES/tail_bench" | cut -c1-16)"

# Two idle first-hyperthread cores of socket 1 (siblings are cpu+144), from two /proc/stat samples 2 s apart.
pick_cores() {
  python3 - <<'PY'
import time
def snap():
    d = {}
    for line in open('/proc/stat'):
        if line.startswith('cpu') and line[3].isdigit():
            f = line.split()
            d[int(f[0][3:])] = (int(f[4]) + int(f[5]), sum(int(x) for x in f[1:]))
    return d
a = snap(); time.sleep(2); b = snap()
def idle(c):
    i0, t0 = a[c]; i1, t1 = b[c]
    return (i1 - i0) / max(1, t1 - t0)
cands = [c for c in range(72, 144) if idle(c) > 0.98 and idle(c + 144) > 0.98]
if len(cands) < 2:
    cands = sorted(range(72, 144), key=lambda c: -(idle(c) + idle(c + 144)))
# two cores far apart in the list, so a shared L2 pair is unlikely
print(cands[0], cands[len(cands) // 2])
PY
}
read -r RCPU WCPU < <(pick_cores) || done_with no-cores
echo "$(ts) reader cpu $RCPU writer cpu $WCPU (siblings $((RCPU + 144)) $((WCPU + 144)))"
for run in run1 run2; do
  t0=$(date +%s)
  "$RES/tail_bench" "$RCPU" "$WCPU" >"$RES/tail_bench-$run.csv" 2>"$RES/tail_bench-$run.err"
  rc=$?
  echo "$(ts) $run rc=$rc in $(( $(date +%s) - t0 )) s, $(wc -l <"$RES/tail_bench-$run.csv") lines"
  [ $rc -eq 0 ] || done_with "run-failed:$run:$rc"
done
uptime >>"$LOG"
done_with ok 0
