export const meta = {
  name: 'numeric-rounding-verify',
  description: 'Five independent checkers verify the new handoff, the update of the split handoff and the two GitHub comment texts',
  phases: [{ title: 'Verify', detail: 'five read-only checkers, each with its own lens' }],
}

const ROOT = '/home/jhan/workspace/smaller-tasks/numeric-rounding'
const NEW = `${ROOT}/handoff-numeric-rounding-20261123.md`
const SPLIT = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md'
const SPLIT_BEFORE = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/handoff-gdn-pr-split-20261122.before-20261123.md'
const C4444 = `${ROOT}/drafts/comment-4444-20261123.md`
const C5433 = `${ROOT}/drafts/comment-5433-draft.md`

const FINDINGS = {
  type: 'object',
  properties: {
    verdict: { type: 'string', description: 'one or two sentences: is the checked text fit for its purpose' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['wrong', 'unsupported', 'contradiction', 'missing', 'unclear', 'style'] },
          file: { type: 'string' },
          location: { type: 'string', description: 'section and a short quote of the passage' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'the command output, file:line or URL that shows it' },
          fix: { type: 'string', description: 'the exact replacement text or the exact change' },
        },
        required: ['severity', 'file', 'location', 'problem', 'evidence', 'fix'],
      },
    },
    confirmed: { type: 'array', items: { type: 'string' }, description: 'the most important claims you checked and found correct, one line each' },
  },
  required: ['verdict', 'findings', 'confirmed'],
}

const COMMON = `
You are an independent checker. Your job is to find what is wrong, unsupported, contradictory, missing or unclear. Do not defend the text. If you cannot verify a claim, report it as "unsupported" and name the source that would settle it. Do not report a point you have not checked.

## Setting
- jhan is an engineer. A Claude session (the "writing session") wrote three things today, 2026-11-23, on jhan's request. The request, word for word:
  "Some updates and may need you to update the handoff files:
  - Please check slack chats with Runar, Ben and Bill. Runar has no plan to merge PR3696 soon and asked us to use its branch
  - In separate message, he mentioned issue 5433 and PR 5571. I think it is similar to one issue we created when working at first batch of AMX PRs. Please update our issue if you believe it is tightly related.
      - please create a new handoff, another agent will investigate this from your handoff. Write the handoff file to a new folder under ~/workspace/smaller-tasks, this new folder will be the root to work on the numeric rounding issue. And I think we need to update the exiting handoff, handoff-gdn-pr-split-20261122.md if the numeric rounding issue is mentioned"
- The Slack chat (group chat, 2026-11-23, PST), word for word:
  10:53 jhan: "Good morning Runar! I like to get a high level estimate of qwen3.5-4b schedule. The context is, Bill asked me to look into leveraging AMX for GDN. My measurement showed promising prefill boost by introducing AMX. qwen model as in PR3696 is not merged, so I like to get a rough read of your plan. It is not blocking me as I need to refine the code and do more testing, just want to have an idea."
  10:57 GDN owner: "My guess is mid-to-late December at the current rate, which is limited by review pace."
  10:58 GDN owner: "You don't have to wait for it though. The GDN kernels are already on main (h/tron/kernels/gated_delta_net.hpp), so the AMX work can branch from main, and you can run Qwen3.5 4b end-to-end from the #3696 branch"
  10:59 jhan: "Yes, I will use this strategy"
  10:59 GDN owner: "Heads up though that #3221 (not merged) parallelizes GDN across key-head groups, which changes how the kernel is driven, and we're measuring whether to drop some of the rounding inside the layer (issue #5433, draft PR #5571)"
- The files:
  - NEW handoff: ${NEW}
  - its six fact files: ${ROOT}/handoff-material/facts-{rounding,port,4444,method,parta-options,stack}.md (written by read-only fact readers today; they can hold errors too)
  - the comment for our issue #4444 (to be POSTED on GitHub today): ${C4444}
  - a draft comment for the GDN owner's issue #5433 (NOT to be posted now): ${C5433}
  - the SPLIT handoff, updated today: ${SPLIT}
  - the split handoff before today's update: ${SPLIT_BEFORE} (use "diff" to see exactly what changed)
- Repository positron-ai/tron, shared local clone /home/jhan/workspace/tron (fetched today). READ ONLY: use "git -C /home/jhan/workspace/tron ..." with read-only commands. No fetch, checkout, commit, stash, gc, and never "git worktree prune". Our code: worktree /home/jhan/workspace/ai-runs/tron-gdn-amx at 882e5322f1 (read only).
  Commit ids: main f454423b09; model's branch (PR #3696) 72e1191804; PR #3221 head 127a662083; PR #5571 head 69cc70fae0 (code commit 59429b0955); our commits 0d69ef3ce8 (counters), 775bba7661 (Part 0 + Part A), 882e5322f1 (Part B).
- GitHub: "gh ... --repo positron-ai/tron" for READING only. Never comment, edit, label, close or create anything.
- Do not use ssh unless your task says so. Do not build. At most 6 CPU threads. Do not change any of the files you check: report, do not fix.
- jhan's writing rules (the plain-english skill, /home/jhan/.claude/skills/plain-english/SKILL.md): a "Short version" of at most three sentences first; one claim per sentence; short sentences; no idioms or metaphors; every code name, abbreviation and metric defined at first use; numbers with units; estimates marked "est."; references as bracket indexes with a reference list at the end. For GitHub text also: no names of people and no @-mentions (roles and links only), "PR" never "pull request", no paths into the author's workspace. Banned words: convoy, refund, swept, "in disguise". Write "prompt 1,024" style, never "ctx".

## Output
Return the structured result. Put the most serious findings first. For each finding give the exact replacement text where you can. Keep "style" findings to the ones that would make a reader stumble; do not list every long sentence.
`

