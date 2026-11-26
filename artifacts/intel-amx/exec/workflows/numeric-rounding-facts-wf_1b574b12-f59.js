export const meta = {
  name: 'numeric-rounding-facts',
  description: 'Six read-only readers collect facts for the numeric-rounding handoff and the update of the GDN split handoff',
  phases: [{ title: 'Read', detail: 'six independent fact readers, each writes one report file' }],
}

const OUT = '/home/jhan/workspace/smaller-tasks/numeric-rounding/handoff-material'

const COMMON = `
You are a fact reader. Another agent will write two handoff files from your report, so your report must hold exact, checkable facts.

## Setting
- Repository: positron-ai/tron (C++ inference program). Shared local clone: /home/jhan/workspace/tron. It was fetched today (2026-11-23). Do NOT fetch, checkout, switch, commit, stash, gc or prune in it, and never run "git worktree prune". Use read-only git commands with "git -C /home/jhan/workspace/tron ..." (a plain "cd" prints a directory listing in this shell).
- Our work: an AMX speed-up of the GatedDeltaNet (GDN) layer of the model Qwen3.5 4B. Local worktree (read only, do not change it): /home/jhan/workspace/ai-runs/tron-gdn-amx at 882e5322f1. Our three commits on top of 72e1191804:
  - 0d69ef3ce8 = counters for GDN (gdn_stats.hpp)
  - 775bba7661 = "Part 0" (AVX-512 chain kernel gdn_recurrence_chain, bit-identical to the token kernel gdn_recurrence) plus "Part A" (AMX block kernel, src/tron/kernels/amx_gdn.cpp, h/tron/kernels/amx_gdn_iface.hpp, t/t_amx_gdn_numerics.cpp)
  - 882e5322f1 = "Part B" (AMX attention kernels for 256-wide heads)
- Commit ids to use (all present in the local clone):
  - main today: origin/main = f454423b09
  - the model's branch (head of PR #3696, "Register Qwen3.5 4B", open): origin/rbjarnason/qwen35-native-4b-registry = 72e1191804
  - PR #3221 (open, "Parallelize GatedDeltaNet operations across key-head groups"): origin/rbjarnason/qwen35-37-gdn-head-parallel = 127a662083 (= main + 4 commits)
  - PR #5571 (draft, "Keep the GatedDeltaNet layer's intermediate values in FP32"): origin/rbjarnason/qwen35-gdn-fp32-intermediates = 69cc70fae0 (two commits on 127a662083: 59429b0955 and 69cc70fae0)
  - PR #5022 (ours, AMX attention kv_mul 16): origin/jhan-amx-kvmul16 = ddf843ad97
- Issue #5433 ("GatedDeltaNet kernels: measure what matching PyTorch's rounding costs, then decide whether to drop it") and draft PR #5571 belong to the owner of the GDN code. Issue #4444 ("AMX and VNNI attention: token divergence against the row-major binary, and the kill-switch rollback contract") is ours.
- GitHub: use "gh ... --repo positron-ai/tron" for READING only (gh issue view, gh pr view, gh pr diff, gh api GET). Never comment, edit, label, close or create anything on GitHub.
- Do not use ssh. Do not build anything. Do not use more than 6 CPU threads. Temporary files go under the directory given in your task, nowhere else.
- Known facts you need not re-derive: PR #5571 removes 14 of 22 bf16 rounding calls in the GDN host code (convolution sum and SiLU result; the seven points of normalize_gdn; the result of the sigmoid in gdn_beta; the value input of the recurrence; three of five in the executor's postprocess). Issue #5433 says six of the seven normalization roundings are removed whatever the measurement says. Our AMX block kernel packs the normalized key and query with bf16_bits(), which keeps the upper 16 bits of each FP32 value and so assumes that those values are already representable in bf16 (src/tron/kernels/amx_gdn.cpp near lines 181-262, h/tron/kernels/amx_gdn_iface.hpp near lines 47-55 and 125-135 at 882e5322f1).

## Report rules
- Write your report as Markdown to the file named in your task. Start with "## Short version" (at most three sentences), then the sections your task lists.
- Every claim carries its evidence: file:line at a named commit id, a command with its output, or a GitHub URL. Quote the decisive lines of code (short quotes).
- Where you could not verify something, write "Not verified" and name the command or measurement that would settle it. Do not guess. Mark estimates "est.".
- Plain English: short sentences, one claim per sentence, define a code name at first use, numbers with units. No names of people: write roles (the GDN owner, the author) and PR or issue numbers.
- Your final message is read by a program, not a person. Return at most 250 words: the path of the report, then the decision-changing facts as a list.
`

