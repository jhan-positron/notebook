#!/usr/bin/env python3
"""fork-chain.py: make exec/pr4-20261012/chain2.sh from exec/pr3-20261012/chain2.sh by exact-text edits
(PR4-handoff.md step 6, edits 1 to 16 and 19; edit 17 is launch2.sh / wait-chain2.sh, edit 18 the copies).
Each replacement must match exactly the expected number of times, or the script stops and writes nothing.
The same for chain-finish.sh (edit 15's handler part). Re-runnable: it always starts from the PR-3 files."""
import pathlib
import sys

SRC = pathlib.Path("/home/jhan/workspace/intel-AMX/exec/pr3-20261012")
DST = pathlib.Path("/home/jhan/workspace/intel-AMX/exec/pr4-20261012")


class Text:
    def __init__(self, name):
        self.name = name
        self.s = (SRC / name).read_text()

    def rep(self, old, new, n=1):
        # n = the exact expected count; None = at least one (a mechanical rename whose leftovers the final grep catches).
        c = self.s.count(old)
        if (n is None and c == 0) or (n is not None and c != n):
            print(f"FAIL {self.name}: {c} matches (expected {n if n is not None else 'at least 1'}) for {old[:90]!r}")
            sys.exit(1)
        self.s = self.s.replace(old, new)
        print(f"  {self.name}: {c} x {old[:60]!r}")

    def write(self):
        (DST / self.name).write_text(self.s)
        print(f"wrote {DST / self.name} ({len(self.s.splitlines())} lines)")


c = Text("chain2.sh")

# ---- edit 1: the header, NAME, D, END_BY default ----
c.rep("# pr3-20261012 chain (runs ON delphi-3bda, detached): build and test PR-3 of the PR 4424 split (branch\n"
      "# jhan-vnnik-3-shared-save, PR3-handoff.md step 6). Fork of exec/pr2-20261011/chain.sh.",
      "# pr4-20261012 chain (runs ON delphi-3bda, detached): build and test PR-4 of the PR 4424 split (branch\n"
      "# jhan-vnnik-4-tail-block, PR4-handoff.md step 6). Fork of exec/pr3-20261012/chain2.sh (edits 1-16 and 19 of\n"
      "# PR4-handoff.md step 6, applied by fork-chain.py).")
c.rep('# plane is bit-identical to AMX QK from row-major K"; "block-save case" = the t_k_vnni_layout case "VNNI K block save\n'
      '# equals the per-token row store, bit for bit"; "save_k case" = the t_llama_unit case "save_k stores every token\'s K row\n'
      '# once, grouped by page block, alone or with helper threads".',
      '# plane is bit-identical to AMX QK from row-major K"; "page-state case" = the t_k_vnni_layout case "page K blocks turn\n'
      '# VNNI at the 16th saved row and back when a row is forgotten"; "save_k case" = the t_llama_unit case "save_k stores\n'
      '# every token\'s K row once, grouped by page block, alone or with helper threads".')
c.rep("#   new  = COMMIT (the PR-3 head), built into /var/tmp/jhan/tron-pr3 (runtron.pr3)\n"
      "#   head = PR2_COMMIT (the PR-2 head), /var/tmp/jhan/tron-pr2 (runtron.pr2): reused when the worktree is at PR2_COMMIT and\n"
      "#          the binary's sha256 equals the one recorded by the pr2-20261011 build; otherwise rebuilt there",
      "#   new  = COMMIT (the PR-4 head), built into /var/tmp/jhan/tron-pr4 (runtron.pr4)\n"
      "#   head = PR3_COMMIT (the PR-3 head), /var/tmp/jhan/tron-pr3 (runtron.pr3): reused when the worktree is at PR3_COMMIT and\n"
      "#          the binary's sha256 equals the one recorded by the pr3-20261012 build; otherwise rebuilt there")
c.rep("#        runtron.pr3 must carry the qwen3-4b tp2 and tp4 plugins",
      "#        runtron.pr4 must carry the qwen3-4b tp2 and tp4 plugins")
c.rep("#   M1.  mutation check of the block store: block c's rows land in block c ^ 1's panels; the block-save case must fail\n"
      "#   M2.  mutation check of the work-unit cut: a block change inside a page no longer cuts; the save_k case must fail\n"
      "#   A2.  the Haskell suite (bin/ingest-cabal test): rc 0, Failed: 0\n",
      "#   M1.  mutation check of the page state: note_k_row_saved reports an incomplete block complete (kv_cache.hpp); the\n"
      "#        page-state case must fail\n"
      "#   M2.  mutation check of the hardware-attention policy: rows are recorded only for hardware-scored operations\n"
      "#        (model.hpp); the save_k case must fail\n"
      "#   A2.  skipped and recorded: PR-4 changes no file under ingest/ (no Haskell suite run)\n")
