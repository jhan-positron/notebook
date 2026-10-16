#!/usr/bin/env bash
# Dry run of perf-fix.sh in a sandbox: the real driver and campaign-fix.sh (paths rewritten), stubbed runtron / perf / sudo / guard / platformd / git.
set -u
S=${S:?}; RE=/home/jhan/workspace/intel-AMX/exec
rm -rf "$S"; mkdir -p "$S"/bin "$S"/exec/{i4934-20261015,sync4424-20261002,q4b-fpga-20260921,results,logs} "$S"/var/tmp/jhan/{tron-i4934,tron-pr4,tron-pr3,tron-main1010}/gen "$S"/dev/hugepages
rw() { sed -e "s#/home/jhan/workspace/intel-AMX/exec#$S/exec#g" -e "s#/var/tmp/jhan#$S/var/tmp/jhan#g" -e "s#/dev/hugepages#$S/dev/hugepages#g" "$1" > "$2"; }
for f in trace-head.sh campaign-fix.sh; do rw "$RE/i4934-20261015/$f" "$S/exec/i4934-20261015/$f"; done
cp "$RE/sync4424-20261002/summarize.py" "$S/exec/sync4424-20261002/"
cat > "$S/exec/lib-guard.sh" <<'EOG'
ci_lease_busy() { return 1; }
other_user_active() { return 1; }
rinzler_active() { return 1; }
campaign_guard_acquire() { echo "GUARD stub acquire"; return 0; }
campaign_guard_release() { return 0; }
rinzler_takeover_if_idle() { return 1; }
GUARD_TAKEOVER_LAST=${GUARD_TAKEOVER_LAST:-0}
EOG
printf '%s\n' '#!/usr/bin/env bash' 'echo "$(date -u +%FT%TZ) stub dut $*"; exit 0' > "$S/exec/q4b-fpga-20260921/dut.sh"
cat > "$S/bin/runtron.stub" <<'EOR'
#!/usr/bin/env bash
[ "${1:-}" = --version ] && { echo "tron stub version"; exit 0; }
echo "Version: stub $0"; echo "Configured instance stub"; echo "App CPU list stub"; echo "HW attention: USE_HW_ATTN=${USE_HW_ATTN:-unset} TRON_AMX_DISABLE=${TRON_AMX_DISABLE:-unset} args: $*"
tr=""; while [ $# -gt 0 ]; do [ "$1" = --trace-gen ] && tr=$2; shift; done
sleep 0.5; echo "Parsing the prompt took 1.000 s at 1000 tokens/s"; sleep 0.5; echo "average tok/s 10.00"; [ -n "$tr" ] && echo trace > "$tr"; exit 0
EOR
cat > "$S/bin/perf" <<'EOP'
#!/usr/bin/env bash
cmd=$1; shift; out=""
run_after_dashes() { while [ $# -gt 0 ]; do [ "$1" = -- ] && { shift; "$@"; return; }; shift; done; }
case $cmd in
  stat) echo "stub perf stat $*" >&2; run_after_dashes "$@"; printf '     1,000,000      cycles\n       500,000      instructions\n' >&2 ;;
  record) while [ $# -gt 0 ]; do [ "$1" = -o ] && out=$2; shift; done; run_after_dashes "$@"; echo "stub data" > "$out"; echo "[ perf record: Captured and wrote 1 MB $out ]" >&2 ;;
  report) echo "# stub report $*"; echo ""; echo "    40.00%  [.] tron::self_attention<...>::apply_page_range<geometry>(std::vector const&)"; echo "    10.00%  [.] k_vnni::qk_group<4ul>(...)"; echo "     5.00%  [k] native_sched_clock"; echo "     3.00%  [.] third_symbol"; echo "     2.00%  [.] fourth_symbol" ;;
  annotate) echo "stub annotate $*" ;;
  *) echo "stub perf: unknown $cmd" >&2; exit 1 ;;
esac
EOP
printf '%s\n' '#!/usr/bin/env bash' '[ "${1:-}" = -n ] && shift' 'exec "$@"' > "$S/bin/sudo"
printf '%s\n' '#!/usr/bin/env bash' 'shift; for u in "$@"; do echo inactive; done' > "$S/bin/systemctl"
printf '%s\n' '#!/usr/bin/env bash' 'echo stubtip' > "$S/bin/git"
printf '%s\n' '#!/usr/bin/env bash' 'exit 1' > "$S/bin/prlimit"
chmod +x "$S"/bin/* "$S"/exec/*.sh "$S"/exec/*/*.sh
for b in tron-pr4/gen/runtron.pr4 tron-pr3/gen/runtron.pr3 tron-main1010/gen/runtron.main1010 tron-i4934/gen/runtron.fix; do cp "$S/bin/runtron.stub" "$S/var/tmp/jhan/$b"; chmod +x "$S/var/tmp/jhan/$b"; done
export OUR_CPUS=0-1 PATH="$S/bin:$PATH"
TOMORROW=$(date -u -d 'tomorrow 01:30' +%FT%TZ)
echo "== perf-fix.sh dry run $(date -u +%T)"
touch "$S/exec/logs/pred.done"; WAIT_FOR="$S/exec/logs/pred.done" END_BY=$TOMORROW bash "$S/exec/i4934-20261015/trace-head.sh"; echo "perf-fix rc=$?"
echo "== log"; cut -c1-220 "$S/exec/logs/i4934-trace2.log"
echo "== done: $(cat "$S/exec/logs/i4934-trace2.done")"; echo "== results"; ls "$S/exec/results/i4934-trace2/" "$S/var/tmp/jhan/perf-i4934/"
echo "== one run log"; cat "$S/exec/results/i4934-trace2/q3-4b-tp2-8u-p1024__fixoff__rep1.log"; echo "== top"; cat "$S/exec/results/i4934-trace2/q3-4b-tp2-8u-p1024__fixoff__rep1.top.txt"; echo "== annotate-1"; cat "$S/exec/results/i4934-trace2/q3-4b-tp2-8u-p1024__fixoff__rep1.annotate-1.txt"; echo "== stat"; cat "$S/exec/results/i4934-trace2/q3-4b-tp2-8u-p1024__fixoff__rep1.stat.txt"
