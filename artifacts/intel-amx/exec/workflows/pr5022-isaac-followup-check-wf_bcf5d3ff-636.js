export const meta = {
  name: 'pr5022-isaac-followup-check',
  description: 'Test the two commits of draft PR 5606 on delphi-3b35 and check every claim of the reviewer against the code',
  phases: [
    { title: 'Build and test', detail: 'one agent on delphi-3b35: option OFF and ON builds, mutations, symbol check' },
    { title: 'Read', detail: 'four readers: one-definition rule, required CI lane, diff review, stale text' },
    { title: 'Refute', detail: 'one skeptic per reader re-checks each finding' },
  ],
}

const IN = '/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/inputs'
const WT = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'

const CTX = `
CONTEXT
PR 5022 of the GitHub repository positron-ai/tron (author jhan-positron, branch jhan-amx-kvmul16, head ddf843ad97f8602fc1171458e42036ef03b6e4c4) lets the AMX attention kernels serve 16 query heads per KV head (the Muse Glimmer shape). The reviewer Isaac (GitHub login ishapira-positron) answered on 2026-11-24 00:48 UTC with one conversation comment. He also opened draft PR 5606 (branch ishapira/jhan-amx-kvmul16-review-followup, base jhan-amx-kvmul16) with two commits on top of the head:
- c6cba6b0f8b9be57672a3cbf36021df4069a2b0b "Run the AMX dispatch test wherever the tests are built"
- 90a9110be5d2c6552267322c472902984dca8e0f "Drop the placeholder case of the AMX dispatch test"
His reviews are written by a multi-agent AI pipeline. Treat every statement of his as a claim to test, not as a fact.

Terms: TRON_AMX_DISPATCH is the CMake option (default OFF) that compiles the AMX kernels and their call sites. The "required lane" is the GCP Nix workflow (.github/workflows/gcp-nix.yml), which every PR must pass and which builds with the option OFF. The "CMake workflow" is .github/workflows/cmake-single-platform.yml, started by hand, which builds with the option ON. Slice is bin/slice, the test scheduler. The registry is config/test-benchmarks.json.

INPUTS (read them first)
- ${IN}/comment-7118448228.md : Isaac's comment
- ${IN}/pr5606-body.md : description of PR 5606
- ${IN}/pr5606.diff : whole diff of PR 5606; ${IN}/commit-c6cba6b0f8.patch and ${IN}/commit-90a9110be5.patch : the two commits
- ${IN}/pr5022-body-live.md : the live description of PR 5022
- Source: the git worktree ${WT} is the PR branch at the head ddf843ad97, clean. Both commits of PR 5606 are fetched into that repository, so \`git -C ${WT} show 90a9110be5:<path>\` and \`git -C ${WT} diff ddf843ad97 90a9110be5\` work.
- Background of the earlier review round: /home/jhan/workspace/intel-AMX/muse-glimmer/status/handoff-pr5022-20261120.md, and the replies already posted in /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/md/ (B2.md and COMBINED.md give the reason the build option stays out of the required lane).

HARD RULES
- GitHub is read-only for you: \`gh\` may only read. Do not post, comment, label, push, commit, merge, rerun, or open anything.
- Do not modify the worktree ${WT}, and do not write any file outside the output folders this prompt names. Never run \`git worktree prune\`.
- Do not send messages to other agents or sessions. Do not spawn further agents.
- Ground every statement in a file:line, a command with its output, or a URL. When you cannot verify something, write "Insufficient data" and name the measurement or source that would resolve it. Do not guess.
`

const NO_MACHINE = `- Do not log in to any lab machine (no ssh to delphi-* or andoria-*). Another agent runs the builds. You work by reading the source and the GitHub records.
`

const FINDINGS = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'at most 8 sentences: the answer to the main questions' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          claim: { type: 'string', description: 'the statement that was checked, in one sentence' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly', 'insufficient-data'] },
          evidence: { type: 'string', description: 'file:line references and commands with output that support the verdict' },
          impact: { type: 'string', description: 'what this means for taking the two commits into PR 5022' },
        },
        required: ['id', 'claim', 'verdict', 'evidence'],
      },
    },
    risks: { type: 'array', items: { type: 'string' } },
    recommendations: { type: 'array', items: { type: 'string' } },
    proposed_texts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          target: { type: 'string' },
          before: { type: 'string' },
          after: { type: 'string' },
          note: { type: 'string' },
        },
        required: ['target', 'after'],
      },
    },
  },
  required: ['summary', 'findings'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    overall: { type: 'string' },
    checked: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          holds: { type: 'boolean' },
          note: { type: 'string', description: 'what you re-ran or re-read, and what you saw' },
        },
        required: ['id', 'holds', 'note'],
      },
    },
    new_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['overall', 'checked'],
}

