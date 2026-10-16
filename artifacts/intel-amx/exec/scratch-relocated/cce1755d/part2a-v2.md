## 5. Checks in detail

### 5.1 Syntax matrix (claude-box)

- Cells: trees gen (AMX dispatch on) and gen-amxoff (off), option off and on, files t/t_llama_unit.cpp, t/t_k_vnni_layout.cpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, t/heterogeneous_scheduler_compile.cpp, plus src/tron/kernels/amx_attn.cpp in gen.
- A cell passes only when the compiler's exit status is 0 and the log has no "error:" line. Warnings do not fail a cell (step 4.1 says which two cells carry warnings).
- The t_llama_unit cell instantiates model.hpp, kv_cache.hpp and self_attention.hpp (the tail block, the policy, the dense gate) in every configuration. The t_k_vnni_layout cell instantiates the five tail-block cases.
- The 38-cell variant adds scheduler/full.cpp (the staging change), gof.cpp, t_gof_dma and t_kv_oom_subcases.
- Limits: syntax and template instantiation only; no link, no generated model translation units, no runtime, no CMake configure.
- If main changed a generated header after the mirror's date (Words), a false error is possible, so compare error sets before and after your change. The probe's matrices on the resolved tree (handoff-material/probe-pr4/out-22, out-38) are the comparison.

### 5.2 Symbols that must be present in PR-4, and the ones that must be absent

