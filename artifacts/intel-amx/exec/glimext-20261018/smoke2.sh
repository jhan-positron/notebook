#!/usr/bin/env bash
# glimext-20261018 smoke2 = smoke.sh plus --dont-stop (review finding: a greedy one-user run that emits the stop token before
# token LEN writes a shorter row, which the verdict counts as incomplete). New file name: smoke.sh ran under the first chain.
# glimext-20261018 token-identity smoke (runs ON delphi-3bda, our half, called by chain2.sh step I once per cell): one user,
# temperature 0, --pay-for-determinism, seed 1, PROMPT prompt tokens, LEN generated tokens, the tokens written with
# --output-token-file; then the token rows of the arms are compared. Fork of exec/i4934-20261015/smoke-fix.sh; the
# functions (guards, placement, watcher, cleanup) come from this folder's campaign.sh (CAMPAIGN_FUNCTIONS_ONLY=1).
# Arms: base = the PR #5015 merge-base binary, head = the PR head binary, head2 = head run a second time (the A/A control),
# headoff = head with TRON_AMX_DISABLE=1 (the kill switch). Pairs compared: head:head2, head:base, headoff:base, headoff:head.
# MUST_MATCH ("a:b ..." pairs) names the pairs that make the verdict; the other pairs are informational (issue #4444:
# an AMX arm against an AVX arm is allowed to differ at a near tie).
# Usage: KEY=<cell key> MODEL=<runtron model> TP=2|4 ATTN=cpu|fpga PROMPT=<n> [LEN=256] [SMOKE_ARMS="base head head2 headoff"]
#        [MUST_MATCH="head:head2 head:base"] [RT_BASE=...] [RT_HEAD=...] bash smoke.sh
# Outputs: exec/results/glimext-20261018/smoke/<KEY>/{<arm>.tokens,<arm>.log,smoke.txt,smoke.done}.
# Never edit this file while a copy of it runs on 3bda (NFS trap); fixes go into a new file name.
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=${NAME:-glimext-20261018}
KEY=${KEY:?KEY (cell key, used as the output folder name) is required}
MODEL=${MODEL:?MODEL (runtron -m name) is required}
TP=${TP:?TP (2 or 4) is required}
ATTN=${ATTN:?ATTN (cpu or fpga) is required}
PROMPT=${PROMPT:?PROMPT (prompt length in tokens) is required}
LEN=${LEN:-256}
SMOKE_ARMS=${SMOKE_ARMS:-"base head head2 headoff"}
MUST_MATCH=${MUST_MATCH:-"head:head2"}
CAMPAIGN_FUNCTIONS_ONLY=1; source "$EXEC/glimext-20261018/campaign.sh"   # returns after the function definitions
unset CAMPAIGN_FUNCTIONS_ONLY
SM=$RES/smoke/$KEY; mkdir -p "$SM"
exec >>"$LOG" 2>&1
rm -f "$SM/smoke.done"
echo "=== $NAME smoke $KEY started $(ts) pid $$ arms=[$SMOKE_ARMS] must_match=[$MUST_MATCH] model=$MODEL tp=$TP prompt=$PROMPT len=$LEN attn=$ATTN ==="
TIP_BASE=$(git -C "$(wt_of "$RT_BASE")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_HEAD=$(git -C "$(wt_of "$RT_HEAD")" rev-parse --short HEAD 2>/dev/null || echo "?")
case $ATTN in cpu) hwenv="USE_HW_ATTN=0" ;; fpga) hwenv="-u USE_HW_ATTN" ;; *) echo "$(ts) ATTN '$ATTN' is not cpu or fpga"; echo "SMOKE-VERDICT bad-attn" >"$SM/smoke.done"; exit 1 ;; esac
NEED_HUGEPAGES=$([ "$TP" = 4 ] && echo 256 || echo 128)
placement "$TP" >/dev/null || { echo "$(ts) TP $TP has no placement"; echo "SMOKE-VERDICT bad-tp" >"$SM/smoke.done"; exit 1; }
trap 'stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null' EXIT
for arm in $SMOKE_ARMS; do
  base_arm=${arm%2}; bin=$(arm_bin "$base_arm") || { echo "$(ts) unknown smoke arm $arm"; echo "SMOKE-FAILED arm=$arm: unknown arm" >>"$SM/smoke.txt"; continue; }
  envv=$(arm_env "$base_arm"); envv=${envv//TRON_ATTN_STATS=1/}   # the exit report is not needed here; the kill switch of headoff stays
  out=$SM/$arm; stops=0; wt=$(wt_of "$bin")
  [ -x "$bin" ] || { echo "SMOKE-FAILED arm=$arm: $bin missing" >>"$SM/smoke.txt"; continue; }
  while :; do
    [ -s "$out.tokens" ] && { echo "$(ts) smoke $arm already done"; break; }
    wait_clear || { echo "$(ts) deadline while waiting"; echo "SMOKE-FAILED arm=$arm: deadline" >>"$SM/smoke.txt"; break; }
    take_guard || { echo "$(ts) deadline while waiting for the guard"; echo "SMOKE-FAILED arm=$arm: deadline (guard)" >>"$SM/smoke.txt"; break; }
    status "smoke $KEY $arm"
    echo "### smoke key=$KEY arm=$arm bin=$bin env=[${envv}] tip=$(arm_tip "$base_arm") model=$MODEL tp=$TP attn=$ATTN prompt=$PROMPT len=$LEN users=1 temperature=0 pay-for-determinism seed=1 $(ts) $(machine_line)" >>"$SM/smoke.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$wt" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv $envv TRON_LOG_LEVEL=info \
        timeout -k 30 1500 "$bin" stream-generate-text -m "$MODEL" $(placement "$TP") --hugepage_file "$HPFILE" -o \
        --prompt-length "$PROMPT" -l "$LEN" -u 1 --dont-stop --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    echo "smoke $arm rc=$rc $(grep -E 'Version:|HW attention|average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-300)" >>"$SM/smoke.txt"
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
      echo "SMOKE-STOPPED arm=$arm rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)" >>"$SM/smoke.txt"
      rm -f "$out.tokens"; stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "SMOKE-GIVEN-UP arm=$arm" >>"$SM/smoke.txt"; break; }
      sleep 120; continue
    fi
    [ $rc -eq 0 ] && [ -s "$out.tokens" ] || echo "SMOKE-FAILED arm=$arm rc=$rc (see $out.log)" >>"$SM/smoke.txt"
    break
  done
