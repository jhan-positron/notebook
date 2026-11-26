export const meta = {
  name: 'gdn-split-handoff-facts',
  description: 'Read-only fact gathering for the GDN PR split handoff: commit cut, counter switch, Part B port, tests and CI, scripts',
  phases: [{ title: 'Read', detail: 'five read-only readers, one topic each' }],
}

const COMMON = `
You gather facts for a handoff document. Another agent will later split one draft PR of the repository positron-ai/tron into four PRs. You do NOT do the split. You only read and report.

HARD RULES
- Read-only. Do not edit, create, move or delete any file outside your scratchpad. Do not check out, commit, stash, rebase, push or change any branch or working tree. Never run "git worktree prune". Use "git show <sha>:<path>", "git diff", "git log", "git grep <pattern> <sha> -- <path>" and "git merge-tree --write-tree" (it writes objects only).
- No ssh. No builds. No test runs. GitHub: read-only "gh pr view" / "gh api" GET only.
- The git worktree to read from: /home/jhan/workspace/ai-runs/tron-gdn-amx (run git with "git -C /home/jhan/workspace/ai-runs/tron-gdn-amx ..."; a plain "cd" prints a directory listing, so avoid it).
- Report only what you verified with a command. Mark anything else "not verified". Give file:line or a commit id as evidence for every fact. Line numbers must name the commit they refer to.
- Your final text is the return value. Write it as compact markdown: headed lists and small tables. No preamble.

BACKGROUND (verified earlier)
- Model's branch = origin/rbjarnason/qwen35-native-4b-registry at 72e1191804 (head of PR #3696, not merged; it registers the model Qwen3.5 4B, whose layers are GatedDeltaNet (GDN) and attention).
- Branch jhan-gdn-amx = three commits on 72e1191804:
  0d69ef3ce8 "counters" (GDN path statistics, switch TRON_GDN_STATS),
  775bba7661 "Part 0 + Part A" in ONE commit (Part 0 = GDN chain kernel gdn_recurrence_chain + executor advance(), AVX-512 only, bit-identical to the token loop; Part A = AMX block kernel for GDN: h/tron/kernels/amx_gdn_iface.hpp, src/tron/kernels/amx_gdn.cpp, t/t_amx_gdn_numerics.cpp, run-time switch TRON_AMX_GDN_DISABLE),
  882e5322f1 "Part B" (AMX attention kernels for 256-wide heads with 4 query heads per KV head, namespace amx_attn_h256g4).
- PR #5022 = branch origin/jhan-amx-kvmul16 at ddf843ad97, based on main (AMX attention for 16 query heads per KV head, template parameter group_heads).
- Planned split: PR 1 counters -> PR 2 Part 0 -> PR 3 Part A (a stack on the model's branch); PR 4 Part B on a new branch off PR #5022's branch.
- AMX = Intel tile-matrix instructions. TRON_AMX_DISPATCH = the CMake option that compiles the AMX kernels. TRON_AMX_DISABLE=1 = run-time kill switch for all AMX kernels.
`

