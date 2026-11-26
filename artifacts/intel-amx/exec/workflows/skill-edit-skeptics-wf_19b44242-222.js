export const meta = {
  name: 'skill-edit-skeptics',
  description: 'Three skeptics review the proposed edits to the review skills: false positives, technical correctness, form and consistency',
  phases: [
    { title: 'Review the edits', detail: 'three independent lenses on the diff between the unedited and the edited skills' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/skill-replay-20261123'
const A = '/home/jhan/workspace/ai-runs/skill-miss-analysis-20261123'
const WT = R + '/tron-ddf843ad97'

const SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['install as is', 'install after the required changes', 'rework'] },
    required_changes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          quoted_text: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          replacement_text: { type: 'string' },
        },
        required: ['file', 'quoted_text', 'problem', 'evidence', 'replacement_text'],
      },
    },
    optional_changes: {
      type: 'array',
      items: {
        type: 'object',
        properties: { file: { type: 'string' }, quoted_text: { type: 'string' }, suggestion: { type: 'string' } },
        required: ['file', 'quoted_text', 'suggestion'],
      },
    },
    cases_walked: {
      type: 'array',
      items: {
        type: 'object',
        properties: { case: { type: 'string' }, what_the_text_prescribes: { type: 'string' }, correct: { type: 'string', enum: ['yes', 'no', 'unclear'] }, why: { type: 'string' } },
        required: ['case', 'what_the_text_prescribes', 'correct', 'why'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['verdict', 'required_changes', 'optional_changes', 'cases_walked'],
}

const COMMON = `
Context. A reviewer found that a test of tron PR 5022 (t/t_amx_dispatch_dtype.cpp) sits under '#ifdef TRON_AMX_DISPATCH' with a placeholder case in the '#else' arm, so the required CI lane, which builds with that CMake option OFF, runs none of its real assertions. His fix gives the one test target the compile definition (DEFINES in add_catch_test) and deletes the placeholder. Our review skills detected the gap several times and never named that fix. The edits below are meant to make the skills name it, rate it, and keep a finding open after a fix is declined.

Files:
- Unedited skills: ${R}/skills-baseline/ (tron-code-review, cpp-coding-guide, folks-code-review with references/procedures.md, ben-review, positron-code-review)
- Edited skills: ${R}/skills-candidate/ . See every edit with: diff -r ${R}/skills-baseline ${R}/skills-candidate
- The script that made the edits (old text and new text side by side): ${A}/tools/apply_candidate.py
- The finding and the fix, verbatim: ${A}/finding.md
- tron at the head of PR 5022: git worktree ${WT} (read-only)
- Reports that the edits were drawn from (JSON): ${A}/out/analyse_skill-tron-code-review.json, analyse_skill-folks-code-review.json, analyse_skill-cpp-coding-guide.json, analyse_repo-facts.json, verify_repo-facts.json, analyse_reviewer-method.json, analyse_history-november.json, verify_history-november.json

Rules: read-only. Do not edit any file, build, run tests, or use the network. Use 'git -C <path>' and full paths; do not cd. Quote the exact text you object to. Give replacement text that can be pasted. A required change needs evidence: a file and line of the repository or of a skill, or a command with its output. Do not ask for a change because of taste. Your default position is that the edit is wrong or harmful until the text and the repository show otherwise.
`

const LENSES = [
  {
    key: 'false-positives',
    prompt: `
Task: find where the edited skill text would make a reviewer raise a wrong finding or prescribe a wrong fix.
${COMMON}
Walk these cases through the edited text of tron-code-review (section "Review the tests"), folks-code-review (check 3A form (f), its steps 16 to 20 in references/procedures.md, check 7, check 35, the last bullet of "Replying to Wade", Setup steps 3, 5 and 6) and cpp-coding-guide (section "Tests behind a build option"). For each case say what the text prescribes and whether that is correct. Put each case in cases_walked.
1. t/t_amx_dispatch_dtype.cpp at the head, new 16-head sections under the guard. Expected: finding, per-target define, delete the placeholder, before the merge.
2. t/t_amx_numerics.cpp at the head, new 16-head sections under the guard at line 82. The Q-pack case needs the kernel source file. The QK and PV cases need the kernel source file and AMX hardware. The gate case needs neither. Expected: no per-target define for the kernel cases.
3. A hypothetical PR that adds a test case inside '#ifdef HBM_ALLOC_SHADOW' in t/t_hwalloc.cpp (line 423 region). The macro changes src/pos/alloc.cpp, src/pos/driver.cpp and the class layout in h/pos/alloc.hpp. No preset and no workflow sets the option. Expected: the gap is reported, and no per-target define is prescribed.
4. A hypothetical PR that adds a case inside the address-sanitizer guard of t/t_heap_v2.cpp (line 1343 region). Expected: not this check (a compiler feature).
5. A hypothetical PR that adds a case inside '#ifdef DUMP_MATPLOT' in t/t_generate_host_2.cpp (line 54 region), which the source calls a manual switch.
6. A hypothetical PR that adds a case inside a model macro guard of t/t_generate_host.cpp (line 123 region) or t/t_rinzler.cpp. The registration sets the macro when the model is selected, and the required lane builds with TRON_REQUIRE_ALL_MODEL_TESTS=ON.
7. A PR that changes only production code under '#ifdef TRON_AMX_DISPATCH' in h/tron/models/self_attention.hpp and adds no test unit.
8. A PR that adds a test with the 'fpga' label, which runs in the FPGA job of the required workflow.
9. A reviewer proposes a fix, the author declines it with a reason, and the checks REFUTE the reviewer's claim. Expected: no search for another fix.
10. A reviewer's preference ("nit", "maybe") that the author declines.
11. A bot marks a finding optional, and the claim rests on no written repository rule.
Then look for cases of your own in the repository where the text misfires: 'git -C ${WT} grep -n -E "^#if" -- t' lists the candidates. Also check each "Do not fire on" and "Do not flag" list for a missing exclusion and for an exclusion that would hide the PR 5022 finding itself.
`,
  },
  {
    key: 'technical-correctness',
    prompt: `
Task: check every technical statement and every command in the edited skill text against the repository.
${COMMON}
Check each of these and report every error as a required change.
1. Every command of steps 16 to 20 in ${R}/skills-candidate/folks-code-review/references/procedures.md. Run each one on the worktree at the head with the placeholders filled for t/t_amx_dispatch_dtype.cpp and TRON_AMX_DISPATCH (WT = ${WT}, BASE = 3bea58b788, HEAD = ddf843ad97; where a command reads 'full/<file>', read the file in the worktree). Does each command run, and does it return what the step says? Quote the output. Check the regular expressions for lines they miss or wrongly match (for example an indented '#  ifdef', a 'target_compile_definitions_if_target' call, an option declared in a subdirectory CMakeLists.txt).
2. The line numbers and facts of the paragraph "On PR 5022 at ddf843ad97" in the same file. Check each one.
3. How add_catch_test applies DEFINES (t/CMakeLists.txt) and which other ways give one test target a definition. Does the edited text name them correctly?
4. The precondition for a per-target define. The edited texts say, in three wordings, that no linked library built without the definition may compile a class, a template instance or an inline function that the macro changes and that the test also uses. Is this precondition correct and sufficient under the C++ one-definition rule? Is it checkable by reading? Is the folks wording (step 5 of form (f), and step 19) consistent with the tron-code-review wording and the cpp-coding-guide wording? Check it against t_amx_dispatch_dtype (expected: safe in practice) and t_hwalloc with HBM_ALLOC_SHADOW (expected: unsafe).
5. "Then delete the guard and its placeholder arm". With the global option ON the tron library holds the real kernel object, and the test defines fakes with the same names. Does the test still link and run its fakes then? Read the test's header comment, the registration and src/tron/CMakeLists.txt. State what you could verify by reading and what needs a build.
6. The statements about the repository policy: quote AGENTS.md "Test policy" at the head and compare with the paraphrases in the edited tron-code-review, in Setup step 3 of folks-code-review and in form (f).
7. The statement in procedures.md that GraphQL prints a bot login without the '[bot]' suffix. Evidence at hand: a GraphQL query of PR 5022 on 2026-11-23 returned author login 'claude' with __typename 'Bot' for the two bot threads. Is the edited filter text correct and complete?
8. The claim in tron-code-review that a lane "still reports a pass when the other arm of the guard holds a placeholder case that only calls SUCCEED, or when another case of the program passes". What does a Catch2 program with zero test cases return? The pinned Catch2 source is not in the worktree unless fetched; say what you can verify.
9. Any statement in the edits that is true only for PR 5022 and is worded as general.
`,
  },
  {
    key: 'form-and-consistency',
    prompt: `
Task: check the edited skills for internal contradictions, for breaks of each skill's own form, and for breaks of the author's writing rules.
${COMMON}
Check each of these and report every defect as a required change with replacement text.
1. Contradictions inside folks-code-review after the edit. Read the whole edited SKILL.md. Examples to test: Setup step 5 ("at most an informational fwiw line") against form (f); the exclusion of check 3A "a run as remedy (move the assertion; missing run: 3B)" against form (f); check 3A's severity line ("Questions, non-blocking, except form (d)") against the must-change of form (f); check 35's "never a blocker" against its new step 7; the reply rules for Wade against the new last bullet; the count sentences ("35 checks", "The thirty-six questions") and the description in the front matter (limit 1,024 characters; count it).
2. Form. folks-code-review writes each check as Trigger, Procedure, Question, Do not fire on, Finding shape, Severity and precedent. tron-code-review writes prose paragraphs with short lists and a provenance sentence with links. cpp-coding-guide writes a scope paragraph, rule bullets and one cpp block with a wrong and a right version. Does each edit follow the form of its skill?
3. Writing rules. The author's rules for prose are in /home/jhan/.claude/skills/plain-english/SKILL.md (you may read this one file under ~/.claude). Check every added sentence: no idioms or metaphors, one claim per sentence, short sentences, every term defined at first use (for example "required lane", "gating lane", "placeholder case", "guard", "fake", "option-only source"), numbers with units. List each violation with the exact phrase and a corrected version.
4. Duplication and size. The same rule now stands in three skills. Is each copy needed, or should one skill own the rule and the others point to it? State the size of each edit in lines and in characters ('diff | grep -c' and 'wc -c'). Name text that can be cut without losing a rule.
5. Would the edited text have changed the outcome at each step of the record? Read ${A}/out/analyse_history-november.json and its verification. Steps: the reply of 2026-10-19 that said the cases "need" the Nix flag; decision card D1; the edit pass of 2026-11-20 03:18 to 03:22 UTC; the pre-review prompt that listed the Nix flag under "Already decided by the author; do not report these as findings"; the bot finding r4645384802. For each step name the sentence of the edited skills that applies, or state that none applies. A step that no sentence covers is a required change.
6. The author's standing rules that the edits must not break (from the record): replies to reviewers stay simple and short; nothing is posted without the author's approval; scope additions to a PR need tests and the author's decision. Does any added sentence push against these? Quote it and reword it.
`,
  },
]

const results = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: 'skeptic:' + l.key, phase: 'Review the edits', schema: SCHEMA }).then(r => ({ key: l.key, review: r }))))
return { reviews: results.map((r, i) => r ? r : { key: LENSES[i].key, review: null }) }
