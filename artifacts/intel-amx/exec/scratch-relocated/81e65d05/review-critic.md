# Completeness review: exec/attnstats-20261002

Short version. The confirmed list covers the chain/campaign control flow well. It missed four launch-day or report defects that I rate should-fix: a stale FUSE mount after a SIGKILLed runtron breaks every later run of that instance; the HW attention line is cut at 240 then 200 characters, so the gpt-oss card-layer count (`hw_slots: 18`) never reaches the report; section 7 prints nothing for a finished run without an exit report and trusts the cell's attention field; and a resume ignores a pinned COMMIT. The rest of my additions are nits.

Words used here: chain = exec/attnstats-20261002/chain.sh; campaign = campaign.sh in the same folder; the lease = /run/lock/systems-test-ci.lease (nightly CI); FUSE leaves = the per-model stats files runtron mounts under `<worktree>/stats/instance-N/`; exit report = the `[attn-stats]` lines tron prints to stderr at process end; hw_slots = the number of attention layers the FPGA card serves; CF-n = confirmed finding n in the list given to me.

What I checked (read-only): all five target files, the five parents, `bash -n` on the three scripts (ok), `gen_compare.py` on both sample result folders (rc 0, 201 and 106 lines, no stderr), tron `origin/main` = 9c88327931 (CMakePresets.json has `native`, no `cross-avx512`; `TRON_AMX_DISPATCH` option exists; `shape_ok` = head 128 and kv_mul 4 at amx_attn_iface.hpp:148-150; `configure_hw_attention` enables slots only for operations without a sliding window at model.hpp:1552-1560), and prior gpt-oss runs on our half (wedperf-20260916: FPGA attention worked, `hw_slots: 18`, head 64, gqa 8; CPU attention prompt 8192 x 8 users parsed in 92 s at tp2).

## Missed

1. **campaign.sh:206-215 (should-fix). A SIGKILLed runtron leaves its FUSE mount; the next run at the same `--instance` fails, and failures cascade.** tron's own doc: "If a runtron ... crashes before it can unmount, the FUSE mount at its per-instance subpath persists. The next invocation at the same subpath will collide and fail" [README.stats.md:205-208 at origin/main]. KILL happens in three places: `timeout -k 60` (line 207), the watcher after the main shell dies (line 110), `finish aborted` (line 173). A TERM-stopped run recovers (q4b-rt8u-20260922 attempt 2 ran after a WATCH-STOP), so the hole is the KILL path only. After one KILL every later run of that instance (tp2 = instance-2, tp4 = instance-1) is RUN-FAILED: 2 per cell skips the cell, 5 in a row aborts the campaign.
   Fix, in `run_one` just before the `(cd "$WT" && ...)` line:
   `for m in "$WT"/stats/instance-*; do [ -d "$m" ] && mountpoint -q "$m" && ! pgrep -u jhan -f "$OUR_RT_RE" >/dev/null && { fusermount3 -u "$m" 2>/dev/null || fusermount -u "$m" 2>/dev/null; echo "$(ts) unmounted a stale FUSE mount $m"; }; done`

2. **campaign.sh:210 and gen_compare.py:85-87 (should-fix). The HW attention line is cut to 240 characters in rt-results.txt and to 200 in the report; the gpt-oss line is 279 characters.** Measured on wedperf-20260916/rt/gptoss-tp4-8u__fpga__target__rep2.log.attempt1 (279) and its rt-results.txt copy (240). `hw_slots: 18` and `pre_attn_scalar` are lost; the sample report's section 1 line already ends at "gqa: 4 pre". For gpt-oss the card-layer count is the one number that explains its AVX share under FPGA attention.
   Fix: campaign.sh:210 `cut -c1-240` -> `cut -c1-400`; gen_compare.py: in `parse_stats` also capture the first full `HW attention (enabled|disabled)` line of rt/<run>.log, parse `max_layers=(\d+)`, `kv_head_size: (\d+)`, `gqa: (\d+)`, `hw_slots: (\d+)`, and print "card layers = hw_slots / n_layers" as a column in section 1 and in the 7.1 bullets ("18 of 36 layers are card candidates; the other 18 are sliding-window layers scored by the CPU").