- Scope: run every list below over the added lines of `git diff jhan-vnnik-3-shared-save HEAD` and over the trees h/, src/, t/, ingest/src, ingest/test and the files README.ci.md and CMakePresets.json.
- Present (the probe's file lists; "defines" names the file with the definition):
  - h/tron/tensor/k_vnni.hpp defines k_vnni::PANEL_ROWS_4, k_vnni::BLOCKS_PER_PAGE_MASK_0XF, k_vnni::block_bit, k_vnni::offset_bit, Note [Row-major tail block], row_major_row, store_row_major, load_row_major, block_to_vnni, block_to_rows, and includes <cstring>;
  - h/tron/models/kv_cache.hpp defines book::eagle_view_active, page::k_vnni_blocks, page::k_storage_ref, page::k_storage_of, page::note_k_row_saved (a template and a uniform-geometry overload), page::note_k_block_saved, page::k_block_to_vnni, page::k_block_to_vnni_at, page::k_row_if_row_major, the four-parameter set_k_block, the layout branches of set_k_row and get_k_row, k_forget_row (called by clear_kv_complete_at), k_rows_saved_, k_vnni_blocks_, k_state_ix, k_block_bits, k_block_is_vnni, k_with_storage_geometry, k_storage_readable, EAGLE_STORAGE_SLOTS_1, BLOCK_COMPLETED_FALSE, CONVERTED_FALSE, CONVERTED_TRUE, copy_storage_slot with a k_storage_ref as its first parameter (the pair replaces the kv_storage_offset argument; its two callers copy_from and the EAGLE copy build the pair), Note [Row-major blocks under hardware attention], and the state paragraph and the six consumer items of Note [K VNNI storage];
  - h/tron/models/model.hpp defines pending_k_block, pending_k_blocks_, convert_pending_k_blocks (called at the forward end after wait_for_coop_gof), the `n < k_store_block` branch and the TRON_ASSERT on `present` in store_k_block, the note_k_block_saved call, and the policy block `if (!cached_operation_uses_hw(binding.operation))` with the note_k_row_saved call and the push_back in save_k_impl;
  - h/tron/models/self_attention.hpp defines k_layout_dense (the dense gate) and uses k_vnni_blocks, BLOCKS_PER_PAGE_MASK_0XF, block_bit, offset_bit and row_major_row (the dotter's row) in the software loop;
  - h/tron/scheduler/full.hpp calls k_row_if_row_major in the k_head_fn of the staging;
  - h/tron/kernels/k_vnni.hpp and h/tron/kernels/amx_attn_iface.hpp reference Note [Row-major tail block];
  - t/t_k_vnni_layout.cpp has the five cases "row-major tail block converts to the VNNI layout and back, bit for bit", "page K blocks turn VNNI at the 16th saved row and back when a row is forgotten", "the EAGLE storage view keeps its own K layout state", "forgetting a row acts on every slot's own block" and "page append carries the K layout state with the rows" (10 cases in the binary); t/t_llama_unit.cpp has the `#ifdef TRON_K_VNNI` K-instance block of check_page_range_reductions and the two SECTIONs "hardware attention scores the operation: the completed block stays row-major, the whole-block save is still VNNI" and "hardware attention scores another operation: this one still converts"; t/t_amx_dispatch_dtype.cpp records rows through note_k_row_saved and k_block_to_vnni;
  - CMakePresets.json: "TRON_K_VNNI": "ON" once, in the deb preset; README.ci.md: the deb paragraph once.
- Absent: save_k_helper (0 matches anywhere, generated plugins included); k_scatter_run_len (0); the five-parameter set_k_block (`__mmask16 present` occurs exactly twice: store_block's parameter and store_k_block's local); the PR-1-only text (PR-2 removed it; it must not reappear): "temporary until", "Temporary until", "Until the VNNI AMX kernel", "No AMX visit can occur", "not taken until", "the layout-specific reader allowed", "That kernel is not part of this change", "requires TRON_AMX_DISPATCH" (0 matches in the probe; 4 in the reference merge, which are the D2 lines). "and the AMX tile rows" is present (t/t_llama_unit.cpp, restored by PR-2) and must stay.
- main itself uses worker_ix, n_workers and "main helpers" in several files; those are PR-3's and main's, not PR-4's. The whole-tree grep for row_major has matches in unrelated files (the row-major K layout of main); check the added lines and the listed files.

### 5.4 Pass criteria

- Unit tests: every binary passes in the VNNI build, the row-major build and the A3 build (where t_amx_numerics and t_amx_dispatch_dtype are placeholders, recorded as such). t_k_vnni_layout reports 10 test cases in every build (PR-3's 5 plus the 5 tail-block cases; the ones that work on an owner run whatever the option, the page-state ones take the row-major branch with the option off: record the counts). The identity case of t_amx_numerics executed on AMX in the VNNI and the row-major builds. Both mutation checks failed their case and the restored binaries passed. Expected counts: step 6, rows A, A3 and B (derived from the records; record what is measured).
- Smokes, per cell (arms: new = PR-4 with the option on, new2 = its A/A run, newoff = new with the kill switch, head = PR-3's binary with the option on, base = main at 72308ec90c):
  - every arm of the cell exited with rc 0 and produced exactly 256 generated tokens (the validator); a shorter or missing token file fails the cell, whatever the script's verdict says;
  - every cell: new vs new2 identical (256 of 256 tokens), or the cell is a finding;
  - CPU attention, prompt 1024 and prompt 8192: new vs base identical (256 of 256 tokens). This is the claim of the PR. With the tail block, the dotter scores the blocks a decode step completes until the forward end converts them. A converted block holds the same values. In the measured cells the generated tokens therefore equal main's. Basis: the 2026-10-09 precheck of the T tree against main be0d5565b3 (exec/results/merge4737-precheck/smoke: identical at both prompt lengths, 256 of 256; the PR-3 state differed at token 52 at prompt 1024). The same cells at main 72308ec90c (PR-3's record: the PR-3 state differs from base at token 83 at prompt 1024, identical at 8192) have not been measured with the T content. A difference is a finding: record the first differing token and both ids, report, and stop before opening the PR. split-plan.md U1.5 says why identity is not general: a converted block of a partial page is scored by the reader, whose fp32 add order differs from the dotter's; the claim is for the measured cells only;
  - CPU attention, prompt 1024: new vs head expected to differ at generated token 83 (head differs from base there, and new equals base); at prompt 8192 identical. Report the measured tokens;
  - FPGA attention, prompt 1024: new vs head identical (256 of 256 tokens): the tail block changes no FPGA-scored token (the 2026-10-09 precheck: the T tree equals the tree without T under FPGA attention). A difference is a finding: report and stop before opening the PR. new vs base and head vs base: expected first difference at generated token 83 (PR-1's reader on the CPU-scored share; PR-3's record), with the same ids;
  - newoff vs new: expected identical in every cell. Basis: the 2026-10-09 precheck (the kill-switch arm of the T tree identical to its AMX-on arm at CPU prompt 1024, 256 of 256) and PR-3's record at prompt 8192 and FPGA prompt 1024. PR-2's and PR-3's records show a difference at token 247 at CPU prompt 1024 for their binaries (an exact tie of the top-2 scores decided by the AMX-versus-reader numerics); with the tail block the scored sequence of that cell changes, so the tie is not expected to recur, but a near tie elsewhere is possible. A difference is a finding: record the first differing token and both ids, report, and stop before opening the PR unless jhan accepts it (PR-2's forced-run check, exec/pr2-20261011/probe247.sh, is the tool that shows a tie);
  - any difference not listed above is a finding. These are expectations from records at other heads, not guarantees; report what is measured.
- Host suite: the known exceptions are t_proxy_lib skipped and t_proxy_llama31 failed (both for the missing Python virtual environment t/proxy/.venv; PR-1 to PR-3: 93 passed, 1 skipped, 1 failed) and, with serving up, 6 heap_setup failures. Anything else is a finding.
- Cells: report TPS and TTFT with the band and the paired t. No claim without n >= 3. A runtron run that aborts with "save_k: the K store window did not close" (the join watchdog) or with a TRON_ASSERT of the tail block ("store_k_block: a run of 16 tokens must cover its block" or any assert of kv_cache.hpp) is a RUN-FAILED record and a finding: report and stop before opening.
- Campaign W: every tag has a perf.json; the per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state) all ok; the marker file exec/results/pr4ci-<date>/.done exists (not .done-with-failures and not .done-aborted; campaign.sh:507-508, :266, :272), and outcome.txt reads `incomplete passes: none; stop reason: none; problems: none; known systematic failures: none` (campaign.sh:504; the word done never appears in outcome.txt, it appears in .status and status-history.log; the 2026-10-09 record exec/results/pr4424ci-20261009/outcome.txt has this line); summary.md has 14 full-pass rows and the sw8k row with n = 2 passes each and a complete pass pair per cell. A run that ends with .done-with-failures but an all-none outcome.txt had one pass repeated after a first failed driver run and the repeat succeeded (status-history.log: "repeating the run once" then "repeat ok"): report it as a finding with the tag and the first run's <tag>-failed1 folder, not as a clean pass. A cell that failed in both runs of a pass is a finding (the campaign repeats a failed driver once). A pass skipped for "not enough time before DRIVER_END_BY" (option (a) with a late release, section 5.3) is re-run on day D+2 with PASS_TAGS and reported as such. The restore at the end reinstalled restore.deb and started serving (dut.sh installed shows the restore version; the units active).
- Cost rows: `bin/slice bench --check` passes on the refreshed config/test-benchmarks.json; the diff touches only the granite_rapids_6962p rows of the four tests (and whatever the bench rewrites by design: section 5.3 says which); the row of t_k_vnni_layout exists under granite_rapids_6962p; genoa96 rows are not required (PR-1's open item).

## 6. The body of PR-4

Rules (jhan's, as recorded for PR-1 to PR-3):

- Present tense, written as of the day. No change history, no review-round narration, no "before/after".
- Measurements keep provenance only (commit id + date). Comparators: the base inside PR-1 (72308ec90c) as runtron and as the base deb, PR-3's head and its kill-switch run. PR-3's binary is the parent of the stack, not a previous head of this PR, so the rule "no previous-head comparator" allows it. No comparator measured before the split (the PR 4424 binaries) in the Measurements section; the 2026-09-16, 2026-09-18 and 2026-10-09 records may be cited in the Background as the reason for the design and the expectation, with their dates and arms (deviation 11). No attribution subsection.
- A pending measurement is its own subsection: the question, the comparator, the cells, the verdict rule, the status, the table. Never a sentence inside another section.
- No clock times, no paths into the author's workspace, no comparison with another head's assertion counts in the Verification section. Keep dates, commit ids, build settings, pass/skip results, exact test counts.
- Every term defined at first use (a "Words used here" table as in the PR-3 body; reuse its rows where they apply). One claim per sentence. Numbers with units. Plain English, no idioms. No names of people (roles and links only). Run the plain-english skill in Check mode on the finished body before posting, and a facts-versus-results check (PR-3's body went through one such workflow before posting; split-status.md records it).
- The PR-3 body's stack table describes PR-4 as: "A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the packed layout when all 16 rows are saved. A row-major policy under hardware attention (FPGA attention) addresses issue #4500. The `deb` package-build preset enables the option in the released package." The PR-4 body must agree with that row.
- The PR-3 body's Open items "The masked partial-block path" and "The single-token store of decode steps" say the fourth PR replaces them; the PR-4 body states the result. Its Open item "Cost data of t_k_vnni_layout and t_llama_unit" says the refresh is planned with the fourth PR's cost-row update; the PR-4 body carries that refresh. Its Open item "The join watchdog and the worker cap" still applies (the shared save is unchanged in PR-4) and is carried over. Its Open item "A control difference beyond the band" is PR-3's own newoff vs headoff result (PR-3's binary against PR-2's); the PR-4 body does not restate it, and reports its own newoff vs headoff pairs (PR-4's binary against PR-3's) under Measurements, with a new Open item only if a pair falls beyond the band (section 5.5).
- The PR 4424 body's sentences on the tail block, the forward-end conversion and the hardware-attention policy may be reused where they hold (D6). Its section on the old per-token decode scatter must not be reused as a description of PR-4's store.

Sections, in this order:

1. "## Short version": three sentences.
   - What the store does: a run shorter than a 16-token block is stored row-major into the block's own bytes, 4 lines per token; the block converts to the VNNI layout at the end of the pass that saves its 16th row; under hardware attention the blocks stay row-major; the deb preset turns the layout on.
   - What it changes: the FPGA-attention decode TPS of qwen3-4b against PR-3's binary and against main at tp2 and tp4, the measured numbers; token identity with main in the CPU cells; the whole-machine table's resolved rows.
   - The state: the last PR of the stack; the option is on in the deb preset and off in every other preset.
2. "### Background":
   - The loss of issue #4500 with its records (2026-09-16 runtron: -2.2 % at tp2 and -9.7 % at tp4; 2026-09-18 the nightly's own layout: -5.0 % at tp2 and -11.0 % at tp4, the CI threshold 135 TPS; cite each with date, arms and model).
   - Its cause: 64 lines written per token by the scatter, and the gather of a VNNI row by the FPGA staging for every generated token.
   - The design, in three parts: a block stays row-major until it is complete. The conversion runs at the forward end, after the cooperative staging has drained (wait_for_coop_gof); that gather is the last reader that can hold a block's rows row-major. Under hardware attention no block is converted: the FPGA holds the K of every complete GOF, the CPU scores only the tail above them, so the AMX kernel never reads a block that decode completes there.
   - Why the result is bit-identical: block_to_vnni equals store_row per token; the layout state is recorded by the page.
   - Reuse the fetched PR 4424 body's sentences on these mechanisms where they hold. The 2026-10-09 whole-machine numbers of the T tree may be named as the expectation, with date, arms (the nightly deb 2026.10.08-be0d5565 against the PR 4424 deb) and the resolution rule.
3. "## Words used here": the table. Rows to add to the PR-3 set: row-major tail block, saved-row bits, converted-block bits (k_vnni_blocks), pending block / forward end, block_to_vnni / block_to_rows, row_major_row, k_row_if_row_major, k_forget_row, storage ref / EAGLE view, dense gate, dotter (its new role), hardware-attention policy, hardware attention / software attention (USE_HW_ATTN), GOF and the engagement point, the deb preset and the released package, the nightly and its perf phase, the 14 configs, the sw8k cell, the base deb and the target deb, platformd and the engines, memory (VmHWM, VmRSS, HugetlbPages), the resolution rule of the campaign (|paired t| >= 2.26 and |delta| >= 1 %), rounds, cost rows and `bin/slice bench --update`, the slice check, mutation check (two), the FPGA-attention cells, head and headoff (PR-3's binary arms).
4. "## The changes": by file, mechanism level, one sub-bullet per file.
   - tensor/k_vnni.hpp: Note [Row-major tail block]. row_major_row: token t of block c owns 256 contiguous bytes in panel (t / 4, c). store_row_major and load_row_major. block_to_vnni: the 16 rows copied to a 64-byte-aligned stack array, then store_block with the full mask. block_to_rows: the inverse. The four constants and helpers. store_block is unchanged; its mask parameter stays for the block-save test, and every other caller passes the full mask.
   - kv_cache.hpp: the two bit sets per storage slot, the EAGLE entry. note_k_row_saved's return and when it is true again. note_k_block_saved after the last KV head. k_vnni_blocks. k_storage_ref and k_storage_of, and why the pair is taken at the save. k_block_to_vnni_at: refuses an incomplete or converted block, converts every KV head, then sets the bit. set_k_row and get_k_row follow the block's recorded layout. set_k_block without the mask. k_row_if_row_major for the staging. k_forget_row: drops the bits at and above the offset, converts a block back when it keeps rows below the offset and the storage is readable. The copy semantics: a whole-page copy carries the bits; a token append goes through row-major rows with block_to_rows first and block_to_vnni after. Note [Row-major blocks under hardware attention]. The changed items 1 to 6 of Note [K VNNI storage].
   - model.hpp: store_k_block's rule: a 16-token run takes the block save and note_k_block_saved, a shorter run is stored row by row. The TRON_ASSERT that a 16-token run covers its block. pending_k_block and the queue, main thread only. The policy block after the join. convert_pending_k_blocks at the forward end after wait_for_coop_gof, with a trace event. The reworded item 1 of Note [Shared block save].
   - self_attention.hpp: the dense gate k_layout_dense read after the dense predicate. The software loop fetches the blocks mask and the plane at the first relevant token. A VNNI block's token sets its live bit for the reader; a row-major block's token is scored by the dotters through row_major_row. `live != 0` instead of `relevant_k_tokens > 0`. The dot_q array exists in VNNI builds now.
   - amx_attn_iface.hpp and kernels/k_vnni.hpp: the Note [QK orientation] paragraph on the two store paths; the reader comment's live-bit rule: every block with a live bit holds the VNNI layout.
   - full.hpp: the staging's k_head_fn returns a row-major row in place and gathers a VNNI row into scratch as before.
   - CMakePresets.json and README.ci.md: the deb preset sets TRON_K_VNNI ON next to TRON_AMX_DISPATCH; every other preset leaves it OFF.
   - The tests: the five tail-block cases of t_k_vnni_layout and what each proves; the K-instance block of the apply-and-join case of t_llama_unit, its mixed page 1; the two hardware-attention sections and the block checks of every save_k section; the dispatch test's recorded rows.
   - State that the masked partial-block path of PR-3 is gone from save_k and that store_block's masked branch is reachable from the block-save test only.
5. "## Measurements": three parts, one sub-bullet each, then one subsection per claim.
   - (a) The runtron cells of step 6, row E: the CPU cells (the PR-3 table form: one table of the 5 arms x 3 cells, one table of the 5 pairs x 3 cells) and the FPGA cells (3 arms x 2 cells; the pairs new:base, new:head, head:base), final head against base and against head, with the band and the paired t.
   - Then one subsection per claim of section 5.5: the FPGA-attention decode (new vs base inside the band while head vs base shows the loss; the claim of issue #4500); the CPU cells against PR-3's head (expected inside the band; the measured pairs decide); against main (TPS and TTFT, as PR-3); the kill switch inside PR-4 (newoff vs new); the store under the reader (newoff vs headoff); PR-3 against main in this session (head vs base).
   - (b) The whole-machine campaign W: the 14 configs and the sw8k cell, the base deb (built from 72308ec90c) against the target deb (built from the three-commit head), in the summary.md table form (TPS, TTFT, VmHWM and VmRSS with the resolution rule), the arm order, the number of passes and rounds; a subsection on the resolved rows and one on memory.
   - (c) Token identity: the five-arm table of section 5.4 (new == base in the CPU cells is the claim).
   - If a run is still pending when you post, it is its own subsection in the pending form.
6. "## Verification", one sub-bullet per item:
   - the three builds and their test counts (the PR-3 table form, with t_k_vnni_layout at 10 cases);
   - the kill-switch runs;
   - the two mutation checks (quote the runs' summary lines and the FAILED line; M1 also its captured tok);
   - the two deb builds (versions, the package checks: the TRON_AMX_DISABLE literal, AMX tile instructions, the deb preset's cache variables as make-deb.log prints them);
   - clang-format and the whitespace check (no fourmolu: no Haskell file changes); say that the Haskell suite is not repeated because PR-4 changes no file under ingest/ (the code generator is untouched; it ran on the PR-3 head, 1,363 tests passed, 0 failed, 2026-10-12), and that the generated-plugin check of the third PR was repeated: every one of the 19 generated plugins of the option-on build carries the same save_k call forms and counts as in the third PR (quote the PASS line and the qwen_3_4b row of plugin-calls-pr4.txt). Do not say byte-identical: the chain compares counts, not bytes;
   - lint-notes; the 38-cell matrix (with the two expected warnings of decision D12); the host suite;
   - the cost rows (the command, the date, the host, the four tests, old and new values);
   - then the subsection "### CI coverage", in one-claim sentences: the required CI builds with both switches off. There the tail-block cases that work on an owner still run, the page-state cases take the row-major branch, the save_k sections run the row-major store, and the dense gate is not compiled. The option-on paths run on the Granite Rapids test machine and in the legacy lane. The deb preset now compiles the option into the released package. The required CI therefore tests a configuration the package does not ship. The whole-machine campaign of this PR and the nightly after the merge test the shipped one. The author accepts this limitation for this PR. Issue #4865 tracks the CI change. The draft's checks that ran (Lint with lint-notes, the infrastructure checks, deb-smoke-tests, and the slice check if the cost-row commit triggered it).
7. "## Open items", one sub-bullet per item:
   - the scoring of decode-completed blocks under software attention for a hardware operation (the cost the Note accepts: before the engagement point, a prompt shorter than 128 tokens, a shard without HBM, a raised engagement point: the dotter scores those blocks instead of the AMX kernel, and a score can differ by the add order alone);
   - the forward-end conversion's serial cost on the main thread (every completed block of every layer and KV head, once per 16 decode steps per user; not measured here: the measurement that would decide it is a Perfetto trace of the convert_k_blocks span, the trace event of convert_pending_k_blocks);
   - the storage-view (EAGLE) state is tested by the unit tests only (no EAGLE model is run here);
   - 128-dimension heads with kv_mul other than 4 (as PR-3's item; llama-3.2-3b's -1.4 % in the whole-machine table is the kv_mul 3 item of PR-1);
   - the join watchdog's 120 s and the 128-worker cap (as PR-3's item; the shared save's window protocol, k_join_timeout_s and helper_windows in model.hpp, is unchanged here);
   - the kill switch and issue #4444 (as PR-3's item, with the measured newoff-vs-new tokens and the restored identity with main in the CPU cells);
   - the benchmark-binary mismatch of the legacy lane (inherited);
   - the CI coverage gap (#4865) with the deb-preset side;
   - the campaign's base deb built from the stack's main rather than the nightly's (deviation 4: say what the nightly deb of the day would have measured instead, Insufficient data);
   - PR 4424 as the reference (open until its author closes it).
8. "## The stack": the four PRs, their order, what each adds, and the state of each (PR-1 #4868 ready for review; PR-2 #4887 a draft based on PR-1; PR-3 #4898 a draft based on PR-2; PR-4 this PR, a draft based on PR-3). Say that the stack is complete with this PR, that PR 4424 stays open as the reference until it is closed, and that the option is on in the deb preset of this PR and off in every other preset.
9. The attribution line: "🤖 Generated with [Claude Code](https://claude.com/claude-code)".

## 8. Traps (each cost a session before)

- git on claude-box:
  - git is 2.34 (no `merge-tree --write-tree`, no `cherry-pick -q`).
  - `git rebase` strips commit-message lines that start with `#`. Use merges.
  - Never `git worktree prune` the shared repository from claude-box.
  - After any amend, check `git branch --show-current`.
  - git rerere is active in ~/workspace/tron: apply both patches with `-c rerere.enabled=false`, or a recorded resolution of your own earlier run could apply silently. Read the five files after the apply.
  - lefthook is missing on claude-box: commit with --no-verify and run the checks yourself.
- The conflicts:
  - The t/t_llama_unit.cpp block looks like a code conflict (and is): the T patch extends a section that PR-3 rewrote twice.
  - Do not take "theirs". It would drop PR-3's second window, its check_window checks, the cut-only-at-a-change loop and the late helper with the finished count read at return. PR-3's reviews added those.
  - Do not take "ours" alone. It would drop the patch's two hardware-attention sections and its block checks (check_blocks before and after the conversion, check_marks, pre_save). The forward-end conversion of a shared save would then be untested.
  - resolve.py keeps both.
- `git apply --check` without `--3way` fails on the B patch (README context); `git apply --3way` applies it cleanly. Do not hand-edit the README from the error.
- The glob `/var/tmp/jhan/tron-pr4*` matches tron-pr4424 and tron-pr4424ci (2026-10-09 worktrees) besides tron-pr4, tron-pr4nd, tron-pr4rm, tron-pr4ci-base and tron-pr4ci-target. Name every worktree in full.
- The deb builds:
  - `make deb` runs outside nix with uv 0.9.5 and ghcup on PATH (exec/pr4424ci-20261009/build-target.sh).
  - It must not run while the nightly's perf phase runs (it would disturb the nightly's numbers) and not next to another build of ours.
  - A worktree that is not clean gives a deb version with "-dirty".
  - Both debs are built on local branches (section 5.3's recipe; step 6, row deb), so both versions carry the branch name: 2026.10.<build day>-72308ec9-jhan-pr4ci-base and 2026.10.<build day>-<8 chars>-jhan-pr4ci-target (bin/get-version.sh takes the date part from the build date, not from the commit date). A detached build would get a version string of the nightly's form and trips the stop rule of section 7 ("a deb's Version field lacks the branch name").
  - The string 2026.10.10-72308ec9 is runtron.main1010's version (a detached build of 2026-10-10, exec/results/pr1-E-cpu/rt-results.txt), not a deb version of this handoff. Do not use it as EXPECTED_BASE.
  - Set EXPECTED_BASE to the base deb's exact Version field (`dpkg-deb -f base.deb Version`) and EXPECTED_BASE_SHA to its rinzler sha256, in both launch.sh and campaign.sh. launch.sh:32, save-base-deb (dut.sh:103) and ensure-base (dut.sh:119) compare that field exactly and do not look for "jhan". The preflight's "jhan" refusal (campaign.sh:415) applies to the package installed at preflight (the restore target) only, so a base version that contains "jhan" passes it.
- Campaign W:
  - Importing the real talos package registers a session in the CI results database; the talos stub must be first on PYTHONPATH (configs.py does this).
  - The harness checkout must be at 14f0ce4 with the stash untouched.
  - HF_OFFLINE=1 needs every tokenizer in the local cache (checked 2026-10-08 for all 15 cells; a new model in the harness list would fail).
  - AMX_PROBE=1 sends 4 short requests after provisioning llama-8b and qwen3-4b tp2 before the measured rounds.
  - The campaign's per-pass deadline logic keeps serving down until the restore: never stop it with -9; use SIGTERM and the recovery steps of the README.
  - Never stop W with SIGTERM, and never let its DEADLINE_START pass, while the chain holds the whole machine: W's trap and its abort path run bill-share.sh release, which re-creates Bill's marker (section 5.3, Bill's marker). The option (a) variables (DEADLINE_START 01:35 on day D+2) exist for that reason.
- The chain script:
  - `git diff HEAD^2 HEAD` works for a merge head only; PR-4's head is a plain commit, so diff against the PR-3 head.
  - A `pgrep -f` pattern in the poller matched its own ssh command line once; exclude it (the `chain[.]sh` form on stdin).
  - A `pkill -f` whose pattern carried a script's literal path once killed the ssh session itself.
  - The body's build-time rows were once mapped by file order and two configurations swapped; map by suffix.
  - The Catch2 exit code of a failing run is not the failed-assertion count; quote the summary line.
  - Catch2 3.7.1 omits a summary column whose value is exactly "0" and pads the others.
  - The script runs under `set -u`: a variable renamed in one place and not another (edit 2) aborts the chain at that step.
- NFS:
  - Never edit a script a 3bda process is running (bash re-reads a running script by byte offset); copy to a new name instead; verify cross-host edits on 3bda before building.
  - The cost-row JSON that `bin/slice bench --update` writes on 3bda lives in the /var/tmp worktree (3bda's local disk, not NFS). The chain's bench step saves `git diff -- config/test-benchmarks.json` as exec/results/pr4-<date>/bench-update.diff (NFS), and the (d) mode of build-branch.sh applies that diff on claude-box (step 1.6, step 7.1). Never edit the JSON by hand, and do not copy it by scp or commit it on a scratch branch in the 3bda worktree: the diff is the only transfer.
- Machine:
  - The nightly leaves rinzler@N units running after a failed run, and the scripts' watch_run kills our runtron when a unit is active or the lease is busy.
  - The host suite with serving up fails 6 heap_setup tests (environmental).
  - A campaign and a pre-check must not wait for the same lease event (the chain writes the hand-off marker at launch, edit 15).
  - `make build-test-host` rebuilds gen/runtron in the worktree; the smoke and cell arms must point at the copied runtron.<suffix>, never at gen/runtron.
  - runtron deletes the path given to --intermediates-file before opening it.
- Tests:
  - The identity case of t_amx_numerics returns early with a WARN when AMX is unavailable; check the AMX-on run for the absence of its "AMX unavailable" line.
  - Never fill bf16 test rows with 0x7f80 or higher patterns (NaN, not a number).
  - The tail-block tests use the poison 0xa5a5 and random rows.
  - The page-state cases call note_k_row_saved on a page whose book has a KV slot: a book with logical_slot_count() == 0 exists in other tests; never touch page K state before a token is relevant (the dense gate is read after the dense predicate for that reason).
- Smoke and cell results:
  - The campaign summary's TPS is the mean over the 8 users of the per-request runtron lines (decode only).
  - A smoke's "average tok/s" line is the same metric at 1 user and is not comparable with the 8-user cell TPS.
  - The "[Load]" and "[Iteration]" throughput lines are different metrics; never quote them as TPS.
  - The first line of summary.md and of rt-results.txt carries stale arm names from the sync4424 campaign; the rows and the `# arms:` line are right. Never copy that first line into the body or the record.
  - The arms are base = runtron.main1010 (72308ec90c), head = runtron.pr3 (80bce9a08d), new = runtron.pr4. Check the arms' sha256 lines near the top of rt-results.txt.
  - smoke.sh's verdict compares the common prefix of two token sequences only and ignores the exit codes (step 6, row D has the validator).
  - campaign.sh runs the arms of ARMS, but summarize.py tabulates the arms of WEDPERF_ARMS and the pairs of WEDPERF_PAIRS; set all three, per campaign invocation.
  - The FPGA cells' TPS levels are about 125 TPS at tp2 (the 2026-09-24 record exec/results/i4587-E-fpga) and about 130 to 150 TPS at tp4 (issue #4500), not the CPU cells' 80 to 120 TPS: do not compare across attention modes.
- Comments: the patch's comment text mentions no PR; keep it that way (section 4, step 5). The two "until" sentences of the added lines are mechanism, not narration.

## 9. Do not

- Do not push to jhan-amx-vnniK, jhan-vnnik-1-layout, jhan-vnnik-2-amx or jhan-vnnik-3-shared-save. Do not force-push anything. Do not close PR 4424. Do not push the probe branches, the tag or the reference merge.
- Do not rebase jhan-vnnik-4-tail-block; merges only.
- Do not run build-branch.sh on the branch after the first push (its (d) mode runs before the push).
- Do not merge origin/main into jhan-vnnik-4-tail-block while PR-3 is open: main enters the stack through PR-1 only, or the PR-4 diff on GitHub would show main's commits.
- Do not add "Run CI". Do not remove "Skip benchmarks". Do not mark PR-4 ready for review until PR-3 has merged and jhan says so.
- Do not change nix/cmake-tron-test-build.nix (D8 is option c; #4865 tracks the CI change).
- Do not edit the bodies of PR-1 to PR-3, and do not reply on PR #4868, #4887 or #4898; those are the earlier sessions' and jhan's.
- Do not restore the masked partial-block path, and do not remove store_block's mask parameter (the block-save test uses it).
- Do not guard, move or delete AMX_AVAILABLE_FALSE and RECORD_ROWS_FALSE in t/t_amx_dispatch_dtype.cpp to silence the AMX-off warnings; report them and leave the decision to jhan (decision D12).
- Do not apply the standing protected-section wording proposal of PR 4424 anywhere (D6).
- Do not use the nightly deb of the day as the base of campaign W unless jhan rejects deviation 4.
- Do not run `make deb` or any build during the nightly's lease, and do not run two builds of ours at once on our half.
- Do not touch /var/tmp/jhan/tron-pr4424ci, /var/tmp/jhan/tron-pr4424 or /var/tmp/jhan/pr4424ci-20261009/.
- Do not stop W, and do not let its DEADLINE_START pass, while the chain holds the whole machine (section 5.3, Bill's marker).
- Do not post to Slack or GitHub comments in jhan's name. Do not name people in the body.
- Do not create files or folders at the top level of ~/workspace. Worktrees go under ~/workspace/ai-runs/, results under ~/workspace/intel-AMX/exec/results/.
- Do not promote PR-2, PR-3 or PR-4; only jhan decides a promotion, after the parent merges.