const TASKS = [
  {
    key: 'stack',
    file: `${OUT}/facts-stack.md`,
    prompt: `
## Your task: map the Qwen3.5 PR stack and the bases our work can use
Write the report to ${OUT}/facts-stack.md. Temporary files: none needed.

Answer these, each in its own section:
1. **The stack today.** List every open PR whose head branch starts with "rbjarnason/qwen35" (gh pr list --repo positron-ai/tron --state open --limit 200 --json number,title,baseRefName,headRefName,headRefOid,isDraft,reviewDecision,updatedAt, then filter), and the PRs of that family merged since 2026-11-15 (gh pr list --state merged --search ...). Order the open ones as a chain from main upward by base -> head. Mark PR #3221, PR #5571 and PR #3696 in the chain. How many open PRs sit between main and PR #3696? Which is the lowest open PR (the next to merge)?
2. **Is the model's branch stale against main?** List the 21 commits of "git log origin/main..72e1191804" (subject, id). For each, say whether main holds a squash-merged commit of the same change (match by PR number in the subject or by subject), and give that main commit id and date. Say how many of the 21 are in that state.
3. **GDN files: main against the model's branch.** For h/tron/kernels/gated_delta_net.hpp, h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_prepared_operation.hpp, t/t_gated_delta_net.cpp, h/tron/models/model.hpp and ingest/src/TronCpp.hs: give "git diff --numstat 72e1191804 origin/main -- <file>" and describe in two to five sentences what main has that the model's branch lacks, and what the model's branch has that main lacks. Name functions and types. Note that h/tron/models/gdn_execution.hpp exists at 72e1191804 and not on main; say what it holds (its role in 3 sentences) and which PR of the stack adds it (find the commit with git log 72e1191804 -- h/tron/models/gdn_execution.hpp and look for the open PR whose head contains it).
4. **PR #3221 against the model's branch.** Does 72e1191804 already contain an older version of the key-head-group parallelism of PR #3221? Compare h/tron/models/gdn_rolling_executor.hpp (and gdn_execution.hpp if present) at 72e1191804 and at 127a662083: which entry points does the executor offer at each commit (names and signatures of the functions that advance a token or a chain of tokens, the work-item type, how key-head groups are split over threads)? Does 127a662083 hold h/tron/models/gdn_execution.hpp? State concretely what "changes how the kernel is driven" means for code that calls gdn_recurrence: which call sites and which template parameters or arguments differ between main (f454423b09), 127a662083 and 72e1191804.
5. **What our commits need that main lacks.** For commit 0d69ef3ce8 and for commit 775bba7661 (git show --stat, git show <id> -- <file>): list each touched file, whether it exists on main, and whether the lines our hunk changes exist on main in the same form (check by searching main's file for two or three context lines of each hunk). Give a per-file verdict: "applies to main as is", "needs a port (reason)", or "no target on main (reason)". Do the same against 127a662083.
6. **Summary table**: three candidate bases for our GDN PRs (main f454423b09; PR #3221 head 127a662083; the model's branch 72e1191804) with, for each: which of our parts (counters, Part 0, Part A) can sit on it without code that is absent from that base, and whether Qwen3.5 4B can be run end to end from that base (is the model registered there: look for qwen_3p5_4b or "qwen-3.5-4b" in config/models.yaml and for the plugin sources at that commit).
`,
  },
  {
    key: 'port',
    file: `${OUT}/facts-port.md`,
    prompt: `
## Your task: trial applications of our commits and of PR #5571 (in a scratch clone)
Write the report to ${OUT}/facts-port.md.
Scratch directory (create it; use only it): /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/port-trials

Make a scratch clone that shares objects and cannot change the shared repository:
  git clone --shared --no-checkout /home/jhan/workspace/tron <scratch>/tron-trial
Inside the clone only: set user.name "trial" and user.email "trial@example.invalid", and commit with --no-verify. All the commit ids listed in the setting are reachable through the shared object store (check with git cat-file -t <id>; if one is missing, say so and continue with the others). Never push. Never touch /home/jhan/workspace/tron or /home/jhan/workspace/ai-runs/tron-gdn-amx.
The git version here is 2.34.1 (no "merge-tree --write-tree"), so run real cherry-picks in the clone, one trial branch per trial, and "git cherry-pick --abort" or reset between trials.

Trials (for each: the exact commands, exit status, the list of conflicted files from "git status --porcelain", the number of conflict regions per file counted by the "<<<<<<<" markers, files reported as "deleted by us"/"deleted by them"/"added by them", and two sentences on what the conflicts are about):
- T1: on f454423b09 (main): cherry-pick 0d69ef3ce8, then (after recording, resolve nothing; start again from a clean checkout) cherry-pick 775bba7661 alone, then 0d69ef3ce8 followed by 775bba7661 where the first applies.
- T2: the same on 127a662083 (head of PR #3221).
- T3: the same on 69cc70fae0 (head of PR #5571).
- T4: on 775bba7661 (our Part 0 + Part A commit, whose parent chain is 72e1191804 -> 0d69ef3ce8 -> 775bba7661): cherry-pick 59429b0955 (the code commit of PR #5571), then 69cc70fae0. This shows where the removal of the roundings meets our chain kernel, our AMX block kernel and our tests. For every conflict region in h/tron/kernels/gated_delta_net.hpp and h/tron/models/gdn_rolling_executor.hpp quote the two sides (up to 15 lines each).
- T5: also for T4, after the cherry-pick stops, list the places in OUR code that PR #5571's change does NOT touch but that repeat a rounding which PR #5571 removes from the token kernel. Search our versions (git show 775bba7661:h/tron/kernels/gated_delta_net.hpp, git show 775bba7661:h/tron/models/gdn_rolling_executor.hpp, src/tron/kernels/amx_gdn.cpp, t/t_amx_gdn_numerics.cpp, t/t_gated_delta_net.cpp) for round_to<bf16>, round_chunk_to<bf16>, bf16_bits and "representable". Give file:line and the code line. These places would stay rounded while the token kernel stops rounding, so the chain kernel would stop being bit-identical to the token kernel.
- T6: on 72e1191804 (the model's branch): cherry-pick 59429b0955 alone. Does PR #5571's change apply to the model's branch? List conflicts. This tells whether a measurement build "model's branch + PR #5571" is cheap to make.
End with a table: trial, base, commit(s), result (clean / N files with M conflict regions / no target file).
Remove nothing from the scratch directory at the end; the next agent may look at it.
`,
  },
  {
    key: 'rounding',
    file: `${OUT}/facts-rounding.md`,
    prompt: `
## Your task: the rounding map of the GDN host code, and which roundings our kernels depend on
Write the report to ${OUT}/facts-rounding.md. Temporary files: none needed.

Read with "git -C /home/jhan/workspace/tron show <commit>:<path>" and number lines with "| cat -n" or "grep -n".
1. **The 22 rounding calls.** At 127a662083 (head of PR #3221) find every call of round_to<bf16> and round_chunk_to<bf16> in h/tron/kernels/gated_delta_net.hpp, h/tron/models/gdn_rolling_executor.hpp and h/tron/models/gdn_prepared_operation.hpp. Issue #5433 counts 22: 4 in the convolution, 11 in the recurrence, 2 at load, 5 in the executor. Make a table with one row per call: number, file:line at 127a662083, function, what value is rounded, whether PR #5571 (69cc70fae0) removes it (yes/no; check with git diff 127a662083 69cc70fae0), whether it is one of the six normalization roundings that issue #5433 says are removed whatever the measurement says (read the issue: gh issue view 5433 --repo positron-ai/tron --comments), and the line of the same call at 72e1191804 (the base of our commits) and at main f454423b09 (or "absent"). If your count differs from 22, show the difference.
2. **Our chain kernel (Part 0).** In our version of h/tron/kernels/gated_delta_net.hpp (git show 775bba7661:h/tron/kernels/gated_delta_net.hpp, Note [GatedDeltaNet chain recurrence] and the functions after it; the worktree /home/jhan/workspace/ai-runs/tron-gdn-amx holds the same file at 882e5322f1): list every place where the chain code rounds or calls a function that rounds (normalize_gdn, gdn_beta, gdn_decay, round_chunk_to<bf16> on the value, and so on), with file:line and one sentence on which rounding of your table it repeats or reuses. Say for each whether it calls the SAME function as the token kernel (then PR #5571's change reaches it automatically) or holds its OWN copy of the rounding (then it must be changed by hand to stay bit-identical). Also find in t/t_gated_delta_net.cpp (at 775bba7661) the test cases that compare the chain kernel with the token kernel bit for bit; name them (TEST_CASE names, lines).
3. **Our AMX block kernel (Part A).** In src/tron/kernels/amx_gdn.cpp and h/tron/kernels/amx_gdn_iface.hpp (worktree /home/jhan/workspace/ai-runs/tron-gdn-amx) and in the executor code that calls it (h/tron/models/gdn_rolling_executor.hpp at 775bba7661: search for amx_gdn, block_kernel, pack_key_head, advance_value_head): for each operand of the kernel (normalized key, normalized query, value, decay, beta, the recurrent matrix S0, the corrections delta) say (a) where the value is produced and which rounding of your table made it, (b) how the kernel reads it (packed with bf16_bits which keeps the upper 16 bits; split into three bf16 pieces; used as FP32 in AVX-512), with file:line and the code line, and (c) what happens to the kernel's result if that operand stops being representable in bf16 (is the low half of the FP32 bit pattern dropped silently, i.e. truncation toward zero; is there an assert or a check that would fire; does a test check representability). State plainly which operands REQUIRE a bf16-representable value today.
4. **Tests that encode the assumption.** In t/t_amx_gdn_numerics.cpp (worktree) and in the chain and block cases of t/t_gated_delta_net.cpp at 775bba7661: how do the tests make their keys and queries (do they call normalize_gdn, or round by hand, or use random FP32 values)? Would the tests still pass their stated error band if normalize_gdn returned unrounded FP32 values? Reason from the code, and say "Not verified by a run".
5. **Size of the rounding as an error.** From Note [BF16 rounding on FP32 bits] (find it: grep -rn "BF16 rounding on FP32 bits" h/ common/ 2>/dev/null in the tree at 127a662083 via git grep) and the PR #5571 body (gh pr view 5571 --repo positron-ai/tron --json body): what relative error does one bf16 rounding introduce (PR #5571 says at most 2^-8 of the value), and what does truncation (keeping the upper 16 bits) introduce (up to 2^-7 relative, always toward zero: derive it from the bf16 format with 8 significant bits and say it is a derivation). Compare with the error band that our Note [AMX GatedDeltaNet block kernel] and t_amx_gdn_numerics.cpp state today (quote the band).
End with a short list "What breaks in our code when PR #5571 or the six normalization removals land", ordered by severity.
`,
  },
  {
    key: 'i4444',
    file: `${OUT}/facts-4444.md`,
    prompt: `
## Your task: issue #4444 against today's main, and its link to issue #5433
Write the report to ${OUT}/facts-4444.md. Temporary files: none needed.

Background: issue #4444 (ours) records that binaries with the AMX attention kernels or the VNNI K layout generate other tokens than the row-major binary. Its measured causes (2026-10-16, at main 72308ec90c) were: (1) three different FP32 add orders in the Q.K dot product (the AVX-512 "dotter" with 2 accumulators of 16 lanes and a halving tree; the VNNI reader, sequential; the AMX tile product), (2) the AVX path truncates the softmax weights P to bf16 (interleave_bf16_ps in h/tron/models/kv_cache.hpp near line 2996 at that time) while the AMX path rounds P to nearest even, (3) a path choice at a page end in one PR. Open items of the issue: item 2 the kill-switch contract (what TRON_AMX_DISABLE=1 promises), item 3 a model-level bound (a test that compares logits by total variation distance, TVD).
Issue #5433 (GDN owner) lists PR #4366 "Round BF16 stores to nearest even" (merged 2026-10-08), PR #4722 "Tighten the GPT-OSS 20B golden-logit limit" (merged 2026-10-10) and PR #4975 "Merge row_dot's accumulators in FP32" (merged 2026-10-31) as earlier measurements of other roundings.

Do this:
1. Read issue #4444 in full with its comments (gh issue view 4444 --repo positron-ai/tron --comments) and issue #5433 with its comments, and the bodies of PR #4366, #4722, #4975, #5571 (gh pr view N --repo positron-ai/tron --json title,body,mergedAt,files). Summarize each of the three merged PRs in 4 sentences: what code changed, what was measured (numbers with units), what was decided.
2. For each of the three merged PRs: does it change code that issue #4444 names (the dotter's accumulators and their merge order; the truncation of P in interleave_bf16_ps; the VNNI reader k_vnni::qk_group; the AMX kernels in src/tron/kernels/amx_attn.cpp; Note [AMX attention dispatch] in h/tron/kernels/amx_attn_iface.hpp)? Use gh pr view N --json files and gh pr diff N --repo positron-ai/tron (read only the relevant files). Say exactly which statements of issue #4444 (body and the three comments) are out of date on today's main because of them, with the old statement quoted and the new fact with file:line at f454423b09.
3. On today's main (f454423b09): is cause 2 still present? Find how the AVX-512 PV path converts the softmax weights to bf16 (search h/tron/models/kv_cache.hpp and h/tron/kernels for interleave_bf16_ps, cvtneps_pbh, cvtne2ps, "trunc", srli_epi32 by 16) and how the AMX path does it. Quote the lines. Is cause 1 still as described (dotter order; search for row_dot in h/tron/kernels/dotter.hpp or where it lives now)? What does item 4 of Note [AMX attention dispatch] say today about TRON_AMX_DISABLE (quote it with its line numbers)?
4. State of the PRs that issue #4444 names: #3879, #4424, #4956, #4957, #4958, #4959, #5015, #5022 (state, mergedAt). Is the VNNI K layout (TRON_K_VNNI) on main today (grep CMakeLists.txt and CMakePresets.json at f454423b09)?
5. **The link between the two issues.** Make a two-column comparison: issue #4444 against issue #5433 on: which code, which two things are compared (reference and trial), which rounding or add-order difference, the size of one difference (in bf16 steps or relative), how the effect is measured (tokens, logit margin, TVD, loss), what decision rule exists (issue #5433's second comment holds thresholds: quote them exactly: the TVD test, the three damage tests, the four-case reading rule), who decides, and what is still open. Then answer in one paragraph each: (a) Could the thresholds of issue #5433 serve as the model-level bound that item 3 of issue #4444 asks for? What would have to be adapted (the reference: Transformers model in BF16 against the row-major binary or the kill-switch run)? (b) Does anything in issue #5433 or PR #5571 change code on the attention paths of issue #4444? (c) Is there any statement in issue #5433 that issue #4444's data already answers or contradicts (for example on how often a rounding-size change flips a token)?
6. Give your own verdict in the report: are the two issues the same topic, closely related, or loosely related? Give the three strongest facts for and the three strongest against "closely related". No hedging filler: state the facts.
`,
  },
  {
    key: 'method',
    file: `${OUT}/facts-method.md`,
    prompt: `
## Your task: the measurement method of issue #5433 and the tools that exist to run it
Write the report to ${OUT}/facts-method.md. Temporary files: none needed.

1. **The method of issue #5433, exactly.** Read the issue and its comments (gh issue view 5433 --repo positron-ai/tron --comments) and the body of PR #5571. Write the method as a numbered procedure: the three builds (all 22 roundings in; six normalization roundings out; fourteen out), what "built for kernel timing" and "built for FPGA cards" mean, each speed test with its threshold r, the TVD test (model, text length, number of positions, the comparison and its limit), the three damage tests, and the four-case reading rule. Quote the numbers. List what the issue leaves unsaid that a person repeating it would need (for example: which 8,192-token text, which 768 positions, how the Transformers model in BF16 is run, how many paired runs, which machine).
2. **Where the pieces live in the repository** (search at 127a662083 with git -C /home/jhan/workspace/tron grep -n ... 127a662083 -- <paths>):
   - the reference gated_delta_net_with_state in ingest/runtime/tron_ingest_runtime/ops.py (line range, and how it runs on BF16 tensors);
   - where the Transformers version is pinned (search for "transformers" in ingest/ pyproject or lock files and nix files; issue #5433 names 5.15.1, 5.17 and 5.20.2 and PR #5124);
   - the two benchmark cases gdn_conv1d_silu<8192> and "gdn_recurrence<16, 32, 128, 128> step" in t/t_gated_delta_net.cpp (lines; how a benchmark case is run: Catch2 BENCHMARK? which command line);
   - the test t_generate_ingest_1_qwen3_5_4b_fpga: where it is defined (t/CMakeLists.txt or generated), its two cases, which data files it reads (token file, golden logits; paths under /scratch/test/data), and whether it exists at 127a662083, at 72e1191804 and on main f454423b09;
   - any existing tool that computes TVD or compares logits between two runs: git grep -n -i -E "tvd|total variation" at 127a662083 and on main in ingest/, bin/, t/, scripts; and the runtron options that record scores: --intermediates-file, --force-feed-text-token-file, "Top-k Logits" (find them in src/ and say what each writes).
3. **Our own tools and data** (read the files; do not run them):
   - /home/jhan/workspace/intel-AMX/GDN/exec/gdn-impl-20261121/: build.sh, run-one.sh (it is in ../gdn-20261120/), campaign.sh, token-check.sh, logit-margin.sh, logit_summary.py, unit-tests.sh, e4b-check.sh. For each: one sentence on what it does, its inputs (environment variables), and what it writes.
   - /home/jhan/workspace/intel-AMX/exec/dd/dd_logits_step.py and dd_first_divergence.py, and /home/jhan/workspace/intel-AMX/exec/td-20261016/ (probe-td.sh, analyze-td.sh, tiestats/, ktest/, replay/): what each computes (does one of them compute TVD per step between two score records? give the function and the line), and the record format it expects.
   - Existing results that the next agent can reuse without a new run: list the directories under /home/jhan/workspace/intel-AMX/GDN/exec/results/ (names, sizes with du -sh, and for gdn-impl-20261121/tokens what logits-* files hold) and /home/jhan/workspace/intel-AMX/exec/results/td-20261016/ (names only).
4. **What a TVD measurement of our AMX GDN kernel would need.** From the above, write the shortest procedure that would give "mean TVD between the AMX block kernel build and the chain kernel build over N positions of one text" with the tools that exist: which binary, which options, which record, which script, and what is missing (name each missing piece). Say what it cannot give (for example the distance to the Transformers model in BF16, if no tool runs that model).
5. **The Qwen3.5 4B generation test and golden data.** Does the model's branch 72e1191804 hold golden-logit data or a "support_level" note that says the tokens of this model are not yet valid (git grep -n support_level 72e1191804 -- config/ ingest/ | head; look at the Qwen3.5 4B entry)? Quote it. This matters for any claim about "correct" tokens.
`,
  },
  {
    key: 'parta',
    file: `${OUT}/facts-parta-options.md`,
    prompt: `
## Your task: what the AMX block kernel for GDN must do when the normalized key and query stop being bf16 values
Write the report to ${OUT}/facts-parta-options.md. Temporary files: none needed. Read the code in the worktree /home/jhan/workspace/ai-runs/tron-gdn-amx (882e5322f1): src/tron/kernels/amx_gdn.cpp, h/tron/kernels/amx_gdn_iface.hpp, t/t_amx_gdn_numerics.cpp, h/tron/models/gdn_rolling_executor.hpp, h/tron/kernels/gated_delta_net.hpp. Read also our measured results: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html (use a text extraction: python3 with html.parser or sed to strip tags; it is large) and /home/jhan/workspace/intel-AMX/GDN/exec/gdn-impl-20261121/pr-body.md, and the design page /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html if you need the cost model.

1. **Count the tile products today.** From the code of the four stages (Note [AMX GatedDeltaNet block kernel]): for one key head and one block of 32 tokens, count the TDPBF16PS executions (_tile_dpbf16ps) per stage, with the loop bounds that give the count (file:line). Express the total per value head per token. Our design text says 18.5 tile products per value head per token: confirm or correct with the arithmetic shown. Say for each stage which operand is "one bf16 piece because the value is already bf16" (K, Q) and which is "three pieces" (S0, w.Delta).
2. **Option list when K and Q are FP32 values with 24 significant bits** (after PR #5571 or after the six normalization roundings are removed). For each option give: what changes in the code (which functions), the tile-product count per value head per token by the same arithmetic (marked "derived"), and the numerical meaning:
   - O1: the kernel rounds K and Q to bf16 itself (round to nearest even) and then works as today. The AMX path then uses rounded keys and queries while the AVX-512 chain kernel and the token kernel use unrounded ones. Derive the size of that difference per key coordinate (at most 2^-9 relative for round to nearest, half a bf16 step) and say what it does to the stated error band of t_amx_gdn_numerics.cpp (quote the band; say "Not verified by a run").
   - O2: K and Q are split into two or three bf16 pieces like S0. Count the products for stage 1 (K S0, Q S0: pieces of K times pieces of S0), stage 2 (K K^T, Q K^T) and stage 4 (K^T (w.Delta)). Give the total for 2 pieces and for 3 pieces and the factor against today.
   - O3: the model keeps one rounding of the normalized key and query for the AMX path only (the layer rounds K and Q once after normalization when the block kernel will run; all other intermediate values stay FP32). Say how that differs from O1 (it is the same arithmetic; the difference is where the contract is written and whether the chain kernel uses the same rounded values so that AMX on and AMX off stay comparable).
   - O4: no AMX block kernel for GDN (keep only the chain kernel).
   Add any further option you find in the code.
3. **What our measurements say about the stake.** From the results page and the PR body: the measured fall of time to first token (TTFT) for Part A against Part 0 and against the counters build per cell (1 and 8 users; prompt 1,024, 4,096, 8,192 tokens), and the measured GDN step times (6.08, 4.01, 2.56 microseconds). Quote the table rows with their source (file and section). Then, as a labeled estimate ("est."), say what share of the Part A step time the tile products take if the results page or the bench files under /home/jhan/workspace/intel-AMX/GDN/exec/gdn-impl-20261121/bench/ and /home/jhan/workspace/intel-AMX/GDN/exec/results/gdn-impl-20261121/ give a stage split (look for task3/task4 outputs and for the counters keys of the block kernel in collected.json: list the keys you find that time the block kernel). If no stage split exists, write "Insufficient data" and name the measurement (which bench with which change) that would give it.
4. **The numerics of the block kernel as measured so far.** From the results page, the PR body and t_amx_gdn_numerics.cpp: quote every measured statement about how the block kernel's results differ from the chain kernel (share of bf16 output words that differ, relative L2 of the matrices, token identity: same tokens for 185 steps then a flip at a margin of 8 bf16 steps, drift up to 10 bf16 steps). Give the source of each. Compare the size of these differences with the size of one rounding of K and Q (2^-9 to 2^-8 relative): is today's block-kernel difference smaller or larger than what O1 would add? Answer from the numbers; where they do not allow an answer, write "Insufficient data" and name the measurement.
5. **A unit-level experiment the next agent can run without the model**: describe (do not run) the smallest change to t/t_amx_gdn_numerics.cpp or a stand-alone program that feeds unrounded normalized keys and queries to the block kernel as it is today and reports the error against gdn_recurrence_chain, and the same with O1. Name the functions to call and the existing test helpers to reuse (file:line).
`,
  },
]

phase('Read')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: `read:${t.key}`, phase: 'Read' })
    .then(r => ({ key: t.key, file: t.file, summary: r }))
))
return results.filter(Boolean)
