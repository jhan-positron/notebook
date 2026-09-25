export const meta = {
  name: 'verify-first-amx-ci-row',
  description: 'Adversarially verify the claims about the first nightly AMX-benchmark row (28.3 TPS) vs our l8b-8u4k measurement',
  phases: [
    { title: 'Refute', detail: '3 lenses per claim: data re-check, confounds, interpretation' },
    { title: 'Critic', detail: 'completeness critic over all verdicts' },
  ],
}
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-CI-test/23fd8660-e9b4-4144-9475-e2c0f3397e73/scratchpad'
const CONTEXT = `
You are verifying one claim made by another agent about last night's System CI run. Evidence files (read them, they are the primary sources):
- ${SCRATCH}/facts.md : the collected facts with sources (Slack text, ssh output from delphi-3bda already captured there: DO NOT ssh to delphi-3bda yourself, it is a shared CI machine; use the captured output).
- ${SCRATCH}/nightly-35683952944.log : full log of the 3bda nightly run 35683952944 (systems_test, 2026-09-22). The 32-user llama-8b row config starts at line 1211; 'Done (TTFT=..., X / 140.00 TPS)' lines are the per-request samples; 'Running averages' lines close each of 10 rounds.
- ${SCRATCH}/nightly-genoa-35682128668.log : same for the AMD machine andoria-b1a3.
- ${SCRATCH}/nightly_rows.json and parse_row.py : the other agent's parse of the rows (re-derive independently, do not trust it).
- /home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920/summary.json and summary.txt : our 2026-09-20 measurement of the same cell (base = nightly deb 3faba6d0 without AMX, canon = same main + AMX kernels compiled in). Per-pass perf.json files live in base-pass*/ and canon-pass*/ under the same directory.
- /home/jhan/workspace/intel-AMX/exec/l8b-8u4k-20260920/configs.py : our cell config. /home/jhan/workspace/intel-AMX/exec/l8b-8u4k-20260920/prompt.py.patch : our prompt-source change.
- /home/jhan/workspace/ai-runs/systems_test-pr221 : a clone of systems_test; 'git show origin/main:scripts/perf.py' has the merged 32-user config (lines ~73-86); 'git show origin/main:testlib/prompt.py' has Rhys's prompt selection. Do not modify this clone.
- gh CLI works: e.g. 'gh pr view 4505 --repo positron-ai/tron --json state,mergedAt', 'gh run list --repo positron-ai/tron --workflow publish-deb.yml --limit 8', 'gh pr view 221 --repo positron-ai/systems_test --json mergedAt'.
- Memory notes with verified background: /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/{l8b-8u4k-20260920-campaign,nightly-amx-check-20260916,ci-enable-20260917-campaign,pr221-rhys-amx-benchmark-review,l8b-levers-20260919-campaign}.md
Rules: work read-only. Quote the exact evidence (file:line, command output) for every statement. Default to refuted=true only if you found concrete contrary evidence; if the claim holds but a number or wording is imprecise, set refuted=false and list the correction. Do not speculate without naming what measurement would settle it.`
const CLAIMS = [
  { id: 'C1', text: "The 3bda nightly run of 2026-09-22 (systems_test run 35683952944) executed tron package 2026.09.18-3faba6d0, whose rinzler binary contains no AMX code (0 AMX tile instructions, no TRON_AMX_DISABLE getenv literal) and is byte-identical (sha256 27e6883c...) to the binary our l8b-8u4k base arm ran on 2026-09-20. Therefore the row labelled 'AMX benchmark' measured a binary without AMX." },
  { id: 'C2', text: "The merged systems_test 32-user row (perf.py: nominal_users 32, prompt_length 4096, generate_length 1536, start_capture 896, end_capture 1024, prompt_mode sharegpt, shared_prompt_length 0, 4 engines behind Caddy = 8 users per engine) has the same load shape as our l8b-8u4k cell (exec/l8b-8u4k-20260920/configs.py). The known differences are: prompt SOURCE (Rhys appended 320 long ShareGPT records; we concatenated conversations), platformd 0.11.0 'explicit' provisioning (nightly) vs 0.10.7 legacy posadm path (ours), and the client host (system-ci-runner vs claude-agentsrv). Both give exactly 4096 prompt tokens." },
  { id: 'C3', text: "The CI row's 320 samples give TPS mean 28.253, population sd 0.163, min 27.79, max 28.73, p05 27.97, TTFT mean 18646 ms, 10 rounds from 04:10:12 to 04:22:58 UTC with running averages 28.21-28.28. Our base arm gave 28.236 / 28.244 / 28.263 TPS (mean 28.248), TTFT 19010-19058 ms, min 27.59-27.66. The CI value is +0.005 TPS (+0.02 %) above our base mean, smaller than our pass-to-pass spread (0.027 TPS), and the TTFT is 2 % lower." },
  { id: 'C4', text: "Conclusion: 28.3 TPS is exactly the expected AMX-OFF value for this row. Once the nightly package carries the AMX kernels (tron PR #4505 merged AND publish-deb succeeding), the expected row value is about 32.2 TPS (+14 %; our canon arm 32.199/32.181/32.239, paired t 338) with TTFT about 11.5 s; the pre-registered band +11..+21 % maps to 31.4-34.2 TPS. A value near 28.3 on a night when the package does contain AMX would be a real finding (AMX not running)." },
  { id: 'C5', text: "Timeline facts: tron PR #4505 (deb preset TRON_AMX_DISPATCH ON) is OPEN and approved, not merged. publish-deb.yml scheduled runs failed at startup on 09-19, 09-20, 09-21 and 09-22 (01:35Z); PR #4510 fixing the workflow permissions merged 2026-09-22T03:50:49Z, after the 09-22 schedule. Hence the 09-23 nightly will most likely get a NEW tron package (main head) that still has NO AMX, and the row should again read about 28.3 TPS unless other main changes move the baseline; AMX appears in the row only after #4505 merges and a publish-deb run after that merge succeeds." },
  { id: 'C6', text: "The AMD nightly (andoria-b1a3, run 35682128668) ran the same row and reported 29.0 TPS (320 samples, mean 29.00, sd 0.455, TTFT 13.3 s). AMD CPUs have no AMX, so this row can never show an AMX gain there; it is an AVX baseline for that machine and is not comparable to the 3bda expectation." },
]
const LENSES = [
  { key: 'data', prompt: 'LENS = data re-check. Independently re-derive every number in the claim from the primary files (parse the log yourself with grep/awk/python; read summary.json and the per-pass perf.json; run the gh commands). Report each number as claimed vs found.' },
  { key: 'confound', prompt: 'LENS = confounds and environment. Look for differences between the nightly run and our measurement that the claim ignores or understates (provisioning path, platformd version, warm vs cold engines, order of configs, prompt set and caching, client host, machine load, number of engines, Caddy spread, speculation settings, env files). For each, say whether the evidence shows it changed the result.' },
  { key: 'logic', prompt: 'LENS = interpretation and wording. Check that the conclusion follows from the evidence, that percentages and rounding are right, that words like "identical", "exactly", "expected", "never" are justified, and that nothing is presented as measured when it is estimated. Propose exact rewording where needed.' },
]
const VERDICT = { type: 'object', properties: {
  claim_id: { type: 'string' }, lens: { type: 'string' },
  refuted: { type: 'boolean' },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  summary: { type: 'string', description: 'one paragraph verdict' },
  evidence: { type: 'array', items: { type: 'string' }, description: 'file:line or command output quotes' },
  corrections: { type: 'array', items: { type: 'string' }, description: 'precise corrections to numbers or wording, empty if none' },
  new_facts: { type: 'array', items: { type: 'string' }, description: 'relevant facts found that the claim did not mention' },
}, required: ['claim_id', 'lens', 'refuted', 'confidence', 'summary', 'evidence', 'corrections', 'new_facts'] }