3. **gen_compare.py:377-406 and 318 (should-fix). Section 7 trusts the cell's attention field and goes silent when the amxon run has no exit report.** If tron logs "HW-attention not available" or "HW attention disabled" (no device, bitfile), 7.1 still titles the cell "Attention on the FPGA". If the amxon run finished (rc 0, TPS lines) but printed no `[attn-stats]` block, lines 394-404 print no bullet at all, and section 3 labels it "one arm missing" although both arms ran.
   Fix: after `hm = on["stats"]["model"] or {}` add `if not any(on["d"].values()): p(f"- {cell}: the amxon run finished but its log has no [attn-stats] exit report ({on['log']})."); continue`. In the bullet add `card = "card on" if (on["hw_attn"] or "").startswith("HW attention enabled") else "card off"` and print `WARNING: cell asked for {attn} but tron ran with the card off` when `attn in ("fpga", "fpga1")` and card off. Line 318: replace `one arm missing` with `f"no exit report in {'amxon' if not don else 'amxoff'}"`.

4. **chain.sh:76 (nit). On a resume a COMMIT given on the command line is ignored when RES/main.sha exists.** Line 76 reads main.sha before it looks at `$COMMIT`. A rebuild at a newer main under the same NAME needs a manual `rm main.sha`.
   Fix, before line 76: `if [ -n "$COMMIT" ] && [ -s "$RES/main.sha" ] && [ "$COMMIT" != "$(cat "$RES/main.sha")" ]; then echo "$(ts) step F: COMMIT $COMMIT overrides main.sha $(cat "$RES/main.sha")"; echo "$COMMIT" >"$RES/main.sha"; fi`

5. **chain.sh:111 (nit). Step R overwrites PR3879/new-PRs/new-counters/attn-stats-compare.md.** A resume with `STEPS="R"` after jhan's plain-English pass loses his edits (the file does not exist yet today, so only the resume path is affected).
   Fix: before the `cp`: `[ -e "$REPORT_COPY" ] && cp -p "$REPORT_COPY" "$REPORT_COPY.$(date -u +%Y%m%dT%H%M%SZ).bak" && echo "$(ts) step R: previous copy saved as .bak"`.