const TOPICS = [
  {
    key: 'cut',
    prompt: `${COMMON}
YOUR TOPIC: how to cut commit 775bba7661 into a Part 0 commit and a Part A commit, and what the counters commit already holds.

Tasks:
1. For each of the 15 files of 775bba7661 ("git show --stat 775bba7661"), classify its hunks: P0 (chain kernel, executor advance(), their tests), PA (AMX block kernel and everything that exists only for it), or MIXED. For a MIXED file give the line ranges at 775bba7661 that are PA, and say in one or two lines what the Part 0-only version of that file must look like (for example: which enum, parameter, member, #ifdef TRON_AMX_DISPATCH region, static_assert or include disappears). Be exact for h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_execution.hpp, h/tron/models/model.hpp, h/tron/models/gdn_stats.hpp, t/t_gated_delta_net.cpp, t/CMakeLists.txt, src/tron/CMakeLists.txt, CMakeLists.txt, README.ci.md, h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp.
2. Say what the small hunks of 775bba7661 in h/tron/kernels/amx_attn_iface.hpp and src/tron/kernels/amx_attn.cpp do, and which part needs them (Part A? Part B commit 882e5322f1?).
3. List the TEST_CASEs of t/t_gated_delta_net.cpp at 775bba7661 that 775bba7661 adds or changes, each with its line and its part (P0 / PA / both). Say which of them call the block kernel or use gdn_block_kernel.
4. In the counters commit 0d69ef3ce8: list the symbols, enum values, counter fields and report rows in h/tron/models/gdn_stats.hpp and README.stats.md that name the chain kernel or the AMX block kernel (for example gdn_path::chain, gdn_path::amx_block, amx_blocks, amx_fallback_blocks, BLOCK_TOKENS_32). For each say whether any code at 0d69ef3ce8 writes it, or whether its first writer comes with 775bba7661. This tells whether PR 1 would hold rows without a writer.
5. Old work-in-progress commits 64cde700af ("WIP Part 0") and a72caf7e40 ("WIP Part A") exist locally. Compare only their FILE LISTS ("git show --stat") with your classification and say whether they agree. They are old code; do not propose them as the source.
6. Estimate the added lines of the Part 0 commit and of the Part A commit from your classification (label them "est.").
Finish with a short list "Risks for the cut" (things that would not compile or would lose a test if cut carelessly).`,
  },
  {
    key: 'switch',
    prompt: `${COMMON}
YOUR TOPIC: the counter switch. Decision already made by the author: the GDN counters reuse the existing switch TRON_ATTN_STATS, and TRON_GDN_STATS goes away.

Tasks (all at commit 882e5322f1 unless stated):
1. Show how h/tron/models/attn_stats.hpp reads TRON_ATTN_STATS (function name, lines, which values turn it on, what it logs for other values) and how h/tron/models/gdn_stats.hpp reads TRON_GDN_STATS (same details). Is there a function in attn_stats.hpp that gdn_stats.hpp could call, or does gdn_stats.hpp include attn_stats.hpp already? Does attn_stats.hpp exist at 72e1191804 (the model's branch) with the same reader?
2. List EVERY place that names TRON_GDN_STATS in the repository at 882e5322f1 (code, tests, README files, generated-code templates such as ingest/src/TronCpp.hs, CMake): file:line and what must change. Include the JSON header field "switch", the info log line, and the test case in t/t_gdn_stats.cpp that sets the variable.
3. Say what the attention stats print at exit and where the GDN stats print ("[attn-stats]" and "[gdn-stats]" lines; FUSE paths /model/<id>/...). With one shared switch, does a model without GDN layers print any "[gdn-stats]" line? Read the code and answer with file:line. Does a model with GDN layers get attention stats turned on too (cost)?
4. In the measurement scripts under /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/ and /home/jhan/workspace/intel-AMX/exec/gdn-20261120/ list every line that sets or parses TRON_GDN_STATS or "[gdn-stats]" (grep -n). These scripts are outside the repository; just list file:line and one phrase on what the line does.
5. README.stats.md at 882e5322f1: which lines describe the GDN switch, and is there a section on TRON_ATTN_STATS that the GDN text should join?
Finish with "Minimal change list" for the switch reuse: an ordered list of edits (file, what), with nothing speculative.`,
  },
  {
    key: 'partb',
    prompt: `${COMMON}
YOUR TOPIC: porting Part B (commit 882e5322f1, 7 files) onto PR #5022's branch (origin/jhan-amx-kvmul16 at ddf843ad97), and the measurement-only build.

Tasks:
1. Simulate the cherry-pick of 882e5322f1 onto ddf843ad97: "git merge-tree --write-tree --merge-base=775bba7661 ddf843ad97 882e5322f1" (read the man page if the option order differs in this git version). List each of the 7 files: clean or conflict, and the number of conflict regions (count the "<<<<<<<" markers with "git show <tree>:<path> | grep -c"). Do not write any file into the worktree.
2. Does Part B depend on anything of commit 775bba7661 (the GDN commit)? 775bba7661 changes h/tron/kernels/amx_attn_iface.hpp and src/tron/kernels/amx_attn.cpp by 4 lines each: show those hunks and say whether 882e5322f1 needs them. A local branch jhan-gdn-partb (8376a86d8a) holds Part B alone on the model's branch: show "git diff --stat 882e5322f1 8376a86d8a" restricted to the 7 files, and say in what it differs.
3. Describe, with file:line at ddf843ad97, the structures of PR #5022 that the ported Part B must fit next to: the group_heads template parameter and the kernel namespaces in h/tron/kernels/amx_attn_iface.hpp and src/tron/kernels/amx_attn.cpp; the new file h/tron/kernels/amx_attn_transpose.hpp; how h/tron/models/self_attention.hpp decides per attention geometry whether AMX serves it (names of the predicates) and where it calls the kernels; the query pack size. Then the same for Part B at 882e5322f1 (amx_attn_h256g4::shape_ok, eligible, amx_serves_128x4 / amx_serves_256x4 / amx_serves, amx_q_pack_elems, is_dense_amx_page). Say plainly which names or mechanisms of the two sides collide (same job, different name or shape).
4. Tests: how do t/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp and t/t_llama_unit.cpp differ between the two sides (cases added by #5022, cases added by Part B)? Only names and counts.
5. Measurement-only build "model's branch + PR #5022 + Part B": simulate merging ddf843ad97 into 72e1191804 with "git merge-tree --write-tree 72e1191804 ddf843ad97" and list the conflicting files. Also report "git merge-base 72e1191804 ddf843ad97" with its date and "git merge-base origin/main ddf843ad97".
6. Models: at ddf843ad97 show the config/models.yaml entries whose name contains gemma_4_e4b (names, slugs, executors, tags) and confirm that no qwen_3p5 entry exists there. Show the same for 72e1191804 (both exist?).
7. State of PR #5022: "gh pr view 5022 -R positron-ai/tron --json state,isDraft,reviewDecision,mergeStateStatus,headRefOid,baseRefName".
Finish with "Port plan facts": which files need hand work, in which order, and what must stay untouched of PR #5022's code.`,
  },
  {
    key: 'tests',
    prompt: `${COMMON}
YOUR TOPIC: tests, CI lanes and housekeeping files for the four future PRs.

Tasks:
1. Read AGENTS.md at 72e1191804 and at origin/main. Quote verbatim (with line numbers and the commit) every rule on: PR stacks and drafts, the labels "Skip benchmarks" and "Run CI", tests that must run in CI, config/test-benchmarks.json, changelog.d, commit and PR text. Note any difference between the two commits.
2. For each test program that the branch jhan-gdn-amx adds or changes (t_gdn_stats, t_gated_delta_net, t_amx_gdn_numerics, t_amx_numerics, t_amx_dispatch_dtype, and any other in "git diff --stat 72e1191804 882e5322f1 -- t"): where it is registered in t/CMakeLists.txt (lines at 882e5322f1), whether it is built only with TRON_AMX_DISPATCH, and what its test cases do when the host has no AMX (skip? pass? how is a skip reported?).
3. CI lanes: read .github/workflows (at origin/main) and nix/ files and README.ci.md. Which workflow runs on every PR, does it set TRON_AMX_DISPATCH, does it skip build and test on draft PRs without the "Run CI" label (quote the lines)? Which workflow builds with TRON_AMX_DISPATCH on and how does it start? So: which of the test programs of task 2 execute their AMX cases in which lane?
4. config/test-benchmarks.json at 72e1191804 and at ddf843ad97: for each test of task 2 list which machine blocks hold an entry (python3 one-liner over "git show"). Read doc/slice.md at origin/main: what happens to a test without an entry; what "bin/slice bench --check" and "--check-platform" do.
5. changelog.d: does the folder exist at 72e1191804? At ddf843ad97? Show changelog.d/5022.changed.md at ddf843ad97 as an example. Quote the rule for stacks from changelog.d/README.md at origin/main.
6. Lint that CI runs: find the commands (clang-format version, "make lint-notes", "git diff --check", forbidden includes such as <cassert>, any commit-message or changelog length check) with file:line.
7. The Gemma 4 E4B generation test: read t/gemma_4_e4b_generation.hpp and t/model_test_selection.cmake at ddf843ad97. State what limits the context to 64 tokens (TRON_BOOK_INITIAL_TOKENS / TRON_BOOK_MAX_TOKENS?), where the golden scores come from (file, how produced, how many token positions they cover), and what a variant with a context of several 64-token pages would need. Facts only, no design.
Finish with a table: test program | PR it belongs to (1 counters, 2 Part 0, 3 Part A, 4 Part B) | runs in the default PR lane? | AMX cases run where?`,
  },
  {
    key: 'scripts',
    prompt: `${COMMON}
YOUR TOPIC: the measurement scripts outside the repository that the next agent will reuse. They live in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/ and /home/jhan/workspace/intel-AMX/exec/gdn-20261120/ (read-only for you), results in /home/jhan/workspace/intel-AMX/exec/results/.

Tasks:
1. For each of these files give: one-line purpose, inputs (environment variables with defaults), outputs (paths), the machine it must run on, and every HARD-WIRED value that a new campaign over new commits must change (build tags, commit ids, arm tables, model slugs, the variable TRON_GDN_STATS, result-folder names): gdn-impl-20261121/{build.sh, build-all.sh, campaign.sh, unit-tests.sh, token-check.sh, logit-margin.sh, logit_summary.py, collect.py, compare.py, report_data.py, gen_report.py, decode_why.py, gen_pr_body.py, pr-prep.sh, final-chain.sh, post-chain.sh, e4b-check.sh, e4b-tests.sh, models.e4b.yaml} and gdn-20261120/{run-one.sh, build-3b35.sh, models.gdn.yaml}. Also /home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh.
2. build.sh: read it fully. Describe step by step what it does on delphi-3b35 (worktree creation from which repository path, cmake preset and options, the model list option, targets, CPU pinning, markers, the record file). Does anything in it assume the model's branch (for example "make ingest-deps", a model list that names qwen_3p5_4b)? Would it work unchanged for a commit based on main, such as PR #5022's head? Compare with the scripts in /home/jhan/workspace/intel-AMX/exec/pr5022-final-20261119/ (read its README.md) and say which script there builds a main-based tree on delphi-3b35.
3. run-one.sh: describe the safety checks before a run (load snapshot, which FPGA cards, which CPUs, the refusal rules), the runtron command line it forms, and what it writes.
4. campaign.sh: the arm table and the cell table verbatim, the rotation rule, how long the last campaign took (look at exec/logs/gdn-impl-20261121-campaign.log first and last time stamps and the number of runs; if several sessions are in the log, give each).
5. logit-margin.sh: what is hard-wired to the Qwen arms, and what a run for the model slug ingested-gemma-4-e4b-it-tp4 at generated token 63 would need to change.
6. List the result files that record the unit tests, the token checks and the build records of the old commits (exec/results/gdn-impl-20261121/: unit-tests.txt, tokens/summary.txt, build-*.txt, and so on) with one line each.
7. "git -C /home/jhan/workspace/tron worktree list": list the trees whose path contains gdn, kvmul16, glimmer, qwen35 or pr5022, with commit and branch.
Finish with "What the new campaign must change", an ordered list of script edits, with file names. Keep it factual.`,
  },
]

phase('Read')
const results = await parallel(TOPICS.map(t => () =>
  agent(t.prompt, { label: `read:${t.key}`, phase: 'Read' })
    .then(text => ({ key: t.key, text }))))
const out = {}
for (const r of results.filter(Boolean)) out[r.key] = r.text
const missing = TOPICS.map(t => t.key).filter(k => !out[k])
if (missing.length) log(`readers without a result: ${missing.join(', ')}`)
return out
