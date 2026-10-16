#!/usr/bin/env bash
# Dry run of the i4934 driver chain in a sandbox: real scripts (paths rewritten), stubbed runtron / build / guard / platformd.
set -u
S=${S:?}; RE=/home/jhan/workspace/intel-AMX/exec
rm -rf "$S"; mkdir -p "$S"/bin "$S"/exec/{i4934-20261015,pr4-20261012,sync4424-20261002,i4525-20260922,q4b-fpga-20260921,results,logs} "$S"/var/tmp/jhan/{tron-i4934,tron-pr4,tron-pr3,tron-main1010}/gen "$S"/dev/hugepages
rw() { sed -e "s#/home/jhan/.nix-profile/bin/nix#$S/bin/nix#g" -e "s#/home/jhan/workspace/intel-AMX/exec#$S/exec#g" -e "s#/var/tmp/jhan#$S/var/tmp/jhan#g" -e "s#/dev/hugepages#$S/dev/hugepages#g" "$1" > "$2"; }
for f in probe-fix.sh campaign-fix.sh smoke-fix.sh identity-fix.sh mutate-fix.sh chain-fix.sh; do rw "$RE/i4934-20261015/$f" "$S/exec/i4934-20261015/$f"; done
rw "$RE/pr4-20261012/chain-finish.sh" "$S/exec/pr4-20261012/chain-finish.sh"
cp "$RE/i4934-20261015/mutations.py" "$S/exec/i4934-20261015/"; cp "$RE/pr4-20261012/validate-smoke.py" "$S/exec/pr4-20261012/"; cp "$RE/sync4424-20261002/summarize.py" "$S/exec/sync4424-20261002/"
cat > "$S/exec/lib-guard.sh" <<'EOF'
ci_lease_busy() { return 1; }
other_user_active() { return 1; }
rinzler_active() { return 1; }
campaign_guard_acquire() { return 0; }
campaign_guard_release() { return 0; }
rinzler_takeover_if_idle() { return 1; }
GUARD_TAKEOVER_LAST=${GUARD_TAKEOVER_LAST:-0}
EOF
printf '%s\n' '#!/usr/bin/env bash' 'echo "$(date -u +%FT%TZ) stub bill-share $*"; exit 0' > "$S/exec/bill-share.sh"
printf '%s\n' '#!/usr/bin/env bash' 'echo "$(date -u +%FT%TZ) stub dut $*"; exit 0' > "$S/exec/q4b-fpga-20260921/dut.sh"
cat > "$S/exec/i4525-20260922/build2.sh" <<'EOF'
#!/usr/bin/env bash
set -u
mkdir -p "$RES" "$WT/gen"
case " $TARGETS " in *" runtron "*) cp "$STUB_RUNTRON" "$WT/gen/runtron.$SUFFIX"; chmod +x "$WT/gen/runtron.$SUFFIX";; esac
if [ ! -e "$WT/.git" ]; then git init -q "$WT"; echo gen/ > "$WT/.gitignore"; for f in h/tron/models/self_attention.hpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp; do mkdir -p "$WT/$(dirname $f)"; cp "$REAL_WT/$f" "$WT/$f"; done; git -C "$WT" -c user.email=dry@x -c user.name=dry add -A; git -C "$WT" -c user.email=dry@x -c user.name=dry commit -qm base; fi
for t in $TARGETS; do case $t in runtron) ;; *) cp "$STUB_TEST" "$WT/gen/$t"; chmod +x "$WT/gen/$t";; esac; done
echo "cache: STUB $CONFIGURE_ARGS" > "$RES/build-$SUFFIX.txt"
: > "$RES/tests-$SUFFIX.txt"; for t in $TESTS; do echo "$t rc=0 tip=$COMMIT env=[${TEST_ENV:-}] stub" >> "$RES/tests-$SUFFIX.txt"; done
echo ok > "$RES/build-$SUFFIX.done"; echo "$(date -u +%FT%TZ) stub build $SUFFIX ok"
EOF
cat > "$S/bin/runtron.stub" <<'EOF'
#!/usr/bin/env bash
# stub runtron: ingested-qwen-3-4b-instruct-2507-tp2 ingested-qwen-3-4b-instruct-2507-tp4
[ "${1:-}" = --version ] && { echo "tron stub version"; exit 0; }
out=""; n=16; tr=""
while [ $# -gt 0 ]; do case $1 in --output-token-file) out=$2; shift;; -l) n=$2; shift;; --trace-gen) tr=$2; shift;; esac; shift; done
echo "Version: stub"; echo "Configured instance stub"; echo "App CPU list stub"; echo "HW attention: USE_HW_ATTN=${USE_HW_ATTN:-unset} TRON_AMX_DISABLE=${TRON_AMX_DISABLE:-unset}"
echo "Parsing the prompt took 1.000 s"; sleep 0.2; echo "average tok/s 10.00"
[ -n "$out" ] && seq -s ' ' 1 "$n" > "$out"
[ -n "$tr" ] && echo trace > "$tr"
exit 0
EOF
printf '%s\n' '#!/usr/bin/env bash' 'shift; for u in "$@"; do echo inactive; done' > "$S/bin/systemctl"
cat > "$S/bin/test.stub" <<'EOF'
#!/usr/bin/env bash
if [ "${DRY_CAUGHT:-1}" = 1 ]; then echo "-----"; echo "the software loop scores row-major rows with the dotter and VNNI blocks with"; echo "the reader"; echo "page K blocks turn VNNI at the 16th saved row and back when a row is"; echo "  the forward end converts a queue of many blocks on the pool"; echo "FAILED:"; echo "test cases: 3 | 2 passed | 1 failed"; exit 1; fi
echo "All tests passed (1 assertions in 1 test cases)"; exit 0
EOF
printf '%s\n' '#!/usr/bin/env bash' 'echo "stub nix $*" >&2; exit 0' > "$S/bin/nix"
printf '%s\n' '#!/usr/bin/env bash' 'exit 1' > "$S/bin/sudo"
chmod +x "$S"/bin/* "$S"/exec/*.sh "$S"/exec/*/*.sh
for b in tron-pr4/gen/runtron.pr4 tron-pr3/gen/runtron.pr3 tron-main1010/gen/runtron.main1010; do cp "$S/bin/runtron.stub" "$S/var/tmp/jhan/$b"; chmod +x "$S/var/tmp/jhan/$b"; done
export OUR_CPUS=0-1 PATH="$S/bin:$PATH" STUB_RUNTRON="$S/bin/runtron.stub" STUB_TEST="$S/bin/test.stub" REAL_WT=/home/jhan/workspace/ai-runs/tron-i4934
COMMIT=$(git -C /home/jhan/workspace/ai-runs/tron-i4934 rev-parse HEAD)
TOMORROW=$(date -u -d 'tomorrow 01:00' +%FT%TZ)
echo "== mutate-fix.sh with DRY_CAUGHT=1 (caught expected) $(date -u +%T)"
DRY_CAUGHT=1 COMMIT=$COMMIT END_BY=$TOMORROW bash "$S/exec/i4934-20261015/mutate-fix.sh"; echo "mutate rc=$?"
cut -c1-250 "$S/exec/results/i4934-mutate/steps.txt"; printf 'mutate.done: '; cat "$S/exec/results/i4934-mutate/mutate.done"
echo "== mutate log"; cut -c1-200 "$S/exec/logs/i4934-mutate.log"
echo "== mut tree clean?"; git -C "$S/var/tmp/jhan/tron-i4934mut" status --short | wc -l; grep -c MUTATION "$S"/var/tmp/jhan/tron-i4934mut/h/tron/models/*.hpp
rm -f "$S/exec/results/i4934-mutate/steps.txt"
echo "== mutate-fix.sh with DRY_CAUGHT=0 (not caught expected)"
DRY_CAUGHT=0 COMMIT=$COMMIT END_BY=$TOMORROW bash "$S/exec/i4934-20261015/mutate-fix.sh"; echo "mutate rc=$?"
cut -c1-250 "$S/exec/results/i4934-mutate/steps.txt"; printf 'mutate.done: '; cat "$S/exec/results/i4934-mutate/mutate.done"
echo "== errors in logs"; grep -nE 'unbound|command not found|No such file|syntax error|Traceback' "$S"/exec/logs/*.log | cut -c1-200 | head; echo "(end of error scan)"
exit 0
echo "== steps.txt"; cat "$S/exec/results/i4934-20261015/steps.txt" | cut -c1-200
echo "== done files"; for f in probe.done ourhalf.done otherbuilds.done; do printf '%s: ' $f; cat "$S/exec/results/i4934-20261015/$f" 2>/dev/null || echo MISSING; done
for f in i4934-E-cpu.done i4934-E-fpga.done; do printf '%s: ' $f; cat "$S/exec/logs/$f" 2>/dev/null || echo MISSING; done
echo "== identity"; cat "$S/exec/results/i4934-identity/steps.txt" | cut -c1-250; printf 'identity.done: '; cat "$S/exec/results/i4934-identity/identity.done" 2>/dev/null || echo MISSING
echo "== errors in logs"; grep -nE 'unbound|command not found|No such file|syntax error|Traceback' "$S"/exec/logs/*.log | cut -c1-200 | head -20; echo "(end of error scan)"
echo "== probe log"; cut -c1-170 "$S/exec/logs/i4934-20261015-probe.log"
echo "== E-cpu log tail"; tail -5 "$S/exec/logs/i4934-E-cpu.log" | cut -c1-170
echo "== rt-results head"; head -12 "$S/exec/results/i4934-E-cpu/rt-results.txt" | cut -c1-170; grep -c '^### runtron' "$S/exec/results/i4934-E-cpu/rt-results.txt" "$S/exec/results/i4934-E-fpga/rt-results.txt"
echo "== summary.md head"; head -8 "$S/exec/results/i4934-E-cpu/summary.md"; cat "$S/exec/results/i4934-E-cpu/summary.err" | head -3