c.rep("#   F.   clang-format 19 on the 7 changed C++ files, fourmolu on the 2 Haskell files, git diff --check, cassert count\n"
      "#        (nix shell, against PR2_COMMIT); lint-notes in the lint shell when it is available within 10 min (recorded only)\n",
      "#   F.   clang-format 19 on the 10 changed C++ files, git diff --check, cassert count (nix shell, against PR3_COMMIT);\n"
      "#        lint-notes in the lint shell (a verdict condition: PR-4 adds two Notes; one retry when the shell takes > 600 s)\n"
      "#   deb. the two Debian packages of campaign W: base from MAIN_COMMIT, then target from COMMIT, serial, on our half,\n"
      "#        through exec/pr4ci-20261012/build-deb.sh (each build waits for the lease first); both build.status files ok\n")
c.rep("#   head. the PR-2 binary: reused or rebuilt (see above)\n"
      "#   all.done = ok only when the three builds are ok and every test binary passed, both kill-switch runs exited 0, the\n"
      "#   identity case ran on AMX in A and B, the plugin check passed, both mutation checks passed, A2 is rc 0 with Failed: 0,\n"
      "#   the three format checks are rc 0 and the cassert count is 0, and the base and head binaries exist.\n",
      "#   head. the PR-3 binary: reused or rebuilt (see above)\n"
      "#   all.done = ok only when the three builds are ok and every test binary passed, both kill-switch runs exited 0, the\n"
      "#   identity case ran on AMX in A and B, the plugin check passed, both mutation checks passed, A2 is recorded as skipped,\n"
      "#   the two format checks are rc 0, the cassert count is 0 and lint-notes is rc 0, both deb builds are ok with their\n"
      "#   package checks and branch-named versions, and the base and head binaries exist.\n")
c.rep("# Whole-machine steps (exec/bill-share.sh take first, on jhan's order to execute PR3-handoff.md; refused while Bill is\n",
      "# Whole-machine steps (exec/bill-share.sh take first, on jhan's order to execute PR4-handoff.md; refused while Bill is\n")
c.rep("#        new2 (A/A), newoff (kill switch), head; cells cpu p1024, cpu p8192, fpga p1024. Must match: new == new2, new == head\n"
      "#        (newoff vs new is expected to differ at generated token 247 at cpu p1024: PR3-handoff.md 5.4). After each cell\n"
      "#        validate-smoke.py checks every arm's rc=0 line and 256 tokens.\n"
      "#   E.   performance (8 users, 256 tokens, CPU attention, 3 repetitions, arms interleaved): cells tp2 p1024, tp2 p8192,\n"
      "#        tp4 p1024; arms base, new, newoff, head, headoff; summarizer arms and pairs set with WEDPERF_ARMS / WEDPERF_PAIRS\n"
      "#   C.   the host test suite in the option-on tree (last: a late end costs it first)\n"
      "#   end. chain.done = ok | failed-<step>; then the exit handler (chain-finish.sh): stop our workload, serving up when this\n"
      "#        chain took it down (unless the lease is busy or the units are active), the Bill marker released, the machine line.\n",
      "#        new2 (A/A), newoff (kill switch), head; cells cpu p1024, cpu p8192, fpga p1024. Must match per cell: cpu cells\n"
      "#        new == new2 and new == base; the fpga cell new == new2 and new == head (PR4-handoff.md 5.4; newoff vs new is\n"
      "#        judged by the stop rule there, not by the script). After each cell validate-smoke.py checks every arm's rc=0\n"
      "#        line and 256 tokens.\n"
      "#   E.   performance (8 users, 256 tokens, 3 repetitions, arms interleaved), two campaign calls: pr4-E-cpu (CPU\n"
      "#        attention; cells tp2 p1024, tp2 p8192, tp4 p1024; arms base, new, newoff, head, headoff) and pr4-E-fpga (FPGA\n"
      "#        attention; cells tp2 p1024, tp4 p1024; arms base, new, head); summarizer arms and pairs per call\n"
      "#   C.   the host test suite in the option-on tree\n"
      "#   bench. the cost-row refresh (bin/slice bench --update of the four VNNI K tests, whole machine) after C; its diff is\n"
      "#        saved as bench-update.diff for the cost-row commit (a failure is recorded, not a stop for the smokes and cells)\n"
      "#   end. chain.done = ok | failed-<step>; then the exit handler (chain-finish.sh): stop our workload, serving up when this\n"
      "#        chain took it down (unless the lease is busy or the units are active), the Bill marker released, the hand-off\n"
      "#        marker removed when this run created it, the machine line.\n")
c.rep("# No step starts after END_BY. START_NOT_BEFORE (ISO UTC, optional) holds the whole chain until that time.\n",
      "# No step starts after END_BY, and a lease wait that reaches END_BY stops the chain (chain.done=stopped-end-by).\n"
      "# START_NOT_BEFORE (ISO UTC, optional) holds the whole chain until that time. The hand-off marker\n"
      "# /var/tmp/jhan/pr4424ci-precheck.running is created at launch by a run that owns the whole-machine part (every mode\n"
      "# except STOP_AFTER_OUR_HALF=1) and removed by its exit handler: campaign W waits for it after the lease.\n")