const READERS = [
  {
    key: 'odr',
    prompt: `${CTX}${NO_MACHINE}
YOUR TASK: the one-definition-rule question.
Commit c6cba6b0f8 registers the test as \`add_catch_test(NAME t_amx_dispatch_dtype DEFINES TRON_AMX_DISPATCH LIBRARIES tron pos_fake PROPERTIES LABELS fake)\`. So in a build with the option OFF, the test's own translation unit is compiled with -DTRON_AMX_DISPATCH, and everything it links (the static library tron, pos_fake, the object library testfake_objects) is compiled without it. Its commit message claims: "The option changes only code inside the self_attention<model> template, and no other translation unit in this binary instantiates that template for the test's models, so nothing else in the binary disagrees about it."
Check that claim by reading the code at 90a9110be5. Answer each point with evidence:
1. List every \`#ifdef TRON_AMX_DISPATCH\` (and #if defined / #ifndef) site in all headers and sources (h/, src/, lib/, t/). For each: which entity encloses it (class template member, free function template, non-template inline function, class layout, namespace-scope variable), and whether a translation unit compiled without the define can emit a different definition of the same linker symbol.
2. Which exact types does the test instantiate (model type, executor types, self_attention specialisations)? Are they local to the test file (internal linkage or a test-only type), or shared types that libtron, pos_fake or testfake_objects also instantiate? Look for explicit instantiations and for uses of the same specialisation in src/ and in the sources of testfake_objects.
3. Does the option change the layout or the members of any class that crosses a translation-unit boundary in this binary (a member under the #ifdef, a differing sizeof)?
4. In an option-OFF build, where do the symbols of namespace tron::amx_attn_h128g4 that the dispatch calls come from? The test header says it defines every entry point as a CPU fake. Check that no entry point is left undefined (a link error) and that none is defined twice in an option-ON build (the test's fakes versus src/tron/kernels/amx_attn.cpp inside libtron.a): explain why the option-ON link works today.
5. Precompiled headers and unity builds: does t/CMakeLists.txt or the top-level CMake reuse a precompiled header across test targets, or use unity builds, in a way that a per-target definition would break or silently ignore?
6. The precedent: how does t_page_share_counters use \`DEFINES TRON_PAGE_SHARE_COUNTERS\`? Is its situation the same (a define that changes template code in a header, with libtron compiled without it), or different in a way that matters?
7. Any other mechanism by which the per-target define could make the test pass or fail for the wrong reason (for example the linker choosing a libtron copy of an inline function that was compiled without the dispatch).
Return findings with ids O1..O7 and a plain overall answer: is the claim of the commit message true, and is the per-target define safe in the option-OFF build and in the option-ON build?`,
  },
  {
    key: 'lane',
    prompt: `${CTX}${NO_MACHINE}
YOUR TASK: what the change does in the required CI lane, and what the registry needs.
Read .github/workflows/gcp-nix.yml, the Nix files it uses (flake.nix, nix/, especially nix/cmake-tron-test-build.nix), .github/workflows/cmake-single-platform.yml, bin/slice, config/test-benchmarks.json, t/AGENTS.md, AGENTS.md, README.ci.md, t/CMakeLists.txt, all at 90a9110be5. Use read-only \`gh\` calls for run records (for example the passed runs of the head: GCP Nix run 44777709823 and CMake workflow run 44777748892, and the checks of PR 5606). Answer each point with evidence:
1. In the required lane today (head ddf843ad97, option OFF): is t_amx_dispatch_dtype built and run? In which job, on which runner labels or machine type, and with which CPU features? Give the log line of that test from run 44777709823 if you can read it.
2. With the two commits, the required lane compiles the \`#ifdef TRON_AMX_DISPATCH\` regions of h/tron/models/self_attention.hpp and the body of t/t_amx_dispatch_dtype.cpp for the first time with the Nix toolchain. Which compiler and version, which warning flags (is -Werror set?), which CPU flags does that lane use, and how do they differ from the CMake workflow, where this code is compiled today? Name any concrete reason the code could fail to compile or to run there (for example an instruction the test's AVX path needs that the lane's machines lack). Note that the test defines CPU fakes for the AMX kernels and executes no AMX instruction.
3. Isaac writes that his Nix sandbox build "leaves out the lane's model flags" and that draft CI ran only lint and contract checks. What are the lane's model flags, and can they change how this test is built or whether it is registered (see tron_register_catch_test_model_contract and add_catch_test in t/CMakeLists.txt)? Has any CI run compiled and run the changed test in the required lane so far? List the checks of PR 5606 and say which ran and which were skipped.
4. The registry rows of t_amx_dispatch_dtype (two machine classes) record times of about 0.42 s and 0.83 s and max_rss_mb 8. The real test body was measured on a Granite Rapids host at 0.77 to 0.79 s and 97 to 99 MiB (file /home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/wall-times.txt). How does bin/slice use \`times\` and \`max_rss_mb\` (scheduling, time limits, memory admission, drift warnings)? What happens when a test needs 12 times the recorded memory or twice the time? Is there any CI check that fails on such drift? Quote the exact rule of t/AGENTS.md about \`bin/slice bench --update\`. Which registry class does each CI lane use? Is a hand edit of max_rss_mb accepted by \`bin/slice bench --check\` (what does that check compare)?
5. Does any checked-in manifest, contract test or count depend on the Catch2 case names or the number of cases of this binary (the placeholder case "AMX dispatch dtype test skipped (dispatch not compiled)" disappears)? Look at the slice catch2 manifest test, the label slice_filter_catch2, and the CI machinery contract tests.
6. Is there a way to run the required lane on the two commits before they are pushed to the branch of PR 5022 (for example a label on the draft PR 5606, or a manual dispatch of gcp-nix.yml on a ref)? Describe it from the workflow files. Do not do it.
Return findings with ids L1..L6, the risks, and what you recommend for the registry rows.`,
  },
  {
    key: 'review',
    prompt: `${CTX}${NO_MACHINE}
YOUR TASK: an independent code review of the two commits of PR 5606 (diff ddf843ad97..90a9110be5, 4 files, 12 lines added, 11 removed). You are not given anyone's conclusion on purpose. Review the diff as a careful maintainer of positron-ai/tron would before taking it into PR 5022.
If the skills tron-code-review and folks-code-review are available to you, load them and apply their checks. Read the surrounding code, not only the hunks: t/t_amx_dispatch_dtype.cpp in full, the add_catch_test function in t/CMakeLists.txt, the comment block around src/tron/CMakeLists.txt:207-225, README.ci.md around line 585-600, t/AGENTS.md, AGENTS.md and the repository lint rules (GNUmakefile lint targets, lefthook.yml, any cmake format or line-length rule).
Check at least:
1. Correctness of each hunk. Does the test still compile and mean the same in an option-ON build, where the library target tron already exports the definition as PUBLIC (a doubled definition)? Is anything left in the test file that only made sense with the removed guard (comments, includes, the header text)?
2. Each added sentence of comment and of README.ci.md: is it true of the code at 90a9110be5, and does it agree with the other comments in the same files? Flag any sentence that is wrong, misleading or longer than needed.
3. The second commit removes the guard and the placeholder case. What happens when the test is compiled without the define after that commit (compile error, link error, or failing sections)? Is the claim of the commit message right ("Without the guard, the bf16 sections fail")? Which is better for the repository: keeping the guard or dropping it?
4. Conventions: line length and format of the changed CMake lines compared with their neighbours, the changelog rule (does changelog.d/5022.changed.md need a change?), and whether a source comment gained an issue or PR number (the PR author's rule forbids new ones in source comments; README files are exempt; existing lines stay untouched).
5. Whether the registry file config/test-benchmarks.json or any other file should have changed in the same commit and did not.
6. Anything else a reviewer would raise.
Return findings with ids R1.. ordered by severity. For each: the exact lines, why it matters, and the smallest fix. Say plainly when you find no problem in a hunk.`,
  },
  {
    key: 'stale',
    prompt: `${CTX}${NO_MACHINE}
YOUR TASK: find every text that goes stale if PR 5022 takes the two commits, and draft the replacements.
After the change, t_amx_dispatch_dtype runs its real cases (30,747 assertions in an option-ON build today) in every build, including the required lane with the option OFF. t_amx_numerics is unchanged: its kernel cases still need the option ON.
1. Read the live description of PR 5022 (${IN}/pr5022-body-live.md). List every sentence or table row that is no longer true, or no longer complete, after the change. Isaac names one: "The Verification row for the default CI build says the AMX checks are compiled out." Find all of them. For each, write the exact replacement text. The description has 1,996 words by \`wc -w\` and must stay under 2,000 words, so count: give the word delta of every replacement and the new total. Keep the style of the description (plain English, short sentences, numbers with units). Do not invent results: where a number depends on a run that has not happened (the required lane on the new head), write a placeholder such as RUN_ID and say which run fills it.
2. Search the tree at 90a9110be5 for other text that the two commits make stale and did not update: comments in t/t_amx_numerics.cpp, the file header of t/t_amx_dispatch_dtype.cpp, h/tron/kernels/amx_attn_iface.hpp (the list of what the option does), src/tron/CMakeLists.txt, t/CMakeLists.txt, README.ci.md (the whole section, not only the edited paragraph), README.md, t/AGENTS.md, changelog.d/5022.changed.md, CMakePresets.json. Use grep for TRON_AMX_DISPATCH, "placeholder", "compiled out", "not compiled", "dispatch not compiled", "option ON", "legacy". For each hit say: still true, or stale with a proposed fix.
3. Compare the two new comment texts and the new README sentence with each other and with the code: do they say the same thing in three places, and is each true?
4. The replies already posted on PR 5022 (/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-post/md/*.md) cannot be edited. List which of their statements describe the old state, so the new reply can name the change in one sentence. Do not propose to edit them.
Return findings with ids S1.., and put every proposed replacement into proposed_texts with target, before, after and the word delta in the note.`,
  },
]