const TASKS = [
  {
    key: 'new-facts',
    prompt: `
## Your lens: every factual claim of the NEW handoff
Read ${NEW} in full. For each factual claim (numbers, commit ids, line numbers, quotes, counts, states of PRs and issues, what code does, what was measured) find its support:
1. in the fact file that the bracket reference names, and
2. for the claims a wrong value of which would mislead the next agent, in the primary source itself: the code (git show <commit>:<path>), GitHub (gh issue view 5433 --comments, gh pr view 5571, gh pr view 3696, gh issue view 4444 --comments), or the result files (/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/collected.json, /home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-*.json, td2-20261016, glimext-20261018/margin).
Check with priority: the rounding table of section 3.2 (22 calls: rows, which go, which are "the six"); section 3.3 (the three pack places and their lines at 882e5322f1, the missing check, the test that would fail); the option table of section 3.4 (tile-product counts 18.5 / 38.0 / 58.5 by the loops of src/tron/kernels/amx_gdn.cpp); the TTFT table of section 3.4 (recompute the six falls from collected.json: which arms, medians of 3); the quotes of section 3.5 against the issue comment; the TVD table of section 3.6 (recompute the means from the steps-*.json files: mean of steps[].tvd; the count of steps where same_top1 is false); section 3.7 (the 12 open PRs and their order: gh pr view each for baseRefName/headRefName; "lower 7 rewritten on 2026-11-23"); section 3.8.
Also check: does any statement present a reading or an estimate as a fact? Does the handoff contradict one of its fact files? Do the fact files contradict each other on a point the handoff uses?
`,
  },
  {
    key: 'new-fresh-agent',
    prompt: `
## Your lens: you are the agent that receives the NEW handoff and must do the work
Read ${NEW} as if you knew nothing else. Then try to start, read-only:
1. Does every path that the handoff names exist (ls each one)? Do the scripts it names exist and take the inputs it says (read build.sh, run-one.sh, token-check.sh, logit-margin.sh in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121 and ../gdn-20261120; dd_logits_step.py in /home/jhan/workspace/intel-AMX/exec/dd)? Is the advice of section 6.3 on copying and changing EXEC, NAME and RES correct for each script (which variables are really fixed in each script text)? Would a build tag that starts with "nr" pass the tag check of build.sh? Would build.sh, copied to another folder, still find the model list file and the repository?
2. Run the read-only commands of section 5.1 except the ssh line (for the ssh line you MAY run exactly this read-only form: ssh -o BatchMode=yes delphi-3b35 'ls -d /var/tmp/jhan/b35-gdn-*; df -h /var/tmp/jhan | tail -1'). Do they work as written? Do they give the ids the handoff expects? Note: "git fetch" is in that list; do NOT run the fetch.
3. Is the worktree command of section 6.3 correct for git 2.34.1 (check "git worktree add -h")? Would a worktree under ${ROOT}/work/ be reachable from delphi-3b35 for build.sh (build.sh makes its own worktree from a commit id: read how)?
4. For each question N1 to N7: could you tell when you are done? Is a needed input missing (a text for the forced run, the options of runtron such as --force-feed-text-token-file, --intermediates-file, --output-token-file: check they exist in the runtron sources at 775bba7661 with git grep)? Is the plan of sections 5.2 to 5.6 doable in the order given, and is any step impossible as written (for example tree B "rows 6 to 11 removed in normalize_gdn": look at the function at 775bba7661 and say whether "remove rows 6 to 11 but keep row 5" is a well-defined edit; tree C: is "the block kernel's window gets K and Q rounded once" well defined against the code of gdn_prepare_recurrence_token and advance_window_with_block_kernel)?
5. Section 7: is it clear what you may and may not do? Is anything that the plan needs forbidden by section 7, or anything risky left allowed?
6. Is any term used before it is defined, or never defined? Is the Short version at most three sentences, and can a newcomer follow it?
7. What would you have to ask jhan that the handoff does not let you answer yourself, beyond S1 to S4?
`,
  },
  {
    key: 'split-update',
    prompt: `
## Your lens: today's update of the SPLIT handoff
Run: diff ${SPLIT_BEFORE} ${SPLIT}
Read the whole updated file ${SPLIT} (it is long; read all of it, because the task is to find contradictions between the new parts and the old parts).
1. Facts of the new section 0 and of every changed passage: check them against ${ROOT}/handoff-material/facts-stack.md, facts-port.md, facts-rounding.md and, where a wrong value would mislead, against git and gh (the 12 open PRs between main and PR #3696 and their order; main f454423b09; which files of our commits exist on main; "12 conflict regions in 5 files"; "The registration and 8 more PRs are above it"; the reboot facts cannot be checked without ssh: mark them unchecked, not wrong).
2. The Slack quotes of section 0.1 against the chat text in your setting. Is the description of the difference between the GDN owner's advice and jhan's sentence fair and neutral?
3. Contradictions between new and old text. Look for: old passages that still state something that section 0 changes (the id of main elsewhere in the file; "PR 1 to PR 3 form a stack on the branch of #3696" in comment texts while Q4 is open; the "done" criteria of section 1 that count four open PRs while Q5 may hold PR 3; section 3 "The go covers ... opening the four draft PRs"; section 5 steps 1, 11, 12, 13 against Q4 and Q5; section 9 report; the stop rule of section 3). For each, say whether a reader would be misled and give the exact fix.
4. Is the flow of the five start questions Q1 to Q5 complete and free of dead ends? Walk through every combination that matters (Q2 yes/no/none times Q5 now/hold/none; Q4 model's branch / main / none) and say what the file tells the agent to do in each. Name any combination where the file gives no instruction or two instructions.
5. Is the "writing session's view" on Q4 and on Q5 clearly marked as a view and not as jhan's decision? jhan decided D1 to D10 on 2026-11-22; does the update reopen any of them without saying so?
6. Do all bracket references [R1] to [R21] that the text uses have an entry in the reference list, and is every entry used?
7. Writing rules: only findings that would make the next agent stumble.
`,
  },
  {
    key: 'comments',
    prompt: `
## Your lens: the two GitHub texts
A. ${C4444} will be posted today as a comment on issue #4444 (our issue). Read the issue with its three comments first (gh issue view 4444 --repo positron-ai/tron --comments), and issue #5433 with its two comments, and issue #4600.
   1. Check every number: recompute the TVD table from /home/jhan/workspace/intel-AMX/exec/results/td-20261016/steps-*.json, /home/jhan/workspace/intel-AMX/exec/results/td2-20261016/steps-*.json and /home/jhan/workspace/intel-AMX/exec/results/glimext-20261018/margin/steps-base-vs-head.json (mean and max of steps[].tvd; steps where same_top1 is false). The row-to-file mapping: "AMX on against the kill switch, main" = steps-baseoff-vs-base.json; "P rounded against P truncated" = steps-new-vs-trunc.json; "AMX add order against AVX-512 add order" = steps-newoff-vs-trunc.json; "row-major binary against main with the kill switch" = steps-clean-vs-baseoff.json; "AMX on against the kill switch, probe commit" = steps-new-vs-newoff.json (td-20261016 for prompt 1024, td2-20261016 for prompt 8192); Glimmer = glimext file. Check what each arm really is: read /home/jhan/workspace/intel-AMX/exec/td-20261016/ scripts (probe-td.sh, build-variant.sh, analyze-td.sh) and the report /home/jhan/workspace/intel-AMX/token-divergence-4444/token-divergence-issue4444-report.html (strip the tags with python3) for the definitions of the arms new, newoff, base, baseoff, clean, trunc. Is each pair described correctly in the comment (what differs: add order, rounding of P, both)? Is "the PR #4959 probe commit ea94e95a4e" right? Are the median margins "19.75 logit units at prompt 8192 and 3.9 at prompt 1024" in the report or the files? Is "about 700 times" right?
   2. Check the statements about the code and the tests: "The golden-logit tests on main force 21 tokens (Llama 3.1 8B) and 9 tokens (Muse Glimmer)" (git show f454423b09:t/t_generate_ingest_1_llama.cpp and ...muse_glimmer.cpp); "the kill-switch run equals the row-major binary in all 256 compared score vectors" (report); "#4600 ... names this issue"; "The truncation is still on main" (git show f454423b09:h/tron/models/kv_cache.hpp, interleave_bf16_ps); "#5433 and its trial, draft PR #5571, change no attention file"; the last bullet on draft PR #5572 (is PR #5572 open and a draft: gh pr view 5572; does its kernel read key and query as bf16 values: src/tron/kernels/amx_gdn.cpp in the worktree; is "By our reading" a fair hedge).
   3. Does the comment say anything that the facts do not carry, or that a reader of issue #4444 would misread? Is the comparison table fair to issue #5433 (read its text)? Does the comment make a promise or a request that jhan did not approve (jhan asked only to update our issue if the two are tightly related)?
   4. Rules for GitHub text (in your setting): names of people, @-mentions, "pull request", workspace paths, undefined terms, idioms, a Short version of more than three sentences. Check that the two links in the comment resolve (gh api repos/positron-ai/tron/issues/comments/7083755152 and .../6255615621).
   5. Is "tightly related" the right word for the two issues, from the facts? Give your own judgment in the verdict in one sentence.
B. ${C5433} is a draft for the GDN owner's issue. It is NOT posted now. Check its numbers against /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/collected.json (TTFT medians of 3 for the arms with the chain kernel and with the block kernel in the six cells; find the arm names in the file and in /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/collect.py), its tile-product counts against src/tron/kernels/amx_gdn.cpp (loop bounds of the stages), and its statements about issue #5433 against the issue text. Say what must change before it could be posted, and what in it would annoy or mislead the owner of the issue.
`,
  },
  {
    key: 'completeness',
    prompt: `
## Your lens: did the writing session do what jhan asked, and is anything missing or misread
Read jhan's request in your setting again, slowly. Then read ${NEW}, the diff of the split handoff (diff ${SPLIT_BEFORE} ${SPLIT}), ${C4444} and ${C5433}.
Answer with findings:
1. "Please check slack chats with Runar, Ben and Bill." The writing session found one group chat. Is the content of that chat fully and correctly carried into the split handoff (section 0.1) and, where it matters, into the new handoff? jhan's own summary of the chat ("has no plan to merge PR3696 soon and asked us to use its branch") differs from the chat text. Is that difference stated plainly and without blame, and is the open choice put to jhan (Q4)? Is the default the right one?
2. "Please update our issue if you believe it is tightly related." Which issue is "our issue"? The writing session chose issue #4444 ("AMX and VNNI attention: token divergence against the row-major binary, and the kill-switch rollback contract"). List jhan's own issues (gh issue list --repo positron-ai/tron --author jhan-positron --state all --limit 60) and say whether another issue fits "similar to issue 5433 / PR 5571" and "created when working at first batch of AMX PRs" better. Then: is the planned comment the right kind of update (a new comment, like the three earlier status comments on that issue), and does it say why the two are related and where they are not?
3. "please create a new handoff, another agent will investigate this". Is the investigation that the new handoff defines (N1 to N7) a fair reading of "investigate this" and of "the numeric rounding issue"? What would a reasonable reading include that the handoff leaves out, and what does the handoff include that jhan did not ask for? Is it clear in the handoff that the scope is the writing session's proposal and that jhan confirms it (S1)?
4. "Write the handoff file to a new folder under ~/workspace/smaller-tasks, this new folder will be the root". Check the folder and its layout (ls -R, at most two levels). Is the root used consistently as the place of all future work of that task?
5. "we need to update the exiting handoff ... if the numeric rounding issue is mentioned". Search the updated split handoff for every place that speaks of numerics, rounding, bit-identical results or the numerics rule (grep -n -i -E "numer|round|bit|bf16 step|tie|contract"). Is each such place consistent with the news? Is a place missed?
6. Decision-changing facts that jhan must hear in the final chat reply. List them in order of weight (at most eight), each in one sentence, and mark the ones that need jhan's decision.
7. Anything the writing session should NOT have done or should not do (for example posting on the GDN owner's issue, or changing the plan that jhan decided on 2026-11-22).
`,
  },
]

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: `verify:${t.key}`, phase: 'Verify', schema: FINDINGS })
    .then(r => ({ key: t.key, result: r }))
))
return results.filter(Boolean)