c.rep("# Usage (on 3bda): COMMIT=<full sha> PR2_COMMIT=<full sha> [MAIN_COMMIT=<full sha>] [END_BY=2026-10-13T01:30:00Z]\n"
      "#        [START_NOT_BEFORE=2026-10-12T13:00:00Z] bash chain.sh   (see launch.sh)\n",
      "# Usage (on 3bda): COMMIT=<full sha> PR3_COMMIT=<full sha> [MAIN_COMMIT=<full sha>] END_BY=<ISO UTC, for example\n"
      "#        2026-10-13T01:30:00Z> [START_NOT_BEFORE=2026-10-13T13:00:00Z] {STOP_AFTER_OUR_HALF=1|WHOLE_MACHINE_ONLY=1}\n"
      "#        bash chain2.sh   (see launch2.sh; always pass a mode flag and END_BY)\n")
c.rep("# chain2.sh = chain.sh split in two runs (2026-10-12 01:1x UTC, jhan: the our-half part fits before the nightly):\n",
      "# The two modes (inherited from the PR-3 fork; the chain is launched as two runs):\n")
c.rep("D=$EXEC/pr3-20261012\n", "D=$EXEC/pr4-20261012\n")
c.rep("export NAME=pr3-20261012\n", "export NAME=pr4-20261012\n")
c.rep("END_BY=${END_BY:-2026-10-13T01:30:00Z}\n", "END_BY=${END_BY:-2026-10-14T01:30:00Z}\n")

# ---- edit 3: the PR-3 record folder and the head record line ----
c.rep("PR2_RES=$EXEC/results/pr2-20261011\n", "PR3_RES=$EXEC/results/pr3-20261012\n")
c.rep("rec=$(grep -E ' gen/runtron\\.pr2$' \"$PR2_RES/build-pr2.txt\" 2>/dev/null | awk '{print $1}')",
      "rec=$(grep -E ' gen/runtron\\.pr3$' \"$PR3_RES/build-pr3.txt\" 2>/dev/null | awk '{print $1}')")

# ---- edit 5: the own-arm names (pr3 -> pr4) before the parent-arm names (edit 6: pr2 -> pr3) ----
c.rep('SUFFIX=pr3 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_6"', 'SUFFIX=pr4 CONFIGURE_ARGS="$CONF_VNNI" TARGETS="$TARGETS_6"')
c.rep("$RES/build-pr3.done", "$RES/build-pr4.done", None)
c.rep("$RES/tests-pr3.txt", "$RES/tests-pr4.txt", None)
c.rep("$RES/tests-pr3-", "$RES/tests-pr4-", None)
c.rep("plugin-calls-pr3.txt", "plugin-calls-pr4.txt", None)
c.rep("pr3nd", "pr4nd", None)
c.rep("pr3rm", "pr4rm", None)
c.rep("format-pr3.txt", "format-pr4.txt", None)
c.rep("lint-notes-pr3.txt", "lint-notes-pr4.txt", None)
c.rep("host-suite-pr3", "host-suite-pr4", None)
c.rep('WT="$WT" SUFFIX=pr3 bash "$EXEC/i4525-20260922/host-suite.sh"', 'WT="$WT" SUFFIX=pr4 bash "$EXEC/i4525-20260922/host-suite.sh"')
c.rep('runtron.pr3 $(sha256sum "$RT_NEW" | cut -c1-16)', 'runtron.pr4 $(sha256sum "$RT_NEW" | cut -c1-16)')
c.rep('echo "$(ts) runtron.pr3 qwen3-4b $m plugin strings=$n"', 'echo "$(ts) runtron.pr4 qwen3-4b $m plugin strings=$n"')
c.rep('step_done A "runtron.pr3 lacks the qwen3-4b $m plugin: abort"', 'step_done A "runtron.pr4 lacks the qwen3-4b $m plugin: abort"')

# ---- edit 6: the head step (pr2 -> pr3) ----
c.rep("# ---- head. the PR-2 binary: reuse when the worktree is at PR2_COMMIT and the sha256 matches the pr2-20261011 record, else rebuild ----",
      "# ---- head. the PR-3 binary: reuse when the worktree is at PR3_COMMIT and the sha256 matches the pr3-20261012 record, else rebuild ----")
c.rep('step_done head "runtron.pr2 reused: worktree at $PR2_COMMIT, sha256 ${cur:0:16} = pr2-20261011 record"',
      'step_done head "runtron.pr3 reused: worktree at $PR2_COMMIT, sha256 ${cur:0:16} = pr3-20261012 record"')
c.rep('step_done head "runtron.pr2 rebuilt:', 'step_done head "runtron.pr3 rebuilt:')
c.rep('SUFFIX=pr2 CONFIGURE_ARGS="$CONF_VNNI" TARGETS=runtron', 'SUFFIX=pr3 CONFIGURE_ARGS="$CONF_VNNI" TARGETS=runtron')
c.rep('step_done head-build "$(cat "$RES/build-pr2.done" 2>/dev/null)"', 'step_done head-build "$(cat "$RES/build-pr3.done" 2>/dev/null)"')