const BUILD_PROMPT = `${CTX}
YOUR TASK: build and test the two commits of PR 5606 on the test server delphi-3b35, and write the records. You are the only agent that uses that machine in this job. Run every planned step. If a step cannot run, say so plainly in the result, with the reason. Do not drop a step silently.

MACHINE RULES (they bind you)
- Reach the server with \`ssh delphi-3b35\` (user jhan). It is an Intel Xeon 6962P machine with AMX. It is shared: other users (Brian Hamon, John Pruitt) run servers on the first half of the machine. No sudo.
- Pin every command that you start there to our CPUs: \`nice -n10 taskset -c 96-143 ...\`. Builds use -j40. Every test run sets SYSTEM_CONFIG="--instance 1,2".
- The tests link the fake device. They must open no FPGA card and take no huge page. Do not start runtron, rinzler or any benchmark.
- Do not run \`bin/slice bench\` (also not --update or --new) and no \`bin/slice run\` with more than one slot. The read-only checks \`bin/slice bench --check\` and \`bin/slice bench --check-platform\` are allowed.
- Never run \`git worktree prune\`. Do not touch /var/tmp/jhan/b35-pr5022-final or /var/tmp/jhan/b35-gdn-stats. Create new worktrees of the shared repository /home/jhan/workspace/tron under new names: /var/tmp/jhan/b35-pr5606-off (option OFF) and /var/tmp/jhan/b35-pr5606-on (option ON), with \`git -C /home/jhan/workspace/tron worktree add --detach <path> <sha>\`. The preset builds into the folder gen inside the tree, so each option value needs its own tree. Leave both trees in place at the end, clean except for gen.
- Do not use delphi-3bda or any other machine. The clock of delphi-3b35 prints UTC.
- The home directory /home/jhan is shared between this machine and delphi-3b35 (check it once). On this machine keep to light commands (it allows about 6 busy processes).
- A remote \`cd\` in an interactive shell prints a directory listing, so prefer \`git -C\` and full paths.
- A build takes about 5 minutes. A Bash call here ends after at most 10 minutes. So start long steps on the server with nohup and a marker file that the script writes at its end, then wait with one ssh command that loops on the marker remotely (for example \`ssh delphi-3b35 'for i in $(seq 1 100); do [ -e MARKER ] && break; sleep 5; done; cat MARKER'\`).

WHERE THINGS GO
- Scripts and a README.md: /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/
- Records: /home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/ (the folder inputs/ there already exists; do not change it)
- Logs: /home/jhan/workspace/intel-AMX/exec/logs/pr5606-check-20261123-*.log
- Model scripts to adapt (read them first): /home/jhan/workspace/intel-AMX/exec/pr5022-final-20261119/build-3b35.sh, tests-3b35.sh, mutation-exit-code-3b35.sh, registry-check-3b35.sh and README.md, with the records in /home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/ (tests.txt, wall-times.txt, build-final.txt). Keep the same build recipe: \`cmake --preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=<ON|OFF> -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache\`, PATH with /tools/uv/0.9.5 and ~/.ghcup/bin in front, RelWithDebInfo.
- The three source states are real commits, visible in the shared repository: S0 = ddf843ad97f8602fc1171458e42036ef03b6e4c4 (the PR head), S1 = c6cba6b0f8b9be57672a3cbf36021df4069a2b0b (first commit), S2 = 90a9110be5d2c6552267322c472902984dca8e0f (both commits, git tree d6c77bd315c556ebf78556450562f2427ee660c7). Move a tree between states with \`git -C <tree> checkout --detach <sha>\`.

STEPS
0. Load snapshot before: \`ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh'\` (about 12 s). Save it. Report the busy share of our CPUs 96-143 and what runs on the other half.
1. Option OFF, state S0. Build the targets t_amx_dispatch_dtype, t_amx_numerics, t_llama_unit and t_page_share_counters. Run each of the first three (the way tests-3b35.sh runs them) and record exit code and the Catch2 summary lines. Expected for t_amx_dispatch_dtype: the placeholder, 1 assertion in 1 test case. Record the real numbers whatever they are.
2. Option OFF, state S1. Rebuild and run t_amx_dispatch_dtype, plain and with the kill switch TRON_AMX_DISABLE=1. Isaac's claim: 30,747 assertions pass. Record from gen/compile_commands.json that the compile command of t/t_amx_dispatch_dtype.cpp carries -DTRON_AMX_DISPATCH and that no command of the library tron does, and that src/tron/kernels/amx_attn.cpp is not compiled in this build.
3. Option OFF, state S2. Check the tree hash. Rebuild. Run the three tests again, plain and with the kill switch. Record: (a) exit codes and Catch2 summaries, and whether t_amx_numerics and t_llama_unit give the same counts as at S0; (b) the count of AMX instructions in gen/t_amx_dispatch_dtype from \`objdump -d --no-show-raw-insn\` (tdpbf16ps, tileloadd, tilestored, tilezero, ldtilecfg, tilerelease), expected 0; (c) wall time and peak resident memory of 5 runs of gen/t_amx_dispatch_dtype with \`/usr/bin/time -f "%e s %M KiB"\`, in the same form as wall-times.txt of the earlier round, and the same 5 runs of the S0 placeholder binary if you kept a copy (copy the S0 binary aside in step 1); (d) the count of compiler warnings in the build logs.
4. Symbol check for the one-definition rule, option OFF, state S2. The test's translation unit is compiled with the define and everything it links is compiled without. Write a script that lists the weak and unique symbols (nm types W, V, u, with sizes: \`nm -S --defined-only\`) defined in the test's own object file, and the same for every object of the libraries and object files on the test's link line (find the link line with \`ninja -C gen -t commands t_amx_dispatch_dtype | tail -1\`). Report: how many symbols are defined both in the test object and in another linked object; for those, how many differ in size; every common symbol whose demangled name contains self_attention, apply_page, apply_dense or amx_attn; and from which object the final binary takes each symbol of namespace tron::amx_attn_h128g4. Say in one or two sentences what this result shows and what it cannot show.
5. Mutations, option OFF, state S2. Purpose: prove that the test, as it now runs in an option-OFF build, fails when the dispatch code is broken. Read h/tron/models/self_attention.hpp and choose at least 6 one-line faults inside the \`#ifdef TRON_AMX_DISPATCH\` regions, each with a different effect (examples: the bf16 eligibility gate inverted, the available() check dropped, the dense-page predicate changed, the pack call skipped, the PV call skipped, the query-group offset of the KV head wrong, the 16-head case sent to the 4-head kernel). For each: apply it, rebuild only t_amx_dispatch_dtype, run it, record the diff line, the exit code and the Catch2 summary, then restore the file with \`git checkout -- <file>\`. A fault that does not compile does not count; choose another one. Then two more cases about the define itself: (m-define-S2) at S2 remove \`DEFINES TRON_AMX_DISPATCH\` from the registration line in t/CMakeLists.txt, rebuild, run, record what happens (compile error, link error, or which sections fail); (m-define-S1) the same at S1, where the placeholder still exists. Use a trap so the tree is restored when the script stops early. At the end: the tree is back at S2 with \`git status --porcelain\` showing nothing but gen, the test is rebuilt and passes again.
6. Option ON, state S2, in the second tree. Build t_amx_dispatch_dtype, t_amx_numerics and t_llama_unit. Run each plain and with the kill switch. Expected from the earlier round at the head: t_amx_dispatch_dtype 30,747 assertions in 1 case (both runs); t_amx_numerics 21,521 assertions in 5 cases with AMX and 6,671 with the kill switch (3 cases pass, 2 skip); t_llama_unit 265,564 assertions in 75 cases. Record the real numbers. Record how often -DTRON_AMX_DISPATCH appears in the compile command of the test's translation unit, and the count of compiler warnings.
7. Registry, read-only, in the option-OFF tree at S2: run \`bin/slice bench --check\` and \`bin/slice bench --check-platform\` the way registry-check-3b35.sh does, and record output and exit codes. Print the two registry rows of t_amx_dispatch_dtype with the names of their machine classes.
8. Load snapshot after. Save it.
9. Write /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/README.md: a "Short version" of at most three sentences, the words used, how to run each script, one results table with every run (state, option, run, exit code, result), the mutation table, the symbol check, the wall times, and a section "Not covered". Plain English, short sentences, every number with its unit. Write a summary record results.txt in the records folder too.

RETURN
Return the structured result. In report, give the full results as text (the tables of step 9), so the caller does not have to open the files. List in skipped every step or part that did not run, with the reason. Give the absolute paths of the records.`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    report: { type: 'string', description: 'the full results as markdown text: every run with exit code and counts, the mutation table, the symbol check, wall times, load snapshots' },
    all_steps_done: { type: 'boolean' },
    skipped: { type: 'array', items: { type: 'string' } },
    surprises: { type: 'array', items: { type: 'string' }, description: 'anything that differs from the expected values named in the task' },
    record_paths: { type: 'array', items: { type: 'string' } },
    trees_clean_at_end: { type: 'boolean' },
  },
  required: ['report', 'all_steps_done', 'skipped', 'record_paths', 'trees_clean_at_end'],
}

