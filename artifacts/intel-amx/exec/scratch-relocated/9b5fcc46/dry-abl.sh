#!/usr/bin/env bash
# Dry run of abl-build.sh and abl-run.sh in a sandbox (real scripts, paths rewritten; stubbed build2.sh / nix / runtron / guards / git for the worktree).
set -u
S=${S:?}; RE=/home/jhan/workspace/intel-AMX/exec
rm -rf "$S"; mkdir -p "$S"/bin "$S"/exec/{i4934-20261015,i4525-20260922,sync4424-20261002,q4b-fpga-20260921,results/i4934-20261015,logs} "$S"/var/tmp/jhan/{tron-i4934,tron-pr4,tron-pr3,tron-main1010}/gen "$S"/dev/hugepages "$S"/repo
rw() { sed -e "s#/home/jhan/.nix-profile/bin/nix#$S/bin/nix#g" -e "s#/home/jhan/workspace/intel-AMX/exec#$S/exec#g" -e "s#/var/tmp/jhan#$S/var/tmp/jhan#g" -e "s#/dev/hugepages#$S/dev/hugepages#g" -e "s#REPO=/home/jhan/workspace/tron#REPO=$S/repo#" "$1" > "$2"; }
for f in abl-build.sh abl-run.sh campaign-fix.sh; do rw "$RE/i4934-20261015/$f" "$S/exec/i4934-20261015/$f"; done
cp "$RE/i4934-20261015/ablations.py" "$S/exec/i4934-20261015/"; cp "$RE/sync4424-20261002/summarize.py" "$S/exec/sync4424-20261002/"
cat > "$S/exec/lib-guard.sh" <<'EOG'
ci_lease_busy() { return 1; }
other_user_active() { return 1; }
rinzler_active() { return 1; }
campaign_guard_acquire() { return 0; }
campaign_guard_release() { return 0; }
rinzler_takeover_if_idle() { return 1; }
GUARD_TAKEOVER_LAST=${GUARD_TAKEOVER_LAST:-0}
EOG
printf '%s\n' '#!/usr/bin/env bash' 'echo "$(date -u +%FT%TZ) stub dut $*"; exit 0' > "$S/exec/q4b-fpga-20260921/dut.sh"
# the shared repo stub: a git repo holding the real fix tree's three files at COMMIT (so cat-file and the worktree checkout work)
git init -q "$S/repo"; for f in h/tron/models/self_attention.hpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp; do mkdir -p "$S/repo/$(dirname $f)"; cp /home/jhan/workspace/ai-runs/tron-i4934/$f "$S/repo/$f"; done
git -C "$S/repo" add -A >/dev/null; git -C "$S/repo" -c user.name=dry -c user.email=dry@x commit -q -m "dry commit"; COMMIT=$(git -C "$S/repo" rev-parse HEAD)
cat > "$S/exec/i4525-20260922/build2.sh" <<'EOB'
#!/usr/bin/env bash
set -u
mkdir -p "$RES"
[ -e "$WT/.git" ] || git -C "$SRC" worktree add --detach "$WT" "$COMMIT" || { echo "worktree add failed"; echo checkout-failed > "$RES/build-$SUFFIX.done"; exit 1; }
mkdir -p "$WT/gen"
printf '#!/usr/bin/env bash\necho "ingested-qwen-3-4b-instruct-2507-tp2 ingested-qwen-3-4b-instruct-2507-tp4"\n' > "$WT/gen/runtron"; chmod +x "$WT/gen/runtron"
cp "$WT/gen/runtron" "$WT/gen/runtron.$SUFFIX"
echo "cache: STUB $CONFIGURE_ARGS" > "$RES/build-$SUFFIX.txt"; echo ok > "$RES/build-$SUFFIX.done"; echo "$(date -u +%FT%TZ) stub build $SUFFIX ok"
EOB
printf '%s\n' '#!/usr/bin/env bash' 'echo "stub nix $*" >&2; cp gen/runtron gen/runtron.new 2>/dev/null; exit 0' > "$S/bin/nix"
cat > "$S/bin/runtron.stub" <<'EOR'
#!/usr/bin/env bash
[ "${1:-}" = --version ] && { echo "tron stub version"; exit 0; }
echo "Version: stub $0"; echo "Configured instance stub"; echo "App CPU list stub"; echo "HW attention: USE_HW_ATTN=${USE_HW_ATTN:-unset} TRON_AMX_DISABLE=${TRON_AMX_DISABLE:-unset}"
echo "Parsing the prompt took 1.000 s at 1000 tokens/s"; sleep 0.1; echo "average tok/s 10.00"; exit 0
EOR
printf '%s\n' '#!/usr/bin/env bash' '[ "${1:-}" = -n ] && shift' 'exec "$@"' > "$S/bin/sudo"
printf '%s\n' '#!/usr/bin/env bash' 'shift; for u in "$@"; do echo inactive; done' > "$S/bin/systemctl"
printf '%s\n' '#!/usr/bin/env bash' 'exit 1' > "$S/bin/prlimit"
chmod +x "$S"/bin/* "$S"/exec/*.sh "$S"/exec/*/*.sh
for b in tron-pr4/gen/runtron.pr4 tron-pr3/gen/runtron.pr3 tron-main1010/gen/runtron.main1010 tron-i4934/gen/runtron.fix; do cp "$S/bin/runtron.stub" "$S/var/tmp/jhan/$b"; chmod +x "$S/var/tmp/jhan/$b"; done
export OUR_CPUS=0-1 PATH="$S/bin:$PATH"
TOMORROW=$(date -u -d 'tomorrow 01:00' +%FT%TZ)
echo "== abl-build.sh dry run (probe.done absent for 3 s, then present)"
( sleep 3; echo "E=ok F=ok" > "$S/exec/results/i4934-20261015/probe.done" ) &
COMMIT=$COMMIT END_BY=$TOMORROW bash "$S/exec/i4934-20261015/abl-build.sh"; echo "abl-build rc=$?"
cut -c1-200 "$S/exec/logs/i4934-abl.log"; echo "abl.done: $(cat "$S/exec/results/i4934-abl/abl.done")"; ls "$S/var/tmp/jhan/tron-i4934abl/gen/"
echo "== worktree clean after the ablations? $(git -C "$S/var/tmp/jhan/tron-i4934abl" status --short | wc -l) files changed"
# the ablation binaries in the sandbox are stubs: replace them with the runtron stub so the run driver can execute them
for a in a1 a2; do cp "$S/bin/runtron.stub" "$S/var/tmp/jhan/tron-i4934abl/gen/runtron.$a"; done
echo "== abl-run.sh dry run (perf.done written after 2 s)"
( sleep 2; echo ok > "$S/exec/logs/i4934-perf.done"; echo ok > "$S/exec/logs/i4934-perf-fpga.done" ) &
REPS=1 END_BY=$TOMORROW bash "$S/exec/i4934-20261015/abl-run.sh"; echo "abl-run rc=$?"
cut -c1-160 "$S/exec/logs/i4934-abl-run.log"; echo "campaign done: $(cat "$S/exec/logs/i4934-abl-cpu.done")"; grep -c "^### runtron" "$S/exec/results/i4934-abl-cpu/rt-results.txt"; grep "arm=" "$S/exec/results/i4934-abl-cpu/rt-results.txt" | grep -o "arm=[a-z0-9]* armenv=\[[^]]*\]" | sort | uniq -c; head -3 "$S/exec/results/i4934-abl-cpu/summary.md" | cut -c1-200
