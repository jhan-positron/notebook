### [0] git-patch | Section 3, deviation 1
QUOTE: In the patch that policy is one condition inside save_k_impl (`if (!cached_operation_uses_hw(binding.operation))`, 3 lines with its comment) and one Note in kv_cache.hpp
PROBLEM: "3 lines with its comment" does not match the code. The policy is one `if` line preceded by a three-line comment, and the `if` guards a 12-line loop that records the rows and queues the blocks. The count as written reads as if the whole policy were 3 lines.
FIX: "(one `if` line with a three-line comment; it guards the 12-line loop that records the rows and queues the completed blocks, model.hpp:3425 at the probe)"

### [1] git-patch | Section 4, step 4.1 (the 38-cell variant)
QUOTE: (the probe: handoff-material/probe-pr4/pr4probe-38.log)
PROBLEM: pr4probe-38.log holds 2 lines only: the last cell's line and the verdict. The per-cell record of the probe's 38-cell run is out-38/summary.txt (38 lines). PR-3's pr3probe-38.log held all 38 cell lines, so an executor who compares the two logs finds the PR-4 one truncated.
FIX: "(the probe: handoff-material/probe-pr4/out-38/summary.txt, 38 cell lines; pr4probe-38.log holds the verdict line only)"

### [2] git-patch | Section 2, the inputs table, row "T patch base"
QUOTE: built and tested 2026-10-08 (45e6bb266d, one comment line less)
PROBLEM: 45e6bb266d is the parent of ba69cb513e. The two differ by a reworded four-line comment in model.hpp (ba69cb513e adds 4 lines and removes 3), not by one line removed. The net count is one line, but the wording hides that the text differs.
FIX: "built and tested 2026-10-08 at 45e6bb266d, the parent of ba69cb513e; the two differ by a reworded comment in model.hpp (+4/-3 lines, 'Fix grammar in save_k worker comment')"

### [3] scripts | Section 5.3, The schedule, option (b)
QUOTE: W alone on D+1 with the 2026-10-09 knobs moved by date (NOT_BEFORE 13:00, DEADLINE_START 19:00, PASS_DEADLINE 23:30, DRIVER_END_BY 02:05 D+2)
PROBLEM: The 2026-10-09 run did not use PASS_DEADLINE 23:30. Its launch line recorded PASS_DEADLINE=2026-10-10T00:30:00Z. The 23:30 value is the script's default.
FIX: "W alone on D+1 with the script's default knobs moved by date (NOT_BEFORE 13:00, DEADLINE_START 19:00, PASS_DEADLINE 23:30, DRIVER_END_BY 02:05 D+2; the 2026-10-09 run itself used PASS_DEADLINE 00:30 D+2)".

### [4] scripts | Step 6, edit 12 (the FPGA campaign invocation)
QUOTE: record the "lose HW attention" and "HBM bypass space exhausted" counts per run (campaign.sh:177, 188), which summarize.py shows per arm row
PROBLEM: summarize.py's arm row shows only the mean of the "lose HW attention" count (column "HBM-exhaustion warnings per run (mean)"). The "HBM bypass space exhausted" count is parsed into summary.json (hbm_exh) and is not in the markdown table.
FIX: "... (campaign.sh:177, 188); summarize.py shows the mean 'lose HW attention' count per arm row, and both counts per run are in summary.json (hbm_lose, hbm_exh)."

### [5] scripts | Step 7.2 (the fill-body.py fork)
QUOTE: its cell parser keys rows by `q3-4b-tp<tp>-8u-p<prompt>` and accepts attn = cpu only (fill-body.py:29, 32, 36)
PROBLEM: The key regex is at line 28, the cpu filter at line 29, the arm-row parse at lines 31-32 and the pair-row parse at lines 33-36.
FIX: "(fill-body.py:28-29, 31-32, 33-36)".

### [6] scripts | Section 5.3, The cost-row refresh, and step 6 row bench
QUOTE: about 2 min of measurement (106 s for three tests on 2026-10-08)
PROBLEM: No record of that 106 s was found. The cost-row commit 6b939d25d2 names the command, the host and the time (13:50 UTC) but no duration. No log under exec/logs/, exec/results/savek2-20261008/ or exec/results/merge4737-20261008/ holds a `bin/slice bench` run. Insufficient data.
FIX: Name the source of the 106 s, or write "about 2 min (est.: the sum of the current rows is 28.3 s + 0.9 s + 0.8 s + 0.9 s per width, three widths, two parallel slots)".

### [7] scripts | Section 5.3, Campaign W (what launch.sh validates)
QUOTE: the harness checkout (no local change under scripts/ or testlib/; HEAD at 14f0ce4 with the 2026-10-09 stash; a moved origin/main prints a note only)
PROBLEM: launch.sh checks only two of these. It refuses local changes under scripts/ and testlib/ and prints a note when HEAD differs from origin/main. It does not check that HEAD is 14f0ce4 and does not look at the stash; step 0.6 of the handoff does that.
FIX: "the harness checkout (no local change under scripts/ or testlib/; a moved origin/main prints a note only; the 14f0ce4 and stash checks are step 0.6, not launch.sh)".

### [8] scripts | Step 6, intro (the chain variables)
QUOTE: The chain's two modes (STOP_AFTER_OUR_HALF, WHOLE_MACHINE_ONLY), START_NOT_BEFORE, END_BY and DEADLINE_HHMM stay as PR-3's.
PROBLEM: The END_BY default is the fixed date 2026-10-13T01:30:00Z in chain2.sh and in launch2.sh. It fits only a whole-machine part that runs on the night of 2026-10-12. On any later day a launch without an explicit END_BY runs the our-half part and then stops at :288 with chain.done=stopped-end-by.
FIX: Add to edit 1 or edit 17: "move the END_BY default at chain2.sh:66 and launch2.sh:3, :5 to the planned date, and always pass END_BY on the launch line".

### [9] scripts | Step 6, edit 9 (the mutation checks)
QUOTE: the comment line (:175 / :199), the file variable (:176 / :200), OLD/NEW (:177-178 / :201-202), the case-name constant (:89 / :90, commas escaped with a backslash), the binary name in `--list-tests` (:179 / :203), ...
PROBLEM: Two more texts name PR-3's files and captures. The M1 STEP line at :194 says "k_vnni.hpp reverted=" while PR-4's M1 reverts kv_cache.hpp. The M2 lines at :210 and :218 grep the captured values with the PR-3 names `(u|begin|end|t) :=`; PR-4's M2 failure captures other names, so the "captured:" field stays empty unless the pattern is changed (the handoff asks to record the counts and captured values).
FIX: Add to edit 9: "the file name in the STEP text (:194 'k_vnni.hpp' becomes 'kv_cache.hpp'; :218 keeps 'model.hpp') and the capture pattern at :210 and :218 (the names that PR-4's save_k case CAPTUREs, or a generic `^ *[A-Za-z_0-9]+ := `)".