# ---- edit 4: the worktrees and binaries ----
c.rep("WT=/var/tmp/jhan/tron-pr3\n", "WT=/var/tmp/jhan/tron-pr4\n")
c.rep("WT_HEAD=/var/tmp/jhan/tron-pr2\n", "WT_HEAD=/var/tmp/jhan/tron-pr3\n")
c.rep("export RT_NEW=$WT/gen/runtron.pr3\n", "export RT_NEW=$WT/gen/runtron.pr4\n")
c.rep("export RT_HEAD=$WT_HEAD/gen/runtron.pr2   #", "export RT_HEAD=$WT_HEAD/gen/runtron.pr3   #")

# ---- edit 2: PR2_COMMIT -> PR3_COMMIT everywhere, and the two :? messages ----
c.rep("COMMIT=${COMMIT:?COMMIT (full sha of the PR-3 head) is required}", "COMMIT=${COMMIT:?COMMIT (full sha of the PR-4 head) is required}")
c.rep("PR2_COMMIT=${PR2_COMMIT:?PR2_COMMIT (full sha of the PR-2 head) is required}", "PR2_COMMIT=${PR2_COMMIT:?PR2_COMMIT (full sha of the PR-3 head) is required}")
n_pr2 = c.s.count("PR2_COMMIT")
c.rep("PR2_COMMIT", "PR3_COMMIT", n_pr2)
print(f"PR2_COMMIT -> PR3_COMMIT: {n_pr2} occurrences")

# ---- edit 7: step A's case-count text ----
c.rep("(expected 5: the block-save case is new)", "(expected 10: the five tail-block cases are new)")

# ---- edit 9: M1 and M2 ----
c.rep("BLOCK_CASE='VNNI K block save equals the per-token row store\\, bit for bit'",
      "PAGE_CASE='page K blocks turn VNNI at the 16th saved row and back when a row is forgotten'")
c.rep("# ---- M1. mutation check of the block store: block c's rows land in block c ^ 1's panels; the block-save case must fail ----\n"
      "K1=h/tron/tensor/k_vnni.hpp\n"
      "OLD1='bf16* panel = plane + (s * k_vnni::TOKEN_BLOCKS_4 + c) * k_vnni::PANEL_ELEMS_512;'\n"
      "NEW1='bf16* panel = plane + (s * k_vnni::TOKEN_BLOCKS_4 + (c ^ 1)) * k_vnni::PANEL_ELEMS_512;'\n",
      "# ---- M1. mutation check of the page state: note_k_row_saved reports every row of an incomplete block complete and the\n"
      "#      16th row not complete (kv_cache.hpp), so no block is converted through the row path; the page-state case must fail ----\n"
      "K1=h/tron/models/kv_cache.hpp\n"
      "OLD1='return (after & k_block_bits(c)) == k_block_bits(c) &&'\n"
      "NEW1='return (after & k_block_bits(c)) != k_block_bits(c) &&'\n")
c.rep('( cd "$WT" && ./gen/t_k_vnni_layout --list-tests "$BLOCK_CASE" ) >"$RES/mutation1-list.txt" 2>&1',
      '( cd "$WT" && ./gen/t_k_vnni_layout --list-tests "$PAGE_CASE" ) >"$RES/mutation1-list.txt" 2>&1')
c.rep('run_case t_k_vnni_layout "$BLOCK_CASE" >"$RES/mutation1-run.out" 2>&1; mrc=$?',
      'run_case t_k_vnni_layout "$PAGE_CASE" >"$RES/mutation1-run.out" 2>&1; mrc=$?')
c.rep('''  echo "mutant t_k_vnni_layout rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|No tests ran|All tests passed' "$RES/mutation1-run.out" | tr '\\n' ' ' | cut -c1-300)" | tee "$RES/mutation1-result.txt"''',
      '''  echo "mutant t_k_vnni_layout rc=$mrc $(grep -E 'test cases:|assertions:|FAILED:|No tests ran|All tests passed' "$RES/mutation1-run.out" | tr '\\n' ' ' | cut -c1-300) captured: $(grep -oE '^ *[A-Za-z_0-9]+ := [0-9]+' "$RES/mutation1-run.out" | head -4 | tr -s ' ' | tr '\\n' ' ')" | tee "$RES/mutation1-result.txt"''')
c.rep('''$(grep -m1 'FAILED:' "$RES/mutation1-run.out" | cut -c1-80); k_vnni.hpp reverted=$reverted; restored rc=$rrc $same"''',
      '''$(grep -m1 'FAILED:' "$RES/mutation1-run.out" | cut -c1-80) captured: $(grep -oE '^ *[A-Za-z_0-9]+ := [0-9]+' "$RES/mutation1-run.out" | head -4 | tr -s ' ' | tr '\\n' ' '); kv_cache.hpp reverted=$reverted; restored rc=$rrc $same"''')