6. **campaign.sh:79-84 (nit). No free-hugepage check before a run.** tp4 needs 256 hugepages (gpt-oss log: "Allocating 256 hugepages"), tp2 128. A shortfall (Bill's instance holds 256, a leftover slice file) is a RUN-FAILED that counts against the cell instead of a wait. The i4500fix chain had the check [exec/i4500fix-20260928/lib.sh:27]. hugepages_free was 512 in every recent run header, so the risk is low.
   Fix: in `blocked()` add `[ "$(awk '/^HugePages_Free/{print $2}' /proc/meminfo)" -ge "${NEED_HUGEPAGES:-256}" ] || { echo "only $(awk '/^HugePages_Free/{print $2}' /proc/meminfo) free hugepages (need ${NEED_HUGEPAGES:-256})"; return 0; }`, and in `run_one` set `NEED_HUGEPAGES=$([ "$tp" = 4 ] && echo 256 || echo 128)` before `wait_clear`.

7. **launch.sh:15 and README.md:81-82 (nit, merge with CF14). A leftover campaign.sh is not detected, and the README's stop order produces a false "ok".** launch.sh checks only for chain.sh. A running campaign.sh makes the new chain's step D exit at once on the instance lock [campaign.sh:234]; the chain then runs R and writes `chain.done` = ok. The README's own recipe (kill campaign.sh first, then chain.sh) has the same window: `finish aborted` returns, the chain continues to R and writes ok before the second kill lands.
   Fix: launch.sh:15 `pgrep -f 'attnstats-20261002/(chain|campaign)[.]sh'`; the chain-side fix is CF14 below.

8. **campaign.sh:130 (nit). A FUSE read can block while runtron dies, and `stop_poller`'s `wait` then blocks the campaign.** A subshell defers TERM while its foreground `cat` runs.
   Fix: `timeout 5 cat "$f" >"$T/$(basename "$f")" 2>/dev/null`.

9. **chain.sh:95 (nit, unverified: no ssh). build2.sh finds the owner repo by reading /var/tmp/jhan/tron-main0916/.git [exec/i4525-20260922/build2.sh:29].** If that worktree is removed, step A ends with "checkout-failed" and a misleading log line.
   Fix: before `run_build`: `[ -e /var/tmp/jhan/tron-main0916/.git ] || fail_chain "step A: build2.sh needs /var/tmp/jhan/tron-main0916 to find the owner repo"`.

10. **gen_compare.py:207 and 230 (nit). `failed` counts attempts, not runs.** A run stopped once by the watcher and finished on attempt 2 appears in both "runs finished" and "failed or stopped".
    Fix: `failed = [r for r in runs if r["kind"] == "rt" and (r["failed"] or r["stopped"]) and (r["cell"], r["attn"], r["arm"], r["rep"]) not in done]`, and in section 8 keep the full attempt list under a heading "attempts".

11. **gen_compare.py:343-356 (nit, gpt-oss). One AVX share mixes card layers and sliding-window layers.** For gpt-oss under FPGA attention the AVX K tokens of the 18 card layers (pending-page tail) and of the 18 sliding-window layers (whole window, at most 128 tokens) are summed into one share. Section 5 lists the distinct per-layer triples when there are at most 4, so the data is visible, but 7.1 does not say it.
    Fix: in section 7, from `cl["layers"]`: `avx_card = sum(v for ix, a, v, f in lay if f > 0); avx_sw = sum(v for ix, a, v, f in lay if f == 0)` and print "AVX K tokens: {avx_card} in the card layers, {avx_sw} in the software-only layers".

12. **gen_compare.py:242, 399 (nit). "fpga1 attention" is script shorthand in prose.** Fix: `ATTN_WORDS = {"cpu": "CPU attention", "fpga": "FPGA attention", "fpga1": "FPGA attention forced with USE_HW_ATTN=1"}` and use it in the headline and the 7.x bullets.

Verified, not a finding: README.md:62-65 (gpt-oss hw_slots 18, head 64, kv_mul 8, 36 layers) matches the wedperf-20260916 log line and model.hpp:1552-1560; the leaf poller's `find -maxdepth 4` matches the mount layout `stats/instance-N/model/<id>/attention` [README.stats.md:234-235; log line "Stats/config mounted at .../stats/instance-2"]; gpt-oss FPGA attention at prompt 1024 x 8 users ran with 0 HBM warnings on 09-16; prompt 8192 x 8 users fits the 2400 s timeout (92 s parse at tp2).

## Ranked fix list

Must-fix

1. gen_compare.py:255 (CF21). Replace the avx_full_page bullet with: "avx_full_page visits = AVX visits that scored a whole page (64 K tokens). With the kernel enabled these are full pages that failed the dense-page test, for example a page written in this forward. With the kill switch they also include every page the kernel would have taken. The identity in section 3 uses that."
2. gen_compare.py:259, 263-273, 399 (CF22 + CF16). Compute `fits = hm.get("head_size") == 128 and hm.get("kv_mul") == 4`; add a "kernel shape" column (fitting / non-fitting) to section 1; print it in the 7.x bullets next to amx_available; replace the definition with "fitting shape = head size 128 and kv_mul 4, the only geometry the AMX kernel accepts (shape_ok in amx_attn_iface.hpp). A non-fitting model never calls the kernel, whatever amx_available says." and add "amx_available = the process-start probe: CPU, OS and permission allow AMX, and TRON_AMX_DISABLE is not 1. It says nothing about the model shape." In section 3 print "trivial (non-fitting shape)" instead of "holds" when not fits.

Should-fix

3. chain.sh:103 (CF1 = CF18). `if [ "$(cat "$EXEC/logs/$NAME.done" 2>/dev/null)" = ok ]; then echo "... step D already done"; continue; fi`.
4. chain.sh:106-107 (CF14 + Missed 7). After campaign.sh returns: `m=$(cat "$EXEC/logs/$NAME.done" 2>/dev/null); case $m in ok*) ;; *) STEPS_LEFT=R; bash -c "..." ;; esac` in plain form: run step R inline for the partial report, then `fail_chain "step D ended: ${m:-no marker} (resume with STEPS='D R')"`. launch.sh:15: pgrep pattern `attnstats-20261002/(chain|campaign)[.]sh`.
5. campaign.sh:90 and chain.sh (CF11). In `wait_clear`, after a successful `rinzler_takeover_if_idle`: `echo "$(ts) taken down by $0 pid $$" >>"$RES/serving-taken-down.marker"`. In chain.sh add `serving_restore()` (copy of exec/i4500fix-20260928/lib.sh:54-60), call it after step D and in `trap 'serving_restore' EXIT`.
6. chain.sh:71 (CF10). `run_build() { setsid bash -c "$1" & BUILD_PGID=$!; ...; wait $BUILD_PGID; BUILD_PGID=""; }` plus `trap '[ -n "${BUILD_PGID:-}" ] && kill -TERM -- -$BUILD_PGID 2>/dev/null' TERM EXIT` near line 72. README: during step A also `kill -TERM -- -$(pgrep -f 'i4525-20260922/build2[.]sh')`.
7. campaign.sh:206 (Missed 1). Add the stale-mount loop given above before each attempt.
8. campaign.sh:40 and 117-120 (CF2 + CF19). `POLL_S=${POLL_S:-1}`; in the comment and README: the leaves are an in-flight sample for the worker and layer rows, may be missing at prompt 1024, and gen_compare.py does not use them.
9. campaign.sh:210 and gen_compare.py:85-87 (Missed 2). `cut -c1-400`; parse the full HW attention line from the run log; print hw_slots / n_layers in sections 1 and 7.1.
10. gen_compare.py:377-406, 318 (Missed 3). The no-exit-report bullet, the card-on/off check, and the section 3 label.
11. gen_compare.py:284 (CF17). `p(f"- {cell}: {r['hw_attn'] or 'no HW attention line'}; HBM warnings amxon lose={on['hbm_lose'] if on else 'n/a'} exhausted={on['hbm_exh'] if on else 'n/a'}; amxoff lose={off['hbm_lose'] if off else 'n/a'} exhausted={off['hbm_exh'] if off else 'n/a'}")`.
12. gen_compare.py:343, 354-356 (CF23). Pass `hm.get("n_kv_heads", 1)` into the triple loop and multiply `f_` by it, or change the section 5 intro to "AMX and AVX are K tokens per KV head. The FPGA value is per query (all KV heads at once). Multiply the FPGA value by n_kv_heads (8 for qwen3-4b and gpt-oss-120b) to compare it with the other two."
13. gen_compare.py:360 (CF26). Replace the T4 clause with: "T4 per forward = the sum, over the layers of one forward, of the time from the first attention job of one layer to the first attention job of the next layer, as attention worker 0 sees it. The last layer has no successor, so the sum covers n_layers - 1 layers (35 of 36 for qwen3-4b and gpt-oss-120b)."
14. gen_compare.py:228-230, 250-259, 288, 343, 402-403 (CF29 + CF30). Short version as three sentences: "Tron main {tip} ran on our half of delphi-3bda with the attention path stats on (TRON_ATTN_STATS=1). Each cell ran twice: with the AMX kernel enabled (amxon) and with it disabled by the kill switch (amxoff, TRON_AMX_DISABLE=1). {n} cells, {m} runs finished, {k} attempts failed or stopped." One term per bullet in "Words used here"; section 6 intro as four bullets; section 7: end the sentence after "avx_full_page visits N." and start "Busy per job goes from A ms to B ms (C % of amxon)."; section 5: "Layers with FPGA > 0 are the layers the card served. Layers with AMX > 0 are the layers where the kernel ran."
15. chain.sh:94-97 (CF12). Wrap step A in `for try in 1 2 3; do wait_slot ...; run_build ...; r=$(cat ...); [ "$r" = ok ] && break; grep -q "CI lease busy during step A" <(tail -5 "$LOG") && [ -z "$r" ] && continue; fail_chain "..."; done`.
16. campaign.sh:121-126 (CF13). `local out=$1 A T main=$$` and `kill -0 "$main" 2>/dev/null || exit 0` at the top of the loop.
17. gen_compare.py:217-220 (CF9 = CF27). `on = sorted(on, key=lambda r: r["rep"])`; return `on[0]`; `print(..., file=sys.stderr)` when `len(on) > 1 or len(off) > 1`; state "repetition 1 of N" in the section 1 note when `max rep > 1`.
18. gen_compare.py:242 (CF28). `f"{short_model(model)}, {ATTN_WORDS[attn]}, prompt {prompt}, {users} users ({cell}): ..."`.
19. gen_compare.py:258 and 360 (CF24). "busy = T2, the time one worker spent inside one attention job: both software passes and the join, without the upstream K/V wait."

Nits

20. chain.sh:98-101 (CF3 + CF4 + CF8). `command -v objdump >/dev/null || fail_chain "step A: objdump not found"`; `objdump -d --no-show-raw-insn "$BIN" >"$RES/dis.tmp" || fail_chain "step A: objdump failed"`; `n_amx=$(grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b' "$RES/dis.tmp")`; `n_sw=$(grep -c -a 'TRON_ATTN_STATS' "$BIN" || true); [ "${n_sw:-0}" -gt 0 ] || fail_chain "step A: TRON_ATTN_STATS literal missing (PR #4596 not in $COMMIT?)"`.
21. launch.sh:16 (CF5). `sha=$($SSH "git -C /home/jhan/workspace/tron ls-remote origin refs/heads/main" | cut -c1-10); [ -n "$sha" ] || echo "warning: 3bda cannot reach origin; step F will use COMMIT_FALLBACK"`.
22. chain.sh:81-82 (CF6). `rev-parse --short=10 origin/main` and `log -1 ... origin/main`.
23. chain.sh:64 (CF7 = CF20). `exec {CHAIN_LOCK_FD}>/var/tmp/jhan/$NAME.chain.lock; flock -n "$CHAIN_LOCK_FD" || { echo "$(ts) another chain.sh runs; exit"; exit 1; }`.
24. campaign.sh:81 (CF15). `ci_lease_busy 300`.
25. gen_compare.py:275 (CF25). "One repetition per cell: a TPS difference of a few percent cannot be separated from run-to-run variation here."
26. gen_compare.py:252, 254, 288, 307 (CF31, CF33, CF32, CF35). The four wordings given in the confirmed list (pending pass over the pages written in this forward; pending pages plural; define "software scale"; "When both arms scored the same prompts, generated the same number of tokens and had the same HBM warning counts, ...").
27. gen_compare.py:267-270 (CF34). `hm = next((r["stats"]["model"] for r in (on, off) if r and r["stats"]["model"]), {})`; print booleans as yes/no.
28. chain.sh:76 (Missed 4). COMMIT override of main.sha.
29. chain.sh:111 (Missed 5). Back up the report copy before overwriting.
30. campaign.sh:79-84 (Missed 6). Free-hugepage wait.
31. campaign.sh:130 (Missed 8). `timeout 5 cat`.
32. chain.sh:95 (Missed 9). Pre-check /var/tmp/jhan/tron-main0916/.git.
33. gen_compare.py:207, 230 (Missed 10). Attempts vs runs in the failed count.
34. gen_compare.py:343-356 (Missed 11). AVX split between card layers and software-only layers for gpt-oss.
35. gen_compare.py:242, 399 (Missed 12). Attention-mode words instead of `fpga1`.

Insufficient data (no ssh allowed): whether /var/tmp/jhan/tron-main0916 still exists on 3bda (item 32), and whether `fusermount3` is on PATH outside `nix develop` there (item 7 falls back to `fusermount`).