### [10] code-tests | Step 6, row A, t_llama_unit count
QUOTE: t_llama_unit: record it (about 276591 est.; T adds two sections and block checks to the save_k case that PR-3 rewrote twice, so the 2026-10-08 delta does not add exactly)
PROBLEM: The estimate adds T's delta to PR-3's count at 80bce9a08d (269326). The chain bases on dfafd13dce, whose t_llama_unit count is 269328 (section 0 says so). 269328 + 7265 = 276593.
FIX: about 276593 est. (269328 at dfafd13dce plus T's measured delta of 7265)

### [11] code-tests | Words, 'Block save (PR-3)' entry
QUOTE: Masked partial-block path (PR-3): the branch of save_k that stores a run of 2 to 15 tokens with masked line stores (set_k_block's `present` parameter, k_scatter_run_len, the `n == k_scatter_run_len` branch of store_k_block)
PROBLEM: The `n == k_scatter_run_len` branch is the one-token scatter branch (set_k_row). The masked partial-block store was the else branch of that test. The parenthesis names the wrong branch.
FIX: (set_k_block's `present` parameter, k_scatter_run_len, the else branch of store_k_block's `n == k_scatter_run_len` test)

### [12] code-tests | Section 5.2, 'Present', kv_cache.hpp bullet
QUOTE: the copy_storage_slot overload that takes a k_storage_ref
PROBLEM: There is one copy_storage_slot. Its first parameter changed from kv_storage_offset to k_storage_ref. It is not an overload. A grep for a second definition finds none.
FIX: copy_storage_slot with a k_storage_ref as its first parameter (the pair replaces the kv_storage_offset argument; its two callers copy_from and the EAGLE copy build the pair)

### [13] code-tests | Step 3, commit (a)
QUOTE: Adds Note [Row-major tail block], row_major_row, block_to_vnni, block_to_rows, block_bit, offset_bit, BLOCKS_PER_PAGE_MASK_0XF;
PROBLEM: Commit (a)'s tensor/k_vnni.hpp also adds PANEL_ROWS_4, store_row_major and load_row_major. Section 5.2 lists them; the commit list omits them. The commit message written from this list would be incomplete.
FIX: Adds Note [Row-major tail block], row_major_row, store_row_major, load_row_major, block_to_vnni, block_to_rows, PANEL_ROWS_4, block_bit, offset_bit, BLOCKS_PER_PAGE_MASK_0XF;

### [14] code-tests | Step 6, row M1 (and the budget line 'M1 about 5 min')
QUOTE: kv_cache.hpp is included by libtron sources, so the rebuild is longer than a test-only change: about 5 min, est.
PROBLEM: PR-3's M1 mutated h/tron/tensor/k_vnni.hpp, which reaches libtron through the same kv_cache.hpp include chain. Its whole step (mutant build, case run, restore build, whole-binary run) took 91 s. The 5-minute estimate is about three times the record. It only inflates the budget.
FIX: about 2 min, est. (PR-3's M1 step, a tensor/k_vnni.hpp mutation with the same include chain, took 91 s for build, run, restore and the whole-binary run)

### [15] code-tests | Step 6, row M2
QUOTE: Expected: a "FAILED:" line at that REQUIRE, a test-cases line that ends in "1 failed", and 4 failed assertions
PROBLEM: The line number of the REQUIRE is not given, while M1 gives its line (691). Reading confirms the prediction: all four leaf sections fail at the same REQUIRE, because Catch2 marks the failed section's parent as needing another run (TrackerBase::fail) and runs the next leaf section; with the mutant the one-thread, 'another operation' and three-thread sections fail at check_blocks(true) (0x8 against 0x9) and the 'scores the operation' section at the second check_blocks(false) (0x9 against 0x8). Giving the line makes the verdict easy to check by eye.
FIX: Expected: four "FAILED:" lines at t/t_llama_unit.cpp:4054 (the line at the probe; re-find by the text `REQUIRE(pages[0]->template k_vnni_blocks<geometry.kv>(slot) == page0)`), one per leaf section (Catch2 re-runs the case for the next section after a failed REQUIRE), the summary lines `test cases:    1 |    0 passed | 1 failed` (the padded "0" column is printed) and `assertions: N | P passed | 4 failed`

### [16] code-tests | Section 5.5, first bullet
QUOTE: Option off (every preset except deb): no behaviour change.
PROBLEM: The option-off page also carries the two new per-slot atomic arrays (n_slots + 1 entries of 8 bytes and of 1 byte), and clear_kv_complete_at now calls k_forget_row, which makes two atomic loads per slot and continues. Functional behaviour is unchanged; the struct size and one call per forgotten token are not. 'No functional change' is the defensible claim.
FIX: Option off (every preset except deb): no functional change (the page carries the two bit arrays in every build, and k_forget_row makes two loads per slot and returns).

### [17] policy | 4. Step 3, commit (d) (against step 7.1)
QUOTE: (d) later, after step 6's bench: "chore(bench): refresh the cost rows": config/test-benchmarks.json.
PROBLEM: Step 7.1 gives a different subject for the same commit.
FIX: Step 3 (d): '"chore(bench): refresh the cost rows of the VNNI K tests (granite_rapids_6962p)"'.

### [18] policy | Words used here, PR-3; 0. State of PR-1 to PR-3
QUOTE: Its review round 1 (codex, 2026-10-12 15:46 UTC) was being answered at the time of writing (split-status.md, "PR-3 review round 1").
PROBLEM: Stale. The round was answered before this file's stated writing time (about 18:00 UTC): the fix was pushed at 16:27 UTC, the body was patched at 16:27 UTC and the replies were posted by 16:3x UTC. Line 80 repeats 'the body edit and the replies were pending at 16:30 UTC'.
FIX: Line 14: 'Its review round 1 (codex, 2026-10-12 15:46 UTC) was answered the same day (fix dfafd13dce pushed 16:27 UTC, body and replies posted 16:3x UTC; split-status.md, "PR-3 review round 1").' Line 80: the same, and drop 'pending at 16:30 UTC'.

### [19] policy | 2. Inputs, table row PR-3 head
QUOTE: the draft CI set passed at 80bce9a08d
PROBLEM: The draft set also passed at dfafd13dce, the head PR-4 bases on.
FIX: 'the draft CI set passed at 80bce9a08d (run 38270438657) and at dfafd13dce (run 38277492157)'.

### [20] policy | 3. Target, deviation 4
QUOTE: origin/main was 9a2c97eeb8 on 2026-10-11 14:27 UTC, 3 merges past 72308ec90c on that day alone
PROBLEM: The merge count does not match git. Between 72308ec90c and 9a2c97eeb8 there are 5 merges: 3 on 2026-10-10 and 2 on 2026-10-11.
FIX: 'origin/main was 9a2c97eeb8 on 2026-10-11 14:27 UTC, 5 merges past 72308ec90c in two days'.

### [21] policy | 4. Step 6, row A
QUOTE: t_llama_unit: record it (about 276591 est.; T adds two sections and block checks to the save_k case that PR-3 rewrote twice, so the 2026-10-08 delta does not add exactly)
PROBLEM: The estimate adds the T delta (259020 - 251755 = 7265) to 269326, the count at 80bce9a08d. The base dfafd13dce has 269328 (two more assertions), so the same arithmetic gives 276593.
FIX: 'about 276593 est. (269328 at dfafd13dce plus the 2026-10-08 delta of 7265; ...)'.

### [22] policy | 7. Reporting and checkpoints, stop list
QUOTE: - the harness checkout ~/workspace/ai-runs/systems_test is not at 14f0ce4 or is dirty.
PROBLEM: Three stop conditions that other sections imply are missing from the list: a section-0 decision with no fitting default (split-handoff.md section 7), a host-suite result other than the known exceptions (5.4: 'Anything else is a finding'), and a cell with fewer than 3 usable repetitions (5.4: 'No claim without n >= 3'; EARLY-STOP and RUN-FAILED records).
FIX: Add three lines: '- the host suite shows a failure or a skip other than t_proxy_lib, t_proxy_llama31 and the 6 heap_setup cases;', '- a cell of E has fewer than 3 usable repetitions for TPS or TTFT (EARLY-STOP or RUN-FAILED);', '- a decision of section 0 is needed and no default fits.'

### [23] policy | 9. Do not
QUOTE: - Do not promote PR-2, PR-3 or PR-4; promotion is jhan's word, after the parent merges.
PROBLEM: Four rules live only in other sections and are missing from the list a reader checks last: never rebase (step 8), never run build-branch.sh on the branch after the push (step 5.3), never touch tron-pr4424ci, tron-pr4424 or /var/tmp/jhan/pr4424ci-20261009 (section 0), do not apply the protected-section wording proposal of PR 4424 (D6; split-handoff.md section 9 lists it as a 'Do not').
FIX: Add four bullets: '- Do not rebase jhan-vnnik-4-tail-block; merges only.', '- Do not run build-branch.sh on the branch after the first push.', '- Do not touch /var/tmp/jhan/tron-pr4424ci, /var/tmp/jhan/tron-pr4424 or /var/tmp/jhan/pr4424ci-20261009/.', '- Do not apply the standing protected-section wording proposal of PR 4424 anywhere.'

### [24] policy | 4. Step 0.7 (against section 7)
QUOTE: Append your record to split-status.md in this folder under a new heading "# split-status: PR-4 of the PR 4424 split" (section 7).
PROBLEM: Section 7 names the heading differently ('under the heading "PR-4"').
FIX: Section 7: 'under the heading "# split-status: PR-4 of the PR 4424 split", with "## PR-4 Step N" subheadings as the PR-3 record'.

### [25] policy | Words used here, Promote
QUOTE: Promote: mark a draft PR ready for review (AGENTS.md: only after its parent merges, and only when jhan says so).
PROBLEM: AGENTS.md states the first condition only. 'Only when jhan says so' is this handoff's rule.
FIX: '(AGENTS.md:12-13: only after its parent merges; this file and section 9: only when jhan says so)'.

### [26] policy | 4. Step 8, last bullet
QUOTE: Re-run D and E with a base built from the merged main and a head built from PR-3's merged state, and W with a base deb from the merged main.
PROBLEM: 'PR-3's merged state' is ambiguous once PR-3 is in main: the head arm is then the merged main built with the option on. The bullet also re-runs D, E and W after the main merge, which is more than split-handoff.md step 5 asks (syntax matrix, clang-format, the unit-test chain, provenance) and is not flagged as a deviation; it is gated on jhan's word, so a note suffices.
FIX: 'a head built from the merged main with the option on (PR-3's content is then in main)'; add '(the D, E and W re-runs go beyond split-handoff.md step 5; jhan decides the scope)'.

### [27] policy | 4. Step 6, edit 8 (against section 3 deviations)
QUOTE: The plugin check (:170-173) stays as a regression check (15 s): the generated plugins of the option-on build must carry the same save_k call forms as PR-3's (PASS for all 19 plugins); it stays part of all.done.
PROBLEM: split-handoff.md's chain table marks the generated-plugin grep 'no' for PR-4. Keeping it is a small departure that section 3 does not list.
FIX: Add one line to the deviations: 'The generated-plugin check of PR-3 is kept as a 15 s regression check in all.done (split-handoff.md 5.3 marks it "no" for PR-4); if jhan rejects it, record it as skipped with A2.'

### [28] policy | 5.3 The schedule, option (b) and the rule
QUOTE: Option (b): everything of the chain on D evening (the our-half part, the two deb builds, the whole-machine part: about 3 h 30 min measured basis, 4 h 15 min README basis; the whole-machine part must end by 01:30 UTC, so launch by 21:00 UTC, better 20:00)
PROBLEM: Option (b) reads as one full-mode launch, but the rule picks the option by the our-half verdict, which a single full run cannot wait for. The two chain modes make the rule workable only when the our-half run is launched first in both options.
FIX: Add before the two options: 'In both options launch the our-half run first (STOP_AFTER_OUR_HALF=1, with the deb step). The option sets the WHOLE_MACHINE_ONLY run's knobs: (b) launch it at the verdict with END_BY=<D+1>T01:30:00Z; (a) launch it with START_NOT_BEFORE=<D+1>T13:00:00Z and END_BY=<D+2>T01:30:00Z.'

### [29] provenance | Words used here, the PR-3 entry
QUOTE: pushed 2026-10-12 about 16:25 UTC
PROBLEM: The record gives 16:27 UTC.
FIX: "pushed 2026-10-12 16:27 UTC".

### [30] provenance | Words used here, the nightly entry
QUOTE: holds the lease until about 13:15 to 13:30 UTC
PROBLEM: The four observed releases of 2026-10-09 to 2026-10-12 run from 13:19 to 13:36 UTC, as section 5.3 itself states; 13:30 understates the latest observed value by 6 min.
FIX: "holds the lease until about 13:20 to 13:40 UTC (observed 13:19 to 13:36 UTC on 2026-10-09 to 2026-10-12, section 5.3)".

### [31] provenance | 5.5, the FPGA-attention bullet
QUOTE: -17.6 % at tp4 (t +5.6; the tp4 arms have sd 4.6 to 8.4 TPS and the A/A pair differs by 6 %)
PROBLEM: The range 4.6 to 8.4 names neither arm of the pair exactly and leaves out one arm. The pair's arms have sd 5.3 and 7.1 TPS. The five tp4 arms of the block range from 2.5 to 8.4 TPS.
FIX: "-17.6 % at tp4 (t +5.6; the pair's arms have sd 5.3 TPS (vnni) and 7.1 TPS (base), the five tp4 arms of the block 2.5 to 8.4 TPS, and the A/A pair vnni2 vs vnni differs by +6.0 %)".

### [32] provenance | 3. Target, deviation 4 (outside the listed sections; reported because it is a number against a git record)
QUOTE: origin/main was 9a2c97eeb8 on 2026-10-11 14:27 UTC, 3 merges past 72308ec90c on that day alone
PROBLEM: There were 2 merges on 2026-10-11 UTC and 5 merges in total between 72308ec90c and 9a2c97eeb8.
FIX: "origin/main was 9a2c97eeb8 on 2026-10-11 14:27 UTC, 5 merges past 72308ec90c in the 37 h since that commit".

### [33] executor | Step 0.5
QUOTE: Record the lease state, the rinzler units, the marker (`ls -la /bill-has-instance-0,2`), the hugepage counts (`grep -i hugepages_ /proc/meminfo`) and `df -h /var/tmp`.
PROBLEM: The hand-off marker /var/tmp/jhan/pr4424ci-precheck.running is not checked. A stale file would make W wait until DEADLINE_START and abort. The chain's handler removes it, so the risk is low, but a step-0 check costs one command.
FIX: Add: "`ls -la /var/tmp/jhan/pr4424ci-precheck.running` must fail (no stale hand-off marker; if it exists, report it and remove it with rm before the launch)."

### [34] executor | Step 6, edit 5
QUOTE: :244, :251-253
PROBLEM: Line 244 of chain2.sh is the `nix develop` opener of step F and holds no "pr3" text; the result-file names of F are at :251 (format-pr3.txt), :252 (lint-notes-pr3.txt) and :253.
FIX: Replace ":244, :251-253" with ":251-253".

### [35] executor | Step 6 (variables) and edit 17
QUOTE: The chain's two modes (STOP_AFTER_OUR_HALF, WHOLE_MACHINE_ONLY), START_NOT_BEFORE, END_BY and DEADLINE_HHMM stay as PR-3's.
PROBLEM: PR-3's END_BY default is the fixed date 2026-10-13T01:30:00Z (chain2.sh:66, launch2.sh:5, the usage comment :45-46). A run on a later day that omits END_BY would start its whole-machine part already past END_BY and stop with stopped-end-by.
FIX: Add to edit 1 and edit 17: "the END_BY defaults at chain2.sh:66 and launch2.sh:5 and the usage comment :45-46 take the run's date, and every launch passes END_BY explicitly (section 5.3 gives the value per option)".

### [36] executor | 7. Reporting and checkpoints
QUOTE: Keep split-status.md in this folder up to date after every step, under the heading "PR-4"
PROBLEM: Step 0.7 names the heading "# split-status: PR-4 of the PR 4424 split", and the PR-3 record uses sub-headings of the form "## PR-3 Step N: ...". The two sentences differ, and the sub-heading form is not stated.
FIX: Write: "under the heading of step 0.7 (`# split-status: PR-4 of the PR 4424 split`), with one sub-heading per step in PR-3's form (`## PR-4 Step N: <what> (<UTC times>) <state>`)".

### [37] executor | Step 0.3
QUOTE: Leave the worktrees tron-split-probe (the PR-2 probe) and tron-split-pr1 to pr3 alone.
PROBLEM: Two more worktrees of this handoff's verification exist now and are not mentioned: ~/workspace/ai-runs/tron-verify-pr4-gitlens (dfafd13dce) and ~/workspace/ai-runs/tron-verify-pr4-refmerge (0a5334ccb6). The executor sees them in `git worktree list` and has to guess whether they matter.
FIX: Add: "The worktrees tron-verify-pr4-gitlens and tron-verify-pr4-refmerge are leftovers of this handoff's verification; leave them alone (or remove them with `git worktree remove`, never with a prune)."

### [38] executor | Step 6, row deb
QUOTE: `ARM=base` from MAIN_COMMIT (72308ec90c) in /var/tmp/jhan/tron-pr4ci-base on the local branch jhan-pr4ci-base, then `ARM=target` from COMMIT in /var/tmp/jhan/tron-pr4ci-target on the local branch jhan-pr4ci-target.
PROBLEM: The call form of build-deb.sh is not fixed: here ARM looks like an environment variable, section 5.3 says "with an ARM argument", and build-target.sh takes the commit as $1 or COMMIT. The chain edit and the by-hand call must agree.
FIX: State one form: "`ARM=base bash exec/pr4ci-<date>/build-deb.sh <MAIN_COMMIT>` and `ARM=target bash exec/pr4ci-<date>/build-deb.sh <COMMIT>` (ARM from the environment, the commit as the first argument, as build-target.sh takes it)."

### [39] executor | 5.3 Rules (the lease wait)
QUOTE: the chain's own wait_slot polls every 120 s with no timeout, bounded by END_BY
PROBLEM: wait_slot has no END_BY test. The past_end test of the whole-machine part runs before wait_slot "step 0", so a lease that clears after END_BY still lets the chain take Bill's marker and bring serving down; only D, E and C are then skipped.
FIX: Write "bounded by the past_end tests before each whole-machine step" and add to edit 15 or a new edit: "after `wait_slot \"step 0\"` repeat the past_end test (`past_end && { step_done 0 \"past END_BY after the lease wait\"; echo stopped-end-by >\"$RES/chain.done\"; exit 1; }`) so that a late lease never starts the takeover."

### [40] plain-english | Words used here (lines 21, 24, 39, 40, 41, 43)
QUOTE: runs functional, perf, MMLU Pro and soak phases
PROBLEM: Rule 1. Words itself uses undefined terms: MMLU Pro and soak (line 40), systemd (39), KiB (21), CMake (24), fourmolu and <cassert> (43), VmHWM and VmRSS (41), HugetlbPages (line 453).
FIX: Add clauses: "MMLU Pro (an accuracy benchmark of multiple-choice questions) and soak (a long run under steady load)"; "systemd (Linux's service manager)"; "KiB (1024 bytes)"; "CMake (the build-configuration tool tron uses)"; "fourmolu (the Haskell formatter)"; "the no-cassert check (<cassert> is the C assert header the repo forbids)"; "VmHWM (a process's peak resident memory), VmRSS (its current resident memory) and HugetlbPages (its hugepage memory), all read from /proc/<pid>/status".

### [41] plain-english | Step 1.4 table (lines 199-204)
QUOTE: every staged K value checked through the K swizzle
PROBLEM: Rule 1. The classification table names hunks by code labels that the file never defines: K swizzle, role-swap sentence, result-buffer comment, Q_PACK_ELEMS_2048 and scalar-gate comments, k_destination_row, Var tokens, s_star matcher, v_star_tolerance, rows_pack_calls probe field, k_packed comment, the "Why" paragraph, kv_slot_id.
FIX: Add one sentence before the table: "The labels in the Where column are words taken from each hunk's own text; find a hunk by grepping its label in handoff-material/probe-pr4/diff-vs-ref.patch."

### [42] plain-english | Section 0 table (lines 60, 70) and section 3 (line 125), Words (line 12)
QUOTE: sw-dev-01 is not used.
PROBLEM: Rule 1. Undefined: "concern T" (line 60; split-plan.md's word), sw-dev-01 (70), jhan-positron (125), the label "Skip benchmarks" (125), "mergeable" and "review required" (12).
FIX: "(concern: split-plan.md's word for one separable part of PR 4424)"; "sw-dev-01 (the build host split-handoff.md D11 names) is not used"; "assignee jhan-positron (jhan's GitHub account)"; "label \"Skip benchmarks\" (the GitHub label that turns the benchmark jobs of gcp-nix.yml and the legacy lane off)"; "mergeable (GitHub reports no conflict with its base), review required (the repo's branch rule)".

### [43] plain-english | Step 6 edit 1, edit 17 (lines 281, 297) and 5.3 (line 402)
QUOTE: edit 1: NAME, D and the header comments
PROBLEM: Rule 1. Script variables named without meaning: D (chain2.sh's script folder), R (wait-chain2.sh), H, RESD, LOG, OUT (launch.sh).
FIX: "NAME, D (the chain's script folder variable, chain2.sh:54) and the header comments"; "wait-chain2.sh (R, its results folder variable; the pgrep pattern ...)"; "launch.sh (H the host, RESD the results folder, LOG the log path, OUT the package folder, at :11-15)".

### [44] plain-english | Words (lines 27, 33, 39) and Step 5.2 (line 268)
QUOTE: the policy block after the join
PROBLEM: Rule 1. "the join" (268), "the cooperative FPGA staging" (27, 87, 452), "scratch" (33) and "the takeover path" (39) are used without a definition; the takeover is explained only at line 395.
FIX: "the join (the point where save_k's main call waits for its helpers)"; "the cooperative FPGA staging (the staging work the pass's worker threads do alongside the compute; wait_for_coop_gof waits for it: confirm the wording against full.hpp)"; "into scratch (a temporary buffer)"; in Words line 39: "the takeover path: stopping the rinzler units through platformd's API (dut.sh serving-down or rinzler_takeover_if_idle), so that platformd does not restart them".

### [45] plain-english | Words (line 41), Step 6 (lines 335, 396), 2. Inputs (line 115)
QUOTE: the four cards of placement 4
PROBLEM: Rule 1. "placement 4" (396), "the 5-minute idle test" (335), "provisioning" (41), "preflight" (115, 400, 402) are undefined.
FIX: "placement 4 (the campaign script's card and core assignment for tp4; its placement() function)"; "the 5-minute idle test (dut.sh stops serving only after 5 min without a request line in the rinzler journal)"; "provisioning (installing a deb and starting the engines for one configuration)"; "the preflight (campaign W's checks before its first pass)".

### [46] plain-english | Step 6 (lines 288, 294, 302), Section 0 (line 76), 1 (line 88), Step 8 (line 362)
QUOTE: it stays part of all.done
PROBLEM: Rule 1. Terms used before their definition: all.done and chain.done (288, 294; defined at 300), pre-review (76), comparator (88), provenance (362; defined at 442), venv (302; defined at 419), light work (159; defined at 394), hunk (185).
FIX: Move each definition to the first use: "all.done (the chain's our-half verdict file) and chain.done (its end verdict file)"; "PR-3's pre-review (the review pass of its step 5, run before the machine run)"; "comparator (a comparison arm)"; "provenance (commit id and date of each measured binary)"; "the t_proxy_llama31 venv (Python virtual environment) failure"; "light work only (ls, git rev-parse, sha256sum, reading files)"; "hunk (one contiguous changed region of a diff)".

### [47] plain-english | Words (line 20), Step 1 (line 166), 2. Inputs (lines 100, 104), Step 5 (275), 5.3 (394, 400), Traps (490, 494)
QUOTE: The `-c rerere.enabled=false` keeps rerere from recording the preimages
PROBLEM: Rule 1. Tool and git terms without a clause: three-way apply (20, 108), preimage (166), post-image (100), remote-tracking ref (104), detached (186, 336), amend and fixup commit (275), cron (394), uv and ghcup (400), HF_OFFLINE (490), SIGTERM and -9 (490), NaN (494), REST PATCH and LF (359), TRON_ASSERT (198), libtron (308), lambda (76), ctest manifest (320), sha256 and md5 (47, 402), pgrep, pkill, setsid, taskset, flock, dpkg-deb, objdump, strings, nice.
FIX: Add a Words row "Tools and git terms" with one clause each, for example: "--3way (git merges a patch through the blobs it names, so a context mismatch becomes conflict markers instead of a reject); preimage (the conflicted text rerere stores to recognise the same conflict later); post-image (the tree a patch produces); HF_OFFLINE (Hugging Face tokenizers are read from the local cache only); ctest manifest (the test command list CMake writes into the build tree); TRON_ASSERT (the repo's assertion macro); libtron (the tron library target); pgrep and pkill (find and kill processes by pattern); sha256 and md5 (file checksums)".

### [48] plain-english | Step 5.2 (lines 245, 269, 273), 5.2 (line 383)
QUOTE: the VNNI-build K instance of the apply-and-join case
PROBLEM: Rule 1. "apply-and-join case", "K instance" (245, 273, 383), "relevant" (269), "the dense predicate" (269), "the identity case" (202, 327, 410, 494) are undefined.
FIX: "the apply-and-join case (the t_llama_unit TEST_CASE check_page_range_reductions; its K instance is the block under #ifdef TRON_K_VNNI that runs it on K pages)"; "relevant (a K token the query may attend to)"; "the dense predicate (is_dense_amx_page)"; "the identity case (the t_amx_numerics case that compares the AMX QK kernel's scores with the reader's; it prints 'AMX unavailable on this host - VNNI QK identity check skipped' when it cannot run)".

### [49] plain-english | 5.5 (line 429)
QUOTE: the policy build's decode Save K span stayed above the canonical build's
PROBLEM: Rule 1. "policy build" and "Save K span" are undefined.
FIX: "the policy build (the i4500c arm that carried the hardware-attention policy) ... Save K span (the Perfetto span tron records around save_k)".

### [50] plain-english | Section 0 D5 (line 64), 2. Inputs (line 115), deviation 4 (line 136)
QUOTE: the cells of split-handoff.md 5.3 row E
PROBLEM: Rule 1. "row E" and "row W" are row labels of another file's table and are not explained here.
FIX: "row E and row W (the rows of split-handoff.md's test table in its section 5.3: E the runtron cells, W the whole-machine campaign)".

### [51] plain-english | Section 3 deviation 5 (line 137)
QUOTE: campaign W measures that cell only through the proxy with 10 rounds per pass
PROBLEM: Rule 1 and Rule 6. "the proxy" is undefined and is a figurative word.
FIX: "campaign W measures that loss only through the nightly's two qwen3-4b configurations (tp2 and tp4 under FPGA attention), which stand in for the 8-user cell, with 10 rounds per pass".

### [52] plain-english | Step 2 (line 238), Step 3 (line 242), 6 (line 441), Traps (line 496)
QUOTE: No narration word in the added lines
PROBLEM: Rule 1 and Rule 6. "narration" is jargon of these handoffs and is never defined.
FIX: At line 238: "No narration word (narration: text about the change's history, its PR or its review, rather than its mechanism) in the added lines".

### [53] plain-english | Words (line 48), 2. Inputs (lines 115, 117), Step 6 (line 279)
QUOTE: Fork the folder into exec/pr4ci-<date>/
PROBLEM: Rule 1. "fork" (verb, 20 lines) is used in a project sense that a general dictionary does not give.
FIX: At the first use (line 48): "forked (fork: copy the script into the new folder and edit the copy; the original stays unchanged)".

### [54] plain-english | Section 3 deviation 4 (line 136) and Step 6 (lines 291, 306, 404, 406)
QUOTE: about 30 to 40 min (est.) on our half, next to serving
PROBLEM: Rule 1 and Rule 6. "next to serving" is an idiom of these handoffs and is not defined.
FIX: At line 136: "next to serving (while the rinzler units keep serving on socket 0)"; later uses may keep the phrase.

### [55] plain-english | Step 1.4 table (line 201) and Traps (line 494)
QUOTE: The tail-block tests use the poison 0xa5a5 and random rows.
PROBLEM: Rule 1 and Rule 6. "poison" is jargon for a fill pattern.
FIX: "the poison (a fill pattern, 0xa5a5, that a correct result never contains) and random rows"; at line 201 "the two poison comments (the comments on the fill pattern)".

### [56] plain-english | Section 0 D11 (line 70) and Step 0 heading (line 150)
QUOTE: about 30 to 40 min each on our half
PROBLEM: Rule 3. Estimates without "est.": line 70 (deb build time; line 136 labels the same figure est.), line 150 "(claude-box, about 45 min)", line 355 "about 1.5 min" (the test-slice job; not said whether measured).
FIX: "about 30 to 40 min each (est.; 17 min measured on 2026-10-08)"; "(claude-box, about 45 min est.)"; "about 1.5 min (est., or cite the PR-3 run that measured it)".

### [57] plain-english | Step 6 table, row A (line 306)
QUOTE: t_amx_dispatch_dtype about 2143 in 1 (1618 + 525; record it
PROBLEM: Rule 3. An estimate without "est." (the t_llama_unit count in the same cell is labelled). Same cell: "the kill-switch run prints 3" has no noun.
FIX: "t_amx_dispatch_dtype about 2143 in 1 (est.: 1618 + 525; record the measured count ...)"; "the kill-switch run prints 3 such lines".

### [58] plain-english | Step 6 table, deb row (line 314)
QUOTE: the TRON_AMX_DISABLE literal >= 1 and AMX tile instructions >= 50
PROBLEM: Rule 3. Two counts without a unit.
FIX: "at least 1 occurrence of the TRON_AMX_DISABLE string and at least 50 AMX tile instructions in the rinzler binary".

### [59] plain-english | 5.5 (line 434) and 6 (line 453)
QUOTE: (|paired t| >= 2.26 and |delta| >= 1 %, two pass pairs of 10 rounds)
PROBLEM: Rule 3. 2.26 has no meaning clause.
FIX: "(|paired t| >= 2.26, the two-sided 5 % threshold for 9 degrees of freedom, and |delta| >= 1 %; two pass pairs of 10 rounds)".

### [60] plain-english | Section 0 (line 79) and 5.3 (line 396)
QUOTE: 512 hugepages all taken by serving
PROBLEM: Rule 3. The hugepage size is not given, so the amount of memory cannot be judged. The file does not state it: Insufficient data (Hugepagesize in /proc/meminfo on delphi-3bda would give it).
FIX: "512 hugepages (of <size> each; read Hugepagesize from /proc/meminfo in step 0.5)".

### [61] plain-english | 6. The body, Verification (line 456)
QUOTE: the deb preset now compiles the option into the released package, so the required CI tests a configuration the package does not ship, and the whole-machine campaign of this PR and the nightly after the merge test the shipped one
PROBLEM: Rule 2. Three claims joined by "so" and "and" inside a 270-word item.
FIX: "The deb preset now compiles the option into the released package. The required CI therefore tests a configuration the package does not ship. The whole-machine campaign of this PR and the nightly after the merge test the shipped one."

### [62] plain-english | Step 6 table, row A (line 306)
QUOTE: the delta is exact because the five cases are separate TEST_CASEs
PROBLEM: Rule 2. Two claims joined by "because".
FIX: "The delta is exact: the five cases are separate TEST_CASEs." -> "The five cases are separate TEST_CASEs. So the delta adds exactly."

### [63] plain-english | 2. Inputs (line 109)
QUOTE: without `--3way`, `git apply --check` reports a context failure on README.ci.md, because PR-1 and PR-2 reworded the lines around the paragraph.
PROBLEM: Rule 2. Two claims joined by "because".
FIX: "Without `--3way`, `git apply --check` reports a context failure on README.ci.md. The reason: PR-1 and PR-2 reworded the lines around the paragraph."

### [64] plain-english | Step 5.3 (line 275)
QUOTE: before every later push, `git merge-base --is-ancestor origin/jhan-vnnik-4-tail-block HEAD` must succeed, because section 9 forbids a force-push.
PROBLEM: Rule 2. Two claims joined by "because".
FIX: "Before every later push, `git merge-base --is-ancestor origin/jhan-vnnik-4-tail-block HEAD` must succeed. Section 9 forbids a force-push."

### [65] plain-english | 5.3 Build recipe (line 397)
QUOTE: If nix refuses to evaluate because main added a file under nix/ that the worktree's index does not track, run `git add -A .` first.
PROBLEM: Rule 2 and Rule 8. An "if" clause with a "because" and a relative clause inside.
FIX: "nix may refuse to evaluate when main added a file under nix/ that the worktree's index does not track. Then run `git add -A .` first."

### [66] plain-english | 5.3 Campaign W (line 402)
QUOTE: its "Runs found" line prints "tron None" because it reads versions["tron"] while the record's key is "Tron (package)": fix or ignore
PROBLEM: Rule 2. Two claims joined by "because" plus a "while" clause.
FIX: "Its 'Runs found' line prints 'tron None'. It reads versions['tron'], and the record's key is 'Tron (package)'. Fix it or ignore the line."

### [67] plain-english | Words, Storage ref (line 31)
QUOTE: taken at the save (page::k_storage_of) so that a later storage-view change cannot redirect a pending conversion.
PROBLEM: Rule 2. "so that" joins two claims.
FIX: "It is taken at the save (page::k_storage_of). A later storage-view change then cannot redirect a pending conversion."

### [68] plain-english | Words, Hand-off marker (line 48)
QUOTE: written by the chain before it waits for the lease and removed by its exit handler, so that W and the chain never wait for the same lease event.
PROBLEM: Rule 2. "so that" joins two claims; three facts in one sentence.
FIX: "The chain writes it before it waits for the lease. The chain's exit handler removes it. W and the chain then never wait for the same lease event."

### [69] plain-english | Step 6 edit 15 (line 295)
QUOTE: so that it exists before any lease wait; in chain-finish.sh add `rm -f "$MARKER"` as the last action of finish(), after the marker release, and list MARKER among the names the handler needs
PROBLEM: Rule 2 and Rule 8. "so that" plus a semicolon join four instructions in one 59-word sentence.
FIX: "Then it exists before any lease wait. In chain-finish.sh add `rm -f \"$MARKER\"` as the last action of finish(), after the marker release. List MARKER among the names the handler needs (chain-finish.sh:3-5)."

### [70] plain-english | 5.3 The deb recipe (line 400)
QUOTE: then put on a local branch with `git checkout -q -B <branch>`, so that bin/get-version.sh appends the branch name to the deb version
PROBLEM: Rule 2. "so that" joins the action and its effect inside a 116-word sentence.
FIX: "Then the worktree is put on a local branch with `git checkout -q -B <branch>`. bin/get-version.sh then appends the branch name to the deb version (...)."

### [71] plain-english | 5.5 (line 432)
QUOTE: since the store is the same with or without the switch.
PROBLEM: Rule 2. Causal "since" joins two claims.
FIX: "... TTFT +768 ms / +65.7 s / +268 ms). The store is the same with or without the switch."

### [72] plain-english | Step 0.5 (line 159)
QUOTE: `sha256sum /var/tmp/jhan/tron-pr3/gen/runtron.pr3` must print 9b3ba64b...; `git -C /var/tmp/jhan/tron-pr3 rev-parse HEAD` must be the PR-3 head you base on (...); `sha256sum ...` must print 365869...; `ls -d ...` must fail for all five; `ls /var/tmp/jhan/pr4424ci-20261009/` shows the 2026-10-09 packages (leave them).
PROBLEM: Rule 2 and Rule 7. One sentence of 73 words with 5 semicolons carries five separate checks; the same holds for step 0.2 (line 154), 0.3 (157), 0.4 (158) and 0.6 (160).
FIX: One sub-bullet per check, each as its own sentence: "- `sha256sum .../runtron.pr3` prints 9b3ba64b...." "- `git -C /var/tmp/jhan/tron-pr3 rev-parse HEAD` prints the PR-3 head you base on. ..."

### [73] plain-english | 5.4 Smokes (line 414)
QUOTE: This is the claim of the PR: with the tail block the blocks a decode step completes are scored by the dotter until the forward end converts them, and a converted block holds the same values; in the measured cells the generated tokens equal main's.
PROBLEM: Rule 2 and Rule 8. Three claims joined by "and" and a semicolon, with two subordinate clauses.
FIX: "This is the claim of the PR. With the tail block, the dotter scores the blocks a decode step completes until the forward end converts them. A converted block holds the same values. In the measured cells the generated tokens therefore equal main's."

### [74] plain-english | Section 3 deviation 4 (line 136), Step 6 deb row (314), 5.3 (402, 405), Traps (489)
QUOTE: the knobs EXPECTED_BASE and EXPECTED_BASE_SHA of campaign.sh
PROBLEM: Rule 6. "knob" is an idiom for a configuration variable (5 occurrences).
FIX: Replace "knob(s)" with "variable(s)" at every occurrence.

### [75] plain-english | 5.3 Schedule (lines 404, 405)
QUOTE: slack before DRIVER_END_BY about 1 h 50 min
PROBLEM: Rule 6. "slack" is an idiom for spare time (3 occurrences; line 508's "Slack" is the product name and is fine).
FIX: "spare time before DRIVER_END_BY about 1 h 50 min"; "A W pass that fails and repeats uses the spare time"; "(spare time about 4 h; ...)".

### [76] plain-english | Section 3 deviation 4 (line 136), deviation 8 (140), Step 1.4 table (207)
QUOTE: the nightly deb of the day carries main's drift since then
PROBLEM: Rule 6. "drift" is a metaphor (4 occurrences: main's drift, machine drift, main drift, "no such drift").
FIX: "the nightly deb of the day carries the commits main gained since then"; "as a control for a change of the machine's speed between sessions"; table row: "main difference"; "The 2026-10-09 run had no such difference".

### [77] plain-english | Step 0.2 (line 154), 0.6 (160), Step 1.2 (166), edit 6 (286), 5.3 (402), Stop and ask (467)
QUOTE: If it moved (a further review round on PR-3)
PROBLEM: Rule 6. "moved" for a branch that gained commits is a metaphor (7 occurrences in that sense, plus "GitHub's main moves daily" at 104).
FIX: "If its head changed (a further review round on PR-3)"; "If the harness checkout changed or is dirty"; "Any other conflict means PR-3's head changed"; "If PR-3's head changed again"; "a changed origin/main prints a note only"; "origin/jhan-vnnik-3-shared-save has new commits past dfafd13dce"; "GitHub's main gains commits daily".

### [78] plain-english | 1. Context (line 88), deviation 11 (143), 6 (442)
QUOTE: (main be0d5565b3 era; the body carries none of these as a comparator)
PROBLEM: Rule 6. "era" is a metaphor (3 occurrences).
FIX: "(measured when main was at be0d5565b3; ...)"; "They are numbers measured against an older main"; "No comparator measured before the split (the PR 4424 binaries)".

### [79] plain-english | 5.5 (line 431) and 6. Open items (457)
QUOTE: the settling measurement: the Save K and convert_k_blocks spans of a Perfetto trace
PROBLEM: Rule 6. "settling measurement" is an uncommon phrase (2 occurrences).
FIX: "the measurement that would decide it: the Save K span and the convert_k_blocks span of a Perfetto trace ...".

### [80] plain-english | Section 0 D10 (line 69), 1. Context (87), Step 1.3 (170)
QUOTE: set_k_block loses its `present` parameter, k_scatter_run_len goes, and store_k_block's branch becomes `n < k_store_block`.
PROBLEM: Rule 6. "goes" meaning "is removed" is an idiom (3 occurrences: lines 69, 87 "The masked partial-block path of PR-3 goes", 170 "PR-2's sentence ... goes").
FIX: Replace "goes" with "is removed" at each occurrence.

### [81] plain-english | 5.2 Absent (line 385)
QUOTE: the PR-1-only text (PR-2 removed it; it must not come back)
PROBLEM: Rule 6. "come back" is an idiom.
FIX: "(PR-2 removed it; it must not reappear)".

### [82] plain-english | Step 8 (line 363)
QUOTE: the stack merges downward (PR-2 merges PR-1, PR-3 merges PR-2)
PROBLEM: Rule 6. "merges downward" is a metaphor.
FIX: "each PR of the stack merges its parent (PR-2 merges PR-1, PR-3 merges PR-2)".

### [83] plain-english | 5.3 Bill's marker (line 395) and 9. Do not (line 510)
QUOTE: jhan's order to execute this handoff is the word those texts require
PROBLEM: Rule 6. "the word" and "jhan's word" are idioms for an explicit instruction (lines 395 twice, 510).
FIX: "jhan's order to execute this handoff is the explicit instruction those texts require"; line 510: "only jhan decides a promotion, after the parent merges".

### [84] plain-english | 5.3 The deb recipe (line 400) and Traps (line 489)
QUOTE: a detached build would get a nightly-looking version
PROBLEM: Rule 6. "nightly-looking" is informal (2 occurrences); "tells our packages from nightlies" (400) and "tell it from a nightly deb" (489) use the idiom "tell X from Y".
FIX: "a detached build would get a version string of the nightly's form (date and commit only)"; "campaign W distinguishes our packages from nightlies by the substring 'jhan'"; "so the campaign's preflight can distinguish it from a nightly deb".

### [85] plain-english | 5.5 (line 433)
QUOTE: a larger deviation says the machine's speed changed between the two sessions, which qualifies every other pair of this run.
PROBLEM: Rule 6 and Rule 2. "qualifies" is used in an uncommon sense; two claims in one sentence.
FIX: "A larger deviation says that the machine's speed changed between the two sessions. That change casts doubt on every other pair of this run."

### [86] plain-english | Section 0 D8 (line 67) and 1. Context (line 89)
QUOTE: For PR-4 the gap has a new side
PROBLEM: Rule 6. "a new side" is a metaphor (2 occurrences).
FIX: "For PR-4 the gap has a second part"; "The CI gap you inherit, with a second part".

### [87] plain-english | 5.3 Rules (line 394)
QUOTE: The nightly's GitHub cron fires at 03:30 UTC
PROBLEM: Rule 6. "fires" is jargon; the same bullet has "brings serving up" (idiom; also lines 40 and 421).
FIX: "The nightly's GitHub schedule starts it at 03:30 UTC"; "the 02:45 ci-runner-stop timer starts the rinzler units".

### [88] plain-english | Step 6 edit 5 (line 285), Step 4 (253), 5.2 (385, 386), 5.3 (392), 7 (463), Words (26)
QUOTE: or a blanket pr3-to-pr4 renames the parent arm too
PROBLEM: Rule 6, remaining single uses: "blanket" (285), "its cell logs land in" (253), "0 hits" and "has hits" (385, 386), "delphi-3bda answered local-legacy" (392), "hand jhan the exact command" (463), "a full 64-token page that the query sees whole" (26), "the campaign took the machine" (295), "drained" (27, 87, 452), "takes the ... path/loop/branch" (12 occurrences).
FIX: "or a global pr3-to-pr4 rename renames the parent arm too"; "its cell logs are written to"; "0 matches", "has matches"; "`bin/slice route` printed local-legacy on delphi-3bda"; "give jhan the exact command"; "a full 64-token page that the query attends to in whole"; "the campaign started its run on the machine"; "has finished" for "drained"; "uses the software loop" for "takes the software loop" (optional: the phrase is consistent and readable).

### [89] plain-english | Words, The probe of this handoff (line 20)
QUOTE: a scratch worktree ~/workspace/ai-runs/tron-split-probe-pr4 at dfafd13dce on which the T patch and the B patch were applied on 2026-10-12 about 16:30 UTC with `git -c rerere.enabled=false apply --3way`, the five conflict blocks resolved by handoff-material/probe-pr4/resolve.py, and the one-line cstring edit made (a first probe on 80bce9a08d, before the PR-3 fix was pushed, gave the same numstats with six blocks; its classification of the reference diff is the one step 1.4 carries).
PROBLEM: Rule 8. One sentence of 74 words with three subordinate clauses and a parenthesis that holds two more claims.
FIX: "The probe of this handoff: the scratch worktree ~/workspace/ai-runs/tron-split-probe-pr4 at dfafd13dce. On 2026-10-12 about 16:30 UTC the T patch and the B patch were applied there with `git -c rerere.enabled=false apply --3way`. resolve.py resolved the five conflict blocks, and the one-line cstring edit was made. A first probe on 80bce9a08d, before the PR-3 fix was pushed, gave the same numstats with six blocks. Step 1.4 carries that first probe's classification of the reference diff."

### [90] plain-english | Section 0, state list (line 76)
QUOTE: The four comment conflict blocks of step 1 come from PR-2's and PR-3's comment wording in h/tron/kernels/amx_attn_iface.hpp (Note [QK orientation]), h/tron/kernels/k_vnni.hpp (the reader comment), h/tron/models/kv_cache.hpp (Note [K VNNI storage] items 2 and 3) and h/tron/tensor/k_vnni.hpp (the file header), which the T patch, made against ba69cb513e, did not know.
PROBLEM: Rule 8. A 60-word sentence whose relative clause ("which the T patch ... did not know") hangs after a four-item list; the whole bullet has 83 words per sentence on average.
FIX: "The four comment conflict blocks of step 1 are in h/tron/kernels/amx_attn_iface.hpp (Note [QK orientation]), h/tron/kernels/k_vnni.hpp (the reader comment), h/tron/models/kv_cache.hpp (Note [K VNNI storage] items 2 and 3) and h/tron/tensor/k_vnni.hpp (the file header). PR-2 and PR-3 reworded those comments. The T patch was made against ba69cb513e and does not carry that wording."

### [91] plain-english | 1. Context (line 87)
QUOTE: What T does: (1) a run shorter than a block is stored row by row into the block's own bytes (4 whole lines per token), so a decode step writes 4 lines instead of 64, and the FPGA staging reads the row directly; (2) ... (5) ...
PROBLEM: Rule 8 and Rule 7. One 153-word sentence holds five numbered mechanisms, each with a "so" or "and" clause.
FIX: Turn (1) to (5) into five sub-bullets, each of one to three short sentences, for example: "1. A run shorter than a block is stored row by row into the block's own bytes (4 whole lines per token). A decode step therefore writes 4 lines instead of 64. The FPGA staging reads the row directly."

### [92] plain-english | Section 3 deviation 2 (line 134)
QUOTE: The resolution keeps PR-3's section (two windows, the late helper, the finished count read at return) and adds the patch's two hardware-attention sections before it and the patch's checks after each window (pre_save, check_marks, check_blocks before and after convert_pending_k_blocks, a second row check).
PROBLEM: Rule 8. A 48-word sentence with two coordinated additions and two parenthetical lists; the next sentence ("The probe compiled it in every syntax cell, and the reader-side review ... found no defect by reading (...); whether it passes is known only from step 6, A.") joins three claims.
FIX: "The resolution keeps PR-3's section (two windows, the late helper, the finished count read at return). It adds the patch's two hardware-attention sections before that section. It adds the patch's checks after each window (pre_save, check_marks, check_blocks before and after convert_pending_k_blocks, a second row check). The probe compiled it in every syntax cell. The reader-side review of this handoff found no defect by reading (...). Whether it passes is known only from step 6, A."

### [93] plain-english | Step 1.3, t/t_llama_unit.cpp item (line 182)
QUOTE: The patch's checks after the join are then added by the two EDITS of resolve.py after each of PR-3's two shared saves: after `const uint32_t finished_0 = shared_save(operation);` and `check(before);` the five lines `...`, and before the second window `pre_save();` after `slot = operation_1.binding.kv_slot;` plus the same five lines (with `before_1`) after `const uint32_t finished_1 = shared_save(operation_1);` and `check(before_1);`.
PROBLEM: Rule 8. One 80-word sentence with nested "after ... and ... plus ... after ... and" placements; the executor must verify resolve.py's edits against it.
FIX: Two sub-bullets: "- EDIT 1: after `const uint32_t finished_0 = shared_save(operation);` and `check(before);`, insert the five lines `check_marks(); check_blocks(/*converted=*/false); state.convert_pending_k_blocks(); check_blocks(/*converted=*/true); check(before);`." "- EDIT 2: before the second window, insert `pre_save();` after `slot = operation_1.binding.kv_slot;`. After `const uint32_t finished_1 = shared_save(operation_1);` and `check(before_1);`, insert the same five lines with `before_1`."

### [94] plain-english | Step 1.5 (line 186)
QUOTE: If the reference worktree is gone (step 0.3), recreate it: `git -C ~/workspace/tron worktree add --detach ...`, then in it `git -c rerere.enabled=false merge --no-commit --no-ff 72308ec90c...` (expected: "Automatic merge went well", no UU file, two added files ... among main's changes), then `git -c core.hooksPath=/dev/null commit -q --no-verify -m "..."`; the new commit id differs from c4bf86005a (the committer date differs), its tree does not; use `git diff --cached <new id>`.
PROBLEM: Rule 8 and Rule 2. One sentence of about 90 words carries three commands, their expected output and two facts about the result.
FIX: Numbered steps: "1. `git -C ~/workspace/tron worktree add --detach ~/workspace/ai-runs/tron-split-probe-pr4ref 0a5334ccb6`. 2. In it: `git -c rerere.enabled=false merge --no-commit --no-ff 72308ec90c...`. Expected: 'Automatic merge went well', no UU file, the two added files doc/rinzler/qwen-protocol.md and h/tron/models/expert_matmul_dispatch.hpp among main's changes. 3. `git -c core.hooksPath=/dev/null commit -q --no-verify -m \"...\"`. The new commit id differs from c4bf86005a (the committer date differs). Its tree is the same. Use `git diff --cached <new id>`."

### [95] plain-english | Step 6 edit 6 (line 286)
QUOTE: At the time of writing both hold for PR3_COMMIT = dfafd13dce: the PR-3 session checked that commit out in tron-pr3 for its review-fix check and rebuilt t_llama_unit only, so runtron.pr3 is still the 80bce9a08d build; dfafd13dce differs from 80bce9a08d in t/t_llama_unit.cpp only (+19/-6), so runtron's code is the same.
PROBLEM: Rule 8 and Rule 2. One sentence with two "so" conclusions and a semicolon; the same facts are repeated at lines 77 and 159.
FIX: "At the time of writing both hold for PR3_COMMIT = dfafd13dce. The PR-3 session checked that commit out in tron-pr3 for its review-fix check. It rebuilt t_llama_unit only. So runtron.pr3 is still the 80bce9a08d build. dfafd13dce differs from 80bce9a08d in t/t_llama_unit.cpp only (+19/-6 lines). So runtron's code is the same." Keep the explanation once (here) and cite it from lines 77 and 159.

### [96] plain-english | Step 6 table, M2 row (line 309)
QUOTE: Expected by reading: Catch2 runs the leaf sections in order; the one-thread section's pre_save, check, check_marks and check_blocks(false) pass, nothing is queued, convert_pending_k_blocks converts nothing, and `check_blocks(true)` fails at its first REQUIRE (...), 0x8 against the expected 0x9); the hardware-attention section fails at the second check_blocks(false) (...); the "another operation" section and the three-thread section fail at the same REQUIRE line.
PROBLEM: Rule 8. A 74-word sentence with three semicolon-joined parts, each with its own list; the executor must compare the run against it.
FIX: Sub-bullets, one per section: "- Catch2 runs the leaf sections in order. - One-thread section: pre_save, check, check_marks and check_blocks(false) pass. Nothing is queued. convert_pending_k_blocks converts nothing. check_blocks(true) fails at its first REQUIRE (...): 0x8 (block 3 only) against the expected 0x9 (blocks 0 and 3). - Hardware-attention section: fails at the second check_blocks(false), 0x9 against 0x8 (the mutant records and converts the hardware-scored operation's block). - The 'another operation' section and the three-thread section fail at the same REQUIRE line."

### [97] plain-english | 5.3 The cost-row refresh (line 401)
QUOTE: The bench reads the ctest manifest of gen/ (the native preset's build tree), runs each test at widths 1, 2 and 4 with `--benchmark-samples=2` (the ctest command; t_llama_unit holds one benchmark section, so its row includes it, as every earlier row did), places instance 0 of every width on socket 0 (so it is whole-machine work), skips calibration on --update, and rewrites only the four selected rows of the granite_rapids_6962p block.
PROBLEM: Rule 8. A 71-word sentence with five verbs and two "so" clauses inside parentheses.
FIX: "The bench reads the ctest manifest of gen/ (the native preset's build tree). It runs each test at widths 1, 2 and 4 with `--benchmark-samples=2`. t_llama_unit holds one benchmark section, so its row includes it, as every earlier row did. The bench places instance 0 of every width on socket 0; so it is whole-machine work. On --update it skips calibration. It rewrites only the four selected rows of the granite_rapids_6962p block."

### [98] plain-english | 5.3 The schedule, option (a) (line 404)
QUOTE: on D+1 one whole-machine session: the chain's WHOLE_MACHINE_ONLY run with START_NOT_BEFORE=<D+1>T13:00:00Z and END_BY=<D+2>T01:30:00Z takes the marker about 13:25, runs D, E, C and the bench, and releases about 15:40; W, launched the same evening with NOT_BEFORE=<D+1>T13:00:00Z, waits on the lease and then on the hand-off marker, starts its first pass about 15:52, and ends about 00:15 UTC on D+2 (slack before DRIVER_END_BY about 1 h 50 min).
PROBLEM: Rule 8. A 107-word sentence that holds a timeline of six events for two processes; "D" here is the day and "D, E, C" are steps in the same sentence.
FIX: "Option (a), day D evening: run the our-half chain with the two deb builds next to serving (75 min measured basis, 121 min README basis). Launch by 22:00 UTC; then every step starts before the 02:10 hold. Day D+1, one whole-machine session: the chain's WHOLE_MACHINE_ONLY run with START_NOT_BEFORE=<D+1>T13:00:00Z and END_BY=<D+2>T01:30:00Z. It takes the marker about 13:25 UTC, runs steps D, E, C and the bench, and releases about 15:40 UTC. W is launched the same evening with NOT_BEFORE=<D+1>T13:00:00Z. It waits on the lease and then on the hand-off marker. It starts its first pass about 15:52 UTC and ends about 00:15 UTC on day D+2 (spare time before DRIVER_END_BY about 1 h 50 min)." Continue the remaining two sentences unchanged.

### [99] plain-english | 5.5 (line 429)
QUOTE: In decode a run of one token now stores 4 whole lines into the row-major tail block instead of 64 scattered dwords, the block whose 16th row a pass saves is converted at the forward end (one 4 KiB copy per block, KV head and layer, once per 16 steps per user), and the page being filled takes the software loop (the reader for its converted blocks, the dotters for the tail) instead of the AMX kernel until all its blocks are converted.
PROBLEM: Rule 8. A 83-word sentence with three coordinated claims and three subordinate clauses.
FIX: "In decode a run of one token now stores 4 whole lines into the row-major tail block instead of 64 scattered dwords. The block whose 16th row a pass saves is converted at the forward end (one 4 KiB copy per block, KV head and layer, once per 16 steps per user). The page being filled uses the software loop (the reader for its converted blocks, the dotters for the tail) instead of the AMX kernel until all its blocks are converted."

### [100] plain-english | 8. Traps (line 486)
QUOTE: Do not take "theirs": it would drop PR-3's second window, its check_window checks, the cut-only-at-a-change loop and the late helper with the finished count read at return, which PR-3's reviews added.
PROBLEM: Rule 8. A list of four items followed by a relative clause; the next sentence has the same shape.
FIX: "Do not take 'theirs'. It would drop PR-3's second window, its check_window checks, the cut-only-at-a-change loop and the late helper with the finished count read at return. PR-3's reviews added those. Do not take 'ours' alone. It would drop the patch's two hardware-attention sections and its block checks (check_blocks before and after the conversion, check_marks, pre_save). The forward-end conversion of a shared save would then be untested. resolve.py keeps both."

### [101] plain-english | Step 5.3 (line 275)
QUOTE: Apply what the review finds through the script: add `edit` or `editf` lines to exec/pr4-<date>/build-branch.sh, or change the message files, then re-run the script from a clean worktree and re-run step 4. PR-4 is three commits when the chain starts and four when it opens (section 3): no `commit --amend`, no fixup commit before the push. [...] Record the findings, the fixes and the commit ids in split-status.md.
PROBLEM: Rule 7. One paragraph carries seven separate instructions (apply through the script, no amend, script for unpublished work only, repair after the push, the merge-base check, update the file counts, record).
FIX: One bullet per instruction: "- Apply what the review finds through the script: ... - No `commit --amend` and no fixup commit before the push; PR-4 is three commits when the chain starts and four when it opens (section 3). - The script resets the branch, so it is for unpublished work only: after the first push (step 7) never run it on the branch again. - A repair after the push is one focused commit appended on the published head; a merge of PR-3 (step 8) is a merge commit. - Before every later push, `git merge-base --is-ancestor origin/jhan-vnnik-4-tail-block HEAD` must succeed (section 9 forbids a force-push). - If a fix adds a file, update the file counts (12 files in section 3 and step 3; 10 C++ files in step 4.2 and step 6 F) and the fill-body assertions that read them. - Record the findings, the fixes and the commit ids in split-status.md."

### [102] plain-english | Intro paragraph (line 3), Step 1.4 closing paragraph (line 210), Step 3 rules (line 242), Step 7.3 (line 355), 5.1 (line 371)
QUOTE: Written 2026-10-12 about 18:00 UTC by Claude for the agent that creates PR-4, the last PR of the stack. This file is the PR-4 part of split-handoff.md (same folder), with every decision resolved and with the state of PR-1, PR-2 and PR-3 included. Read split-handoff.md only for the description of the whole stack. [...]
PROBLEM: Rule 7. Each of these paragraphs carries four to seven separate points (line 3: author and date, what the file is, two reading instructions, the companion list; line 210: five facts about the diff; line 242: six commit-message rules; line 355: the label rule, the record, the expected checks, the Lint failure path; line 371: the cells, the pass rule, what each cell instantiates, the limits, the false-error case).
FIX: Split each into bullets, one point per bullet; for line 242 a list "Commit rules" with six items.