c.rep("# ---- M2. mutation check of the work-unit cut: a block change inside a page no longer cuts; the save_k case must fail ----\n"
      "K2=h/tron/models/model.hpp\n"
      "OLD2='pg != run_page || block != run_block'\n"
      "NEW2='pg != run_page || block == run_block'\n",
      "# ---- M2. mutation check of the hardware-attention policy: rows are recorded (and blocks queued) only for hardware-scored\n"
      "#      operations (model.hpp, save_k_impl); the save_k case must fail in check_blocks ----\n"
      "K2=h/tron/models/model.hpp\n"
      "OLD2='if (!cached_operation_uses_hw(binding.operation)) {'\n"
      "NEW2='if (cached_operation_uses_hw(binding.operation)) {'\n")
c.rep('''captured: $(grep -oE '^ *(u|begin|end|t) := [0-9]+' "$RES/mutation2-run.out" | head -4 | tr -s ' ' | tr '\\n' ' ')''',
      '''captured: $(grep -oE '^ *[A-Za-z_0-9]+ := [0-9]+' "$RES/mutation2-run.out" | head -4 | tr -s ' ' | tr '\\n' ' ')''', 2)

# ---- edit 8: A2 skipped and recorded ----
c.rep('''# ---- A2. the Haskell suite (bin/ingest-cabal test) ----
wait_slot "step A2"
t0=$(date +%s)
( cd "$WT" && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-pr3.txt" 2>&1
a2_secs=$(( $(date +%s) - t0 ))
a2_rc=$(grep -oE 'ingest-cabal-test rc=[0-9]+' "$RES/ingest-test-pr3.txt" | tail -1)
a2_ok=$([ "$a2_rc" = "ingest-cabal-test rc=0" ] && grep -qE '^\\s*Failed:\\s+0\\s*$' "$RES/ingest-test-pr3.txt" && grep -q 'Test suite ingest-tests: PASS' "$RES/ingest-test-pr3.txt" && echo ok || echo failed)
step_done A2 "$a2_ok ($a2_secs s): $a2_rc $(grep -E 'Examples:|Passed:|Failed:|Test suite ingest-tests' "$RES/ingest-test-pr3.txt" | tr -s ' ' | tr '\\n' ';')"
''',
      '''# ---- A2. the Haskell suite: skipped and recorded (PR-4 changes no file under ingest/; PR4-handoff.md step 6, edit 8) ----
a2_ok=skipped; step_done A2 "skipped: PR-4 changes no file under ingest/ (no Haskell suite run)"
''')

# ---- edit 10: F without fourmolu; lint-notes as a verdict condition with one retry ----
c.rep("# ---- F. format checks (nix shell of the option-on worktree), against the PR-2 head; lint-notes recorded only ----\n",
      "# ---- F. format checks (nix shell of the option-on worktree), against the PR-3 head; lint-notes is a verdict condition ----\n")
c.rep('''  echo "fourmolu: $(fourmolu --version 2>&1 | grep -v capabilities | head -1)"
  fourmolu +RTS -N8 -RTS --mode check -o -XImportQualifiedPost ingest/src/TronCpp.hs ingest/test/LoopyTronSpec.hs 2>&1 | grep -v "256 capabilities"; echo "fourmolu rc=${PIPESTATUS[0]}"
''', '')
c.rep('''( cd "$WT" && timeout 600 "$NIX" develop .#lint --accept-flake-config -c make lint-notes 2>&1 | tail -5; rc=${PIPESTATUS[0]}; if [ $rc = 124 ]; then echo "lint-notes: not run (the lint shell was not available within 600 s)"; else echo "lint-notes rc=$rc"; fi ) >"$RES/lint-notes-pr4.txt" 2>&1
''',
      '''for attempt in 1 2; do
  ( cd "$WT" && timeout 600 "$NIX" develop .#lint --accept-flake-config -c make lint-notes 2>&1 | tail -5; rc=${PIPESTATUS[0]}; if [ $rc = 124 ]; then echo "lint-notes: not run (the lint shell was not available within 600 s; attempt $attempt)"; else echo "lint-notes rc=$rc"; fi ) >"$RES/lint-notes-pr4.txt" 2>&1
  grep -q '^lint-notes: not run' "$RES/lint-notes-pr4.txt" || break
done
''')

# ---- edit 11: the deb step after F, before A0 ----
c.rep('''# ---- A0. base build (main, runtron only) ----
''',
      '''# ---- deb. the two Debian packages of campaign W: base from MAIN_COMMIT, then target from COMMIT (serial, our half, each after a lease wait) ----
DEB=$EXEC/pr4ci-20261012/build-deb.sh
DEB_OUT=/var/tmp/jhan/pr4ci-20261012
wait_slot "step deb base"
t0=$(date +%s); ARM=base bash "$DEB" "$MAIN_COMMIT" >"$RES/deb-base.log" 2>&1; echo "deb base rc=$? in $(( $(date +%s) - t0 )) s" >>"$RES/deb-base.log"
deb_base=$(cat "$DEB_OUT/build-base.status" 2>/dev/null); deb_base_ver=$(dpkg-deb -f "$DEB_OUT/base.deb" Version 2>/dev/null)
case $deb_base_ver in *-jhan-pr4ci-base) ;; *) deb_base="bad-version:$deb_base";; esac
step_done "deb base" "$deb_base_ver $deb_base; $(grep -E 'package checks|make deb done|deb base rc=|FAILED' "$RES/deb-base.log" | tr '\\n' ';' | cut -c1-300)"
wait_slot "step deb target"
t0=$(date +%s); ARM=target bash "$DEB" "$COMMIT" >"$RES/deb-target.log" 2>&1; echo "deb target rc=$? in $(( $(date +%s) - t0 )) s" >>"$RES/deb-target.log"
deb_target=$(cat "$DEB_OUT/build.status" 2>/dev/null); deb_target_ver=$(dpkg-deb -f "$DEB_OUT/target.deb" Version 2>/dev/null)
case $deb_target_ver in *-jhan-pr4ci-target) ;; *) deb_target="bad-version:$deb_target";; esac
step_done "deb target" "$deb_target_ver $deb_target; $(grep -E 'package checks|make deb done|deb target rc=|FAILED' "$RES/deb-target.log" | tr '\\n' ';' | cut -c1-300)"

# ---- A0. base build (main, runtron only) ----
''')

