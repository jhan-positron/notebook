export const meta = {
  name: 'pre-pr-check',
  description: 'Check the draft PR body and the branch diff against data, the PR rules and the repository guides before the push',
  phases: [{ title: 'Check' }, { title: 'Refute' }],
}

const COMMON = `
A draft PR is about to be opened in the repository positron-ai/tron. You check it BEFORE it is pushed. Be a skeptic and report only real problems.
Branch: git worktree /home/jhan/workspace/ai-runs/tron-gdn-amx, branch jhan-gdn-amx, 3 commits on top of 72e1191804 (the head of the open PR #3696). Diff: git -C /home/jhan/workspace/ai-runs/tron-gdn-amx diff 72e1191804 HEAD
PR body draft: /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/pr-body.md (written by gen_pr_body.py in the same folder). The commit ids and the unit-test counts in the body will be refreshed once more before the push (a rebuild is running), and one more table row "AMX dispatch off, build type Debug" will be added. Do not report those.
Words: tron = the inference program; GDN = GatedDeltaNet, a recurrent layer type of the model Qwen3.5 4B; AMX = Intel tile-matrix instructions; TTFT = time to first token; arm or binary = one build with one set of switches (base, p0, a0, a, b, ab).
Data behind the body: R = /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/
  R/rt/<cell>__<arm>__rep<N>.log (repetitions 11-13 = the campaign; 21-23 = control runs with arms base, nost, orig), R/collected.json, R/comparison.json, R/comparison-controls.json,
  R/tokens/p<prompt>__<arm>.txt and R/tokens/logits-*.txt, R/unit-tests.txt, R/bench/task3-table-cpu140-run1.txt, R/load/*.txt.
  A log has per user "saw X s TTFT" and "at Y average tok/s", and at exit "[attn-stats] ..." and "[gdn-stats] ..." JSON lines.
Hard rules for you:
- Read-only on everything above. Scratch files only under /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/prepr-<your lens>/ .
- No ssh. Do not touch any machine named delphi-*. No network, no gh, no git push, no git commit. At most 2 processes at a time.
Each finding: where (file and line, or the body section), the exact quote, severity, the problem, your evidence, and the corrected text or code. Also return "checked": what you verified and found correct, with counts.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          where: { type: 'string' },
          quote: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'wrong', 'rule', 'wording'] },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['where', 'quote', 'severity', 'problem', 'evidence', 'fix'],
      },
    },
    checked: { type: 'string' },
  },
  required: ['findings', 'checked'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          quote: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted'] },
          reason: { type: 'string' },
          corrected_fix: { type: 'string' },
        },
        required: ['quote', 'verdict', 'reason'],
      },
    },
  },
  required: ['verdicts'],
}

const LENSES = [
  {
    key: 'body-facts',
    prompt: `Lens: every fact of the PR body. Recompute with your own code and check:
- Performance tables: per cell and binary the mean of the 3 repetitions 11-13 (TTFT = the largest "saw X s TTFT" of a run; decode = mean of the users' "average tok/s"), the change against base in percent, and the mark "inside" (a change is inside when it is not beyond twice the larger sample standard deviation of the two binaries). Also the sentence with the largest standard deviations, and every range in "What the tables say".
- The counter-derived numbers: GDN step in us (busy_cycles / head tokens of the prefill class, cell 1 user prompt 1,024, median of 3 runs is what the body uses), attention busy time factors p0 to b (prefill and decode), join wait values, the share of the decode fall that is join wait, and the control-run numbers (decode with the counters on against off, the spread, counters off against the PR base).
- Token table and its bullets from R/tokens (tokens and best scores).
- Unit-test counts against R/unit-tests.txt (rows of build pab).
- The numerics claim in "How to review this PR" against R/bench/task3-table-cpu140-run1.txt.
- Every code name in the body exists at the head with that spelling and meaning: Note names, file paths, functions (gdn_recurrence_slice, advance, step, run_gdn_operation, advance_window_with_block_kernel, amx_serves_128x4, amx_serves_256x4, namespace amx_attn_h256g4), test case names in quotes, environment variables, the model name, the test program names.
- Every sentence that says what the code does: read the code and confirm (for example "step() keeps the token kernel for chains of 1 token", "the kill switch turns both shapes off", "a refused block leaves the state untouched", "The code of the three 128-wide kernels has no change" against git show 72e1191804:src/tron/kernels/amx_attn.cpp).
- The diff size sentence (added lines, files).`,
  },
  {
    key: 'body-rules',
    prompt: `Lens: the rules for the PR body. Read /home/jhan/.claude/skills/PR-description/SKILL.md and its references/example-how-to-review.md, and /home/jhan/.claude/skills/plain-english/SKILL.md. Check the body against every rule and the self-check list of the PR-description skill, and run the plain-english Check mode on it.
Count the words the way the skill says: awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' pr-body.md | wc -w (limit: under 2,000).
Things that authors often miss: a fact stated in two sections; a term in the Words table that is used in only one section, or a project term used in more than one section that is missing from the table; change history or "before / after" wording; clock times; paths into the author's workspace; names of people; the words "pull request"; a section pointer inside the Short version; more than three bold questions in "How to review this PR" or a question without a "Verification:" bullet; a table interpretation that does not start with the line "What the table says:"; an Open item that nobody must act on before merging; an Open item that restates a question of section 4; a sentence with two claims; a sentence above 25 words; an idiom; a number without unit; a term used before its definition. Also check the project term list in /home/jhan/workspace/intel-AMX/CLAUDE.md: terms such as kill switch, bf16, AMX and AVX need a definition at first use.
Give the corrected sentence for every finding. Keep the body under the word limit: when a fix adds words, say what to cut.`,
  },
  {
    key: 'repo-guides',
    prompt: `Lens: the repository's own rules, applied to the diff. Read /home/jhan/workspace/ai-runs/tron-gdn-amx/AGENTS.md, t/AGENTS.md, ingest/AGENTS.md, .github/AGENTS.md, .agents/skills/random-numbers/SKILL.md, .editorconfig and lefthook.yml in that worktree. Then check the diff (22 files) against them. Look for:
- C++ library use beyond libstdc++ 12 (the guide lists the traps), <cassert> in place of h/common/assert.hpp, the NaN rule.
- The test policy: every added test file must be collected and executed by a required CI suite (read t/CMakeLists.txt, config/, README.ci.md, .github/workflows and the slice configuration to prove that the cases of t/t_amx_gdn_numerics.cpp and t/t_gdn_stats.cpp run in CI, and whether the AMX cases really execute there or skip); tests that the policy forbids (tautologies, tests that derive the expected value from the code under test, tests that document the implementation, regression tests for mistakes made inside this change); the rule to refresh config/test-benchmarks.json.
- The random-number rules in the new tests.
- The ingest guide for the change in ingest/src/TronCpp.hs (does a generated file or a golden file need a refresh? is a Haskell test or format target required?).
- The public API rule (h/libtron.hpp and what it exports).
- Anything the direct CI lint checks in flake.nix would reject (read the lint checks there: formatting of every changed language, whitespace, spelling, prohibited headers, license or header rules, shell or markdown lint for README changes).
- The PR CI policy for labels and draft state.
Report a violation only with the rule text and the offending lines. Say "blocker" only for something that makes CI lint fail or breaks a stated must-rule.`,
  },
  {
    key: 'reviewer-eyes',
    prompt: `Lens: the first impression of the reviewers. Read /home/jhan/.claude/skills/folks-code-review/SKILL.md and apply its claim checks and scope checks (and any check that needs only reading) to the PR body and the diff. Also read the three commit messages (git log 72e1191804..HEAD --format=%B) and check them against the diff of each commit: does each message say what its commit does, in present tense, with no stale statement (for example a counter name, a file or a test that the commit does not have)? Does any commit contain a hunk that belongs to another commit (check with git show --stat for each)? Does the first commit build a meaningful unit on its own (does it reference kernels or paths that only a later commit adds)?
Look also for: debug switches or leftover debug code in the diff, comments that contradict the code, comments that cite an issue or PR number or a person, TODO lines without an owner, files that should not be in the PR, and statements in README.stats.md or README.ci.md that the code does not support.
Report at most 15 findings, the most important first.`,
  },
]

const results = await pipeline(
  LENSES,
  l => agent(COMMON + '\n' + l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (found, l) => {
    if (!found || !found.findings.length) return { lens: l.key, checked: found ? found.checked : 'agent failed', findings: [], verdicts: [] }
    return agent(COMMON + `\nAnother checker (lens: ${l.key}) reported the findings below. For EACH finding, try to REFUTE it by reading the file, the rule text or the data yourself. Verdict "refuted" when the finding is wrong, "partly" when the problem is real but smaller, "confirmed" when it is right. Give a corrected fix when the proposed one is wrong. Copy the "quote" field of each finding into your verdict.\n\nFindings:\n${JSON.stringify(found.findings, null, 1)}`,
      { label: `refute:${l.key}`, phase: 'Refute', schema: VERDICTS })
      .then(v => ({ lens: l.key, checked: found.checked, findings: found.findings, verdicts: v ? v.verdicts : [] }))
  }
)
return results.filter(Boolean)