function refutePrompt(r, reader) {
  return `${CTX}${NO_MACHINE}
YOUR TASK: you are a skeptic. Another agent (task "${reader.key}") produced the findings below. Try to refute each one. Open the cited files at the cited lines (tree at 90a9110be5 in ${WT}, via git show or git grep with that revision) and re-run the cited read-only commands. A finding holds only when you saw its evidence yourself. When the evidence is missing, wrong, or does not support the verdict, set holds to false and say what you saw. Also name anything important the agent missed for its task; put that in new_issues. Do not repeat the findings; judge them.

THE AGENT'S TASK WAS:
${reader.prompt.slice(reader.prompt.indexOf('YOUR TASK'))}

THE AGENT'S RESULT (JSON):
${JSON.stringify(r, null, 1)}`
}

const [readerResults, build] = await parallel([
  () => pipeline(
    READERS,
    reader => agent(reader.prompt, { label: `read:${reader.key}`, phase: 'Read', schema: FINDINGS }),
    (r, reader) => r
      ? agent(refutePrompt(r, reader), { label: `refute:${reader.key}`, phase: 'Refute', schema: VERDICTS })
          .then(v => ({ key: reader.key, result: r, check: v }))
      : { key: reader.key, result: null, check: null },
  ),
  () => agent(BUILD_PROMPT, { label: 'build-test:delphi-3b35', phase: 'Build and test', schema: BUILD_SCHEMA }),
])

const missing = (readerResults || []).filter(x => !x || !x.result).length
if (missing) log(`${missing} reader(s) returned nothing`)
if (!build) log('the build agent returned nothing')
return { build, readers: readerResults }