# ---- the our-half verdict: format-ok 2/2, lint-notes, deb, A2 skipped ----
c.rep('''f=$(grep -cE '^(clang-format|fourmolu|diff-check) rc=0$' "$RES/format-pr4.txt"); cas=$(grep -oE '^cassert-in-diff [0-9]+' "$RES/format-pr4.txt" | awk '{print $2}')
if [ "$a" = ok ] && [ "$a3" = ok ] && [ "$b" = ok ] && [ "$a0" = ok ] && [ "$hd" = ok ] && [ "$ks_fail" = 0 ] && [ "${a_unavail:-1}" = 0 ] && [ "${b_unavail:-1}" = 0 ] && [ "$plugin_ok" = ok ] && [ "$m1_ok" = ok ] && [ "$m2_ok" = ok ] && [ "$a2_ok" = ok ] && [ "$f" = 3 ] && [ "${cas:-1}" = 0 ]; then echo ok >"$RES/all.done"
else echo "failed vnni=$a nodispatch=$a3 rm=$b base=$a0 head=$hd killswitch-failed=$ks_fail amx-unavailable-A=$a_unavail amx-unavailable-B=$b_unavail plugin=$plugin_ok mutation1=$m1_ok mutation2=$m2_ok haskell=$a2_ok format-ok=$f/3 cassert=${cas:-?}" >"$RES/all.done"; fi
''',
      '''f=$(grep -cE '^(clang-format|diff-check) rc=0$' "$RES/format-pr4.txt"); cas=$(grep -oE '^cassert-in-diff [0-9]+' "$RES/format-pr4.txt" | awk '{print $2}')
ln=$(grep -c '^lint-notes rc=0$' "$RES/lint-notes-pr4.txt")
if [ "$a" = ok ] && [ "$a3" = ok ] && [ "$b" = ok ] && [ "$a0" = ok ] && [ "$hd" = ok ] && [ "$ks_fail" = 0 ] && [ "${a_unavail:-1}" = 0 ] && [ "${b_unavail:-1}" = 0 ] && [ "$plugin_ok" = ok ] && [ "$m1_ok" = ok ] && [ "$m2_ok" = ok ] && [ "$a2_ok" = skipped ] && [ "$f" = 2 ] && [ "${cas:-1}" = 0 ] && [ "$ln" = 1 ] && [ "$deb_base" = ok ] && [ "$deb_target" = ok ]; then echo ok >"$RES/all.done"
else echo "failed vnni=$a nodispatch=$a3 rm=$b base=$a0 head=$hd killswitch-failed=$ks_fail amx-unavailable-A=$a_unavail amx-unavailable-B=$b_unavail plugin=$plugin_ok mutation1=$m1_ok mutation2=$m2_ok haskell=$a2_ok format-ok=$f/2 cassert=${cas:-?} lint-notes=$ln deb-base=$deb_base deb-target=$deb_target" >"$RES/all.done"; fi
''')

# ---- edit 15: the hand-off marker (created at launch by a run that owns the whole-machine part) ----
c.rep("MARKER_TAKEN=0\nSERVING_DOWN_BY_US=0\n",
      "MARKER_TAKEN=0\nSERVING_DOWN_BY_US=0\n"
      "MARKER=/var/tmp/jhan/pr4424ci-precheck.running   # the hand-off marker campaign W waits for (campaign.sh hard-codes the name)\n"
      "MARKER_CREATED=0\n")
c.rep('''if [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ]; then rm -f "$RES/chain.done"; else rm -f "$RES/all.done" "$RES/chain.done"; fi
''',
      '''if [ "${WHOLE_MACHINE_ONLY:-0}" = 1 ]; then rm -f "$RES/chain.done"; else rm -f "$RES/all.done" "$RES/chain.done"; fi
if [ "${STOP_AFTER_OUR_HALF:-0}" != 1 ]; then touch "$MARKER" && MARKER_CREATED=1; echo "$(ts) hand-off marker $MARKER created (campaign W waits for its removal)"; fi
''')