done
python3 - "$SM" "$SMOKE_ARMS" "$MUST_MATCH" "$LEN" <<'PY' >>"$SM/smoke.txt" 2>&1
import os, re, sys
d, arms, n_want = sys.argv[1], sys.argv[2].split(), int(sys.argv[4])
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if os.path.exists(p):
        lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
        if lines: rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
pairs = [("head", "head2"), ("head", "base"), ("headoff", "base"), ("headoff", "head")]
MUST_MATCH = {tuple(p.split(":")) for p in sys.argv[3].split() if ":" in p}
print("must-match pairs:", sorted(MUST_MATCH))
verdict = "ok"
wanted = [p for p in pairs if p[0] in arms and p[1] in arms]
for a in arms:   # every asked arm must have a full row (the pair check below only looks at the common prefix)
    if a not in rows: print(f"{a}: no token row"); verdict = "incomplete"
    elif len(rows[a]) != n_want: print(f"{a}: {len(rows[a])} tokens, expected {n_want}"); verdict = "incomplete"
for a, b in wanted:
    if a not in rows or b not in rows:
        print(f"{a} vs {b}: missing"); verdict = "incomplete" if verdict == "ok" else verdict; continue
    ra, rb = rows[a], rows[b]; n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    tag = "must match" if (a, b) in MUST_MATCH else "informational"
    if first is None: print(f"{a} vs {b}: identical for {n} tokens (lengths {len(ra)} / {len(rb)}) [{tag}]")
    else:
        ndiff = sum(1 for i in range(n) if ra[i] != rb[i])
        print(f"{a} vs {b}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens; {ndiff} of {n} positions differ [{tag}]")
        if (a, b) in MUST_MATCH and verdict == "ok": verdict = "differs"
print("SMOKE-VERDICT", verdict if (wanted and len(rows) >= 2) else "incomplete")
PY
tail -9 "$SM/smoke.txt"
last=$(grep -o 'SMOKE-VERDICT.*' "$SM/smoke.txt" | tail -1)   # the LAST verdict line only (smoke.txt is appended to across reruns)
[ "$last" = "SMOKE-VERDICT ok" ] && echo ok >"$SM/smoke.done" || echo "${last:-SMOKE-VERDICT missing}" >"$SM/smoke.done"
echo "=== $NAME smoke $KEY finished $(ts): $(cat "$SM/smoke.done") ==="