phase('Refute')
const results = await pipeline(CLAIMS,
  c => parallel(LENSES.map(l => () => agent(
    `${CONTEXT}\n\nCLAIM ${c.id}: ${c.text}\n\n${l.prompt}\n\nTry hard to refute the claim. Return the structured verdict.`,
    { label: `refute:${c.id}:${l.key}`, phase: 'Refute', schema: VERDICT }))).then(vs => ({ claim: c, votes: vs.filter(Boolean) }))
)
for (const r of results.filter(Boolean)) log(`${r.claim.id}: ${r.votes.filter(v => v.refuted).length}/${r.votes.length} refuted`)

phase('Critic')
const critic = await agent(`${CONTEXT}\n\nHere are six claims and the verdicts of three verifiers each:\n${JSON.stringify(results.filter(Boolean), null, 1)}\n\nYou are the completeness critic. Answer: (1) what question about "does 28.3 TPS align with our expectation" is still unanswered by these claims and verdicts? (2) which corrections across the verdicts are the same finding (dedupe) and which contradict each other (resolve by checking the primary files yourself)? (3) list the final, deduplicated corrections that the write-up must apply, each with evidence. (4) list anything in the facts file that is wrong. Return JSON with keys: unanswered (array of strings), resolved_contradictions (array), final_corrections (array of {text, evidence}), facts_file_errors (array), one_paragraph_verdict (string).`,
  { label: 'completeness-critic', phase: 'Critic', schema: { type: 'object', properties: {
    unanswered: { type: 'array', items: { type: 'string' } },
    resolved_contradictions: { type: 'array', items: { type: 'string' } },
    final_corrections: { type: 'array', items: { type: 'object', properties: { text: { type: 'string' }, evidence: { type: 'string' } }, required: ['text', 'evidence'] } },
    facts_file_errors: { type: 'array', items: { type: 'string' } },
    one_paragraph_verdict: { type: 'string' },
  }, required: ['unanswered', 'resolved_contradictions', 'final_corrections', 'facts_file_errors', 'one_paragraph_verdict'] } })
return { results, critic }