# ---- edit 19: END_BY inside the lease wait ----
c.rep('''wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }''',
      '''wait_slot() { local w=0; while ci_lease_busy 600 || other_user_active 2>/dev/null || preci_hold; do past_end && { step_done end-by "past END_BY while waiting before $1: stop"; echo stopped-end-by >"$RES/chain.done"; exit 1; }; [ $w = 0 ] && echo "$(ts) waiting before $1: CI lease busy, another person active, or the 02:10-03:45 UTC pre-CI hold"; w=1; sleep 120; done; echo "$(ts) $1 may start"; }''')

# ---- edit 13: step D's must-match pairs per cell ----
c.rep('''export MUST_MATCH="new:new2 new:head"
export DEADLINE_HHMM=0130
''', '''export DEADLINE_HHMM=0130
''')
c.rep('''  set -- $spec; attn=$1; prompt=$2; shift 2
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
''', '''  set -- $spec; attn=$1; prompt=$2; shift 2
  case $attn in cpu) export MUST_MATCH="new:new2 new:base";; fpga) export MUST_MATCH="new:new2 new:head";; esac
  ATTN=$attn PROMPT=$prompt LEN=256 SMOKE_ARMS="$*" bash "$S/smoke.sh"
''')

# ---- edit 12: E as two campaign calls ----
c.rep('''# ---- E. performance (5 arms, 3 cells: tp2 p1024, tp2 p8192, tp4 p1024) ----
''', '''# ---- E. performance: pr4-E-cpu (5 arms, 3 cells: tp2 p1024, tp2 p8192, tp4 p1024), then pr4-E-fpga (3 arms, 2 cells: tp2 p1024, tp4 p1024) ----
''')
c.rep('''if past_end; then step_done E "skipped: past END_BY"; else
  NAME=pr3-E-cpu CELLS_ALL="$(cells 2:1024 2:8192 4:1024)" ARMS="base new newoff head headoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \\
    WEDPERF_ARMS="base new newoff head headoff" WEDPERF_PAIRS="new:base new:head newoff:new newoff:headoff head:base" bash "$S/campaign.sh"
  step_done E "$(cat "$EXEC/logs/pr3-E-cpu.done" 2>/dev/null); head line: $(grep -m1 '^# arms:' "$EXEC/results/pr3-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-200)"
fi
''', '''if past_end; then step_done E-cpu "skipped: past END_BY"; else
  NAME=pr4-E-cpu CELLS_ALL="$(cells 2:1024 2:8192 4:1024)" ARMS="base new newoff head headoff" ATTNS=cpu REPS=3 DEADLINE_HHMM=0130 \\
    WEDPERF_ARMS="base new newoff head headoff" WEDPERF_PAIRS="new:base new:head newoff:new newoff:headoff head:base" bash "$S/campaign.sh"
  step_done E-cpu "$(cat "$EXEC/logs/pr4-E-cpu.done" 2>/dev/null); head line: $(grep -m1 '^# arms:' "$EXEC/results/pr4-E-cpu/rt-results.txt" 2>/dev/null | cut -c1-200)"
fi
if past_end; then step_done E-fpga "skipped: past END_BY"; else
  NAME=pr4-E-fpga CELLS_ALL="$(cells 2:1024 4:1024)" ARMS="base new head" ATTNS=fpga REPS=3 DEADLINE_HHMM=0130 \\
    WEDPERF_ARMS="base new head" WEDPERF_PAIRS="new:base new:head head:base" bash "$S/campaign.sh"
  step_done E-fpga "$(cat "$EXEC/logs/pr4-E-fpga.done" 2>/dev/null); head line: $(grep -m1 '^# arms:' "$EXEC/results/pr4-E-fpga/rt-results.txt" 2>/dev/null | cut -c1-200)"
fi
''')

# ---- edit 14: the bench step after C, before the end verdict; edit 16: the end verdict's text ----
c.rep('''# ---- end. the verdict; serving up and the marker release follow in the exit handler ----
h=$(cat "$RES/host-suite-pr4.done" 2>/dev/null)
''', '''# ---- bench. the cost-row refresh (bin/slice bench --update of the four VNNI K tests; whole machine; after C) ----
bn=skipped
if past_end; then step_done bench "skipped: past END_BY"; else
  wait_slot "step bench"
  cp "$WT/config/test-benchmarks.json" "$RES/test-benchmarks.before.json"
  t0=$(date +%s)
  ( cd "$WT" && timeout -k 60 1800 "$NIX" develop --accept-flake-config --command bash -c '
    bin/slice route; echo "route rc=$?"
    env -u SYSTEM_CONFIG bin/slice bench --check-platform; echo "check-platform rc=$?"
    env -u SYSTEM_CONFIG bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics t_amx_dispatch_dtype; echo "bench-update rc=$?"' ) >"$RES/bench-update.log" 2>&1
  echo "bench wall $(( $(date +%s) - t0 )) s" >>"$RES/bench-update.log"
  ( cd "$WT" && git diff -- config/test-benchmarks.json ) >"$RES/bench-update.diff" 2>&1
  bstat=$(cd "$WT" && git diff --stat -- config/test-benchmarks.json | tail -1 | sed 's/^ *//')
  if grep -q '^bench-update rc=0$' "$RES/bench-update.log" && ! grep -qE '\\[FAILED\\]|\\[SKIPPED\\]|BENCH FAILURES' "$RES/bench-update.log" && [ "$bstat" = "1 file changed, 4 insertions(+), 4 deletions(-)" ]; then bn=ok; else bn=failed; fi
  step_done bench "$bn; diff: ${bstat:-none}; $(grep -E 'rc=|Updated|Calibration|Box capacity|bench wall' "$RES/bench-update.log" | tr '\\n' ';' | cut -c1-300)"
fi

# ---- end. the verdict; serving up and the marker release follow in the exit handler ----
h=$(cat "$RES/host-suite-pr4.done" 2>/dev/null)
''')
c.rep('''e=$(cat "$EXEC/logs/pr3-E-cpu.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo "ok (E: $e)" >"$RES/chain.done"; else echo "failed host=$h smoke=$s1/$s2/$s3 E=$e" >"$RES/chain.done"; fi
''', '''e1=$(cat "$EXEC/logs/pr4-E-cpu.done" 2>/dev/null); e2=$(cat "$EXEC/logs/pr4-E-fpga.done" 2>/dev/null)
if [ "$h" = ok ] && [ "$s1" = ok ] && [ "$s2" = ok ] && [ "$s3" = ok ]; then echo "ok (E: $e1/$e2 bench: $bn)" >"$RES/chain.done"; else echo "failed host=$h smoke=$s1/$s2/$s3 E=$e1/$e2 bench=$bn" >"$RES/chain.done"; fi
''')
c.rep('echo "=== $NAME chain finished $(ts): $(cat "$RES/chain.done") (the exit handler restores serving and releases the marker next) ==="',
      'echo "=== $NAME chain finished $(ts): $(cat "$RES/chain.done") (the exit handler restores serving, releases the marker and removes the hand-off marker next) ==="')
c.write()

# ---- chain-finish.sh: edit 15's handler part ----
f = Text("chain-finish.sh")
f.rep("# The exit handler of the pr3-20261012 chain (PR3-handoff.md step 6, \"The exit handler\"). Sourced by chain.sh and,\n"
      "# with stubs, by cleanup-test.sh. It needs these names from the sourcing script: ts, machine, DUT (dut.sh path),\n"
      "# BILL_SHARE (bill-share.sh path), OUR_RT_RE (regex of our runtron binaries' command lines), NAME, and the two\n"
      "# flags MARKER_TAKEN and SERVING_DOWN_BY_US, plus ci_lease_busy and rinzler_active (lib-guard.sh or stubs).\n"
      "# Order: stop this chain's remaining workload and wait for it; restore serving when this chain took it down,\n"
      "# unless the CI lease is busy or the units are already active; release Bill's marker when this chain took it;\n"
      "# print the machine line. FINISHED guards against a second run (the TERM trap and the EXIT trap both call it).\n",
      "# The exit handler of the pr4-20261012 chain (PR4-handoff.md step 6, edit 15; fork of exec/pr3-20261012/chain-finish.sh).\n"
      "# Sourced by chain2.sh and, with stubs, by cleanup-test.sh. It needs these names from the sourcing script: ts, machine,\n"
      "# DUT (dut.sh path), BILL_SHARE (bill-share.sh path), OUR_RT_RE (regex of our runtron binaries' command lines), NAME,\n"
      "# MARKER (the hand-off marker path), and the three flags MARKER_TAKEN, SERVING_DOWN_BY_US and MARKER_CREATED, plus\n"
      "# ci_lease_busy and rinzler_active (lib-guard.sh or stubs).\n"
      "# Order: stop this chain's remaining workload and wait for it; restore serving when this chain took it down,\n"
      "# unless the CI lease is busy or the units are already active; release Bill's marker when this chain took it;\n"
      "# remove the hand-off marker when this run created it (a marker another run holds is left alone); print the machine\n"
      "# line. FINISHED guards against a second run (the TERM trap and the EXIT trap both call it).\n")
f.rep('''release_marker() {
  if [ "$MARKER_TAKEN" = 1 ]; then bash "$BILL_SHARE" release 2>&1 | tail -1; echo "$(ts) finish: Bill marker released"
  else echo "$(ts) finish: marker not taken by this chain, nothing to release"; fi
}
''', '''release_marker() {
  if [ "$MARKER_TAKEN" = 1 ]; then bash "$BILL_SHARE" release 2>&1 | tail -1; echo "$(ts) finish: Bill marker released"
  else echo "$(ts) finish: marker not taken by this chain, nothing to release"; fi
}
remove_handoff_marker() {
  if [ "$MARKER_CREATED" = 1 ]; then rm -f "$MARKER"; echo "$(ts) finish: hand-off marker removed"
  else echo "$(ts) finish: hand-off marker not created by this run, left alone"; fi
}
''')
f.rep('''  release_marker
  echo "$(ts) machine at exit: $(machine)"
''', '''  release_marker
  remove_handoff_marker
  echo "$(ts) machine at exit: $(machine)"
''')
f.write()
print("fork-chain.py: done")
