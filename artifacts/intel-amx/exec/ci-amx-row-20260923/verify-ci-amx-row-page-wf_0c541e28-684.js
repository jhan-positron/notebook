export const meta = {
  name: 'verify-ci-amx-row-page',
  description: 'Adversarially verify every claim on the 2026-09-23 CI AMX-row page, check its English, then critique the verdict',
  phases: [
    { title: 'Verify', detail: '6 fact groups re-derived from raw sources + 1 plain-English check' },
    { title: 'Critic', detail: 'attack the overall verdict and find gaps' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/CI-test/status/CI-AMX-row-20260923.html'
const GEN = '/home/jhan/workspace/intel-AMX/exec/ci-amx-row-20260923/gen_page.py'
const DIR = '/home/jhan/workspace/intel-AMX/exec/ci-amx-row-20260923'

const COMMON = `You verify one part of an engineering report page. The page answers two questions from the user (jhan):
(1) "Last night's CI row 'llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): 32.5 TPS (placeholder threshold), prefill~354 tok/s, TTFT 11569ms (@4.1k prompt)' - is this result as expected?"
(2) "The night before it read '... (AMX benchmark): 28.3 TPS' with no prefill. Why was prefill not listed, and what was the prefill TPS of that test?"

Page (HTML, generated): ${PAGE}
Generator with every number and its source comment (FACTS dict): ${GEN}
Working folder with the saved GitHub run logs and scripts: ${DIR}
  nightly-35683952944.log (delphi-3bda 09-22), nightly-35815209295.log (delphi-3bda 09-23), nightly-genoa-35682128668.log (andoria-b1a3 09-22),
  nightly-genoa-35813240282.log (andoria-b1a3 09-23), plus nightly-35052594106/35178969541/35303980268/35419103383/35487126137/35558398011.log (3bda 09-16..09-21);
  amx_row.py -> amx_row.json, all_rows.py -> all_rows.json, history_3bda.json.
Other sources: systems_test repo at ~/workspace/ai-runs/systems_test (git fetch done; commits 7327184 = 09-22 nightly head, 5b2250b9 = 09-23 head);
  tron repo at ~/workspace/tron (origin/main fetched); our campaign summary /home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920/summary.json;
  plan /home/jhan/workspace/intel-AMX/CI-test/status/llama-3.1-8b-8u-4k-plan.md; combined report /home/jhan/workspace/intel-AMX/CI-test/status/llama-3.1-8b.html;
  memory notes /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/*.md (first-ci-amx-row-20260922.md, l8b-8u4k-20260920-campaign.md, ci-enable-20260917-campaign.md, amx-vs-avx-sense.md, l8b-levers-20260919-campaign.md);
  gh CLI works for positron-ai/tron and positron-ai/systems_test; Slack channel #ci-cd-notifications = C06S8PNDBQA (load Slack tools with ToolSearch "select:mcp__claude_ai_Slack__slack_read_channel"; 09-22 reports are between ts 1790078400 and 1790096400, 09-23 reports after 1790136000).
Rules: re-derive each claim yourself from the raw source (run the command, read the log line, recompute the number). Do not trust the generator's comments.
Try hard to REFUTE each claim; mark "upheld" only when your own check confirms it. Use "corrected" when the claim is nearly right but a number, time, name or wording is off (give the exact fix), "refuted" when it is wrong, "unverifiable" when no source you can reach settles it.
delphi-3bda is a shared CI machine that is busy now: do NOT ssh to it except, if you need it, ONE read-only command combining dpkg-query -W tron and "strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE". Never run objdump there. Do not modify any file.
Return findings for every claim in your group, including the upheld ones, with the evidence you used (command + output excerpt or file:line).`

const GROUPS = [
  { key: 'package', prompt: `GROUP "package": page section 3 table and the Words list entries about PR #4505 / TRON_AMX_DISPATCH. Claims: PR #4505 merged 2026-09-22 21:08:26 UTC with merge commit 9276183ad3; publish-deb run 35806901506 started 2026-09-23 01:35:16 UTC and succeeded on main 5cf65b9241; 5cf65b9241 contains 9276183ad3; delphi-3bda log line 455 "Setting up tron (2026.09.23-5cf65b92)" at 03:40:06 UTC and andoria-b1a3 log line 485 at 03:10:12 UTC; both Slack reports name v2026.09.23-5cf65b92; dpkg 2026.09.23-5cf65b92 installed; rinzler 234,414,048 bytes with 86 AMX tile instructions and TRON_AMX_DISABLE once (86/1 also in our canon build, 0/0 in no-kernel packages: check memory ci-enable-20260917-campaign.md and nightly-amx-check-20260916.md); config.env empty; no run-time AMX counter in CI. Also check that the 09-22 nightly on both machines ran 2026.09.18-3faba6d0 and whether the publish-deb build log shows kernels/amx_attn.cpp being compiled (gh run view 35806901506 --log, grep amx_attn).` },
  { key: 'row-stats', prompt: `GROUP "row-stats": page section 1 bullets, table 1 CI rows, chart 1 and chart 2 values. Recompute from the four logs the AMX-benchmark row (the config block with n_users=32, prompt_length=4096, generate_length=1536; samples = "Done (TTFT=..., X / Y TPS)" lines until the next config): sample count, TPS mean (numpy mean), population sd, p05 by linear interpolation, min, mean TTFT, harness-rounded TTFT, prefill = 4096 / (round(mean TTFT)/1000). Confirm the 09-23 Slack line values (32.5, 354, 11569) and andoria 09-23 (28.9, 307, 13324) are reproduced, the 09-22 prefill 219.7 tok/s (Slack would print 220) and andoria 09-22 308.8 tok/s. Check the gains quoted: CI +15.0 %, AMD -0.3 %, prefill +61.2 % (CI), -0.4 % (AMD). Check the claim "The per-sample TTFT means match the Slack TTFT of all 13 rows on both machines for 09-23" against the Slack reports. Check that the measured window really is generated tokens 896 to 1024 (start_capture/end_capture) and that systems_test computes TPS/p05/TTFT/prefill the way the page says (scripts/perf.py around lines 378-400, testlib/perf_metrics.py).` },
  { key: 'ours', prompt: `GROUP "ours": every number the page takes from our own 09-20 campaign and plans. Claims: base mean 28.248, canon mean 32.206 TPS, gain +14.0 % with paired t about 338 over 3 pairs; canon passes span 32.18 to 32.24; CI 09-23 is +0.29 TPS (+0.9 %) above canon and above all three passes; 09-22 no-kernel values agreed to +0.02 %; canon TTFT 11,481 ms, CI TTFT +0.8 % slower; base TTFT 19,035 ms and CI 09-22 TTFT -2.0 % vs it; our prefill 215.2 -> 356.8 tok/s (+65.8 %); table 1 "Ours" rows (sd ranges, p05 means, slowest values); the band "+11 to +21 % over 28.25 = 31.35 to 34.18 TPS registered before our campaign" (plan section 7); the 09-22 TTFT estimate "11.2 to 11.5 s" (memory first-ci-amx-row-20260922.md) and "0.07 s above its upper edge"; proposed thresholds mean 30.6 / p05 30.3 / slowest 30.0 TPS in llama-3.1-8b.html section 9.4 and the margins 1.89 / 1.93 / 2.08 TPS; the chart-3 caption claim that our campaign measured +0.2 % (not resolved) for AMX at 2 users per engine and prompt 1024 (exec/results/l8b-levers-20260919/summary.json). Also check whether calling our canon build "3faba6d0 + AMX build option" and "canonical (default) AMX kernels" is accurate (memory canon-ci-20260918-campaign.md, l8b-8u4k-20260920-campaign.md).` },
  { key: 'slack-format', prompt: `GROUP "slack-format": page section 2 "Why Slack did not print it". Claims: the 09-22 delphi-3bda nightly ran systems_test commit 7327184; in that version a row with no threshold at all got a short line with only the TPS value (testlib/results.py branch "if not has_threshold"); the gemma-4 row printed timing on 09-22 because it has a placeholder goal of 1.00 TPS in scripts/system_ci.py and took the placeholder branch; the AMX row had no goal entry; PR #227 titled "Include prefill and TTFT in uncalibrated benchmark Slack reports" (commit 18c60c6 by Rhys) changed the short line to the placeholder format with timing and merged at 2026-09-22 17:48:38 UTC; the 09-23 run used commit 5b2250b9 which includes it; scripts/perf.py:396-397 (TTFT rounding and prefill formula) is identical in both commits and the harness stores prefill with each result (verify where prefill_mean goes: talos/results upload). Also verify the two Slack lines quoted on the page are verbatim (except the page writes "~" for the approximately sign). Check whether andoria-b1a3's 09-22 AMX row also lacked prefill in Slack.` },
  { key: 'history', prompt: `GROUP "history": page section 4, chart 3 and the details table. Recompute, from the eight delphi-3bda logs (09-16..09-23), every perf row's mean TPS per night (numpy mean over the row's Done samples) and check: the package each night (09-16 f46e48ba, 09-17 31b80a18, 09-18..09-22 3faba6d0, 09-23 5cf65b92) and that all packages before 09-23 had no AMX kernels (memory nightly-amx-check-20260916.md, first-ci-amx-row-20260922.md); the flagged rows: qwen-3-4b tp4 172.12 vs 140.88..153.13 (+12.4 % above the highest), gpt-oss-120b tp4 118.91 vs 101.16..109.70 (+8.4 %), llama-3.3-70b tp4 31.33 vs 30.14..30.41 (+3.0 %), gemma-4-31b tp2 37.40 vs 37.94..38.12 (-1.4 % below); llama-3.1-8b 8 users 141.39 is +0.2 % above its highest earlier night; "the other tp2 rows stayed inside their range, or within 0.3 % of it"; the AMD 09-22 -> 09-23 changes quoted (+1.8, +1.5, -0.2 % for the three tp4 rows, gemma-4 AMD change). Also check the row labels: user counts (in total), prompt 200 / 1024 / 4096 for the three llama rows that name a prompt (read each config block), and that the "(users in total, 4 engines)" header is right for every row (tp4 models on 8 cards: are there 4 engines or 2? check the log's provisioning lines "engines" for tp4 models, e.g. "Waiting for platformd inference engines to be ready: [...]").` },
  { key: 'open-items', prompt: `GROUP "open-items": page section 5 and its reasoning. Claims: CI ran tron main 5cf65b9241, which is 32 merges (102 commits) after 3faba6d0; the candidate merges exist in that range with the stated subjects: #4455 and #4456 (sliding KV storage and reclamation), #4516 (slice cost data for the Xeon 6962P = granite_rapids_6962p), #4258 (FPGA attention streaming join), placement changes; check whether any of those touch code on the CPU attention / AMX / decode path used by llama-3.1-8b tp2 (git show --stat on each merge; look for kernels/amx_attn*, attention, kv_cache, scheduler, cost data that selects slices). Claim: "the kill switch arm ran a few points slower than a no-kernel build in our 08-31 test" (memory amx-vs-avx-sense.md) - check the exact wording and numbers there. Claim: qwen-3-4b uses FPGA attention in the nightly and CPU attention work appeared under FPGA attention in the 09-17 check (501 M AMX busy cycles; memory ci-enable-20260917-campaign.md) - the page words hypothesis (1) carefully; say if it overstates. Judge whether each hypothesis is paired with a measurement that would really decide it, and whether any stronger, cheaper decisive measurement is missing.` },
]

const FINDINGS = {
  type: 'object',
  properties: {
    group: { type: 'string' },
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          verdict: { type: 'string', enum: ['upheld', 'corrected', 'refuted', 'unverifiable'] },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['claim', 'verdict', 'evidence'],
      },
    },
  },
  required: ['group', 'items'],
}

const ENGLISH = {
  type: 'object',
  properties: {
    violations: {
      type: 'array',
      items: {
        type: 'object',
        properties: { rule: { type: 'string' }, phrase: { type: 'string' }, fix: { type: 'string' } },
        required: ['rule', 'phrase', 'fix'],
      },
    },
  },
  required: ['violations'],
}

phase('Verify')
const tasks = GROUPS.map(g => () => agent(`${COMMON}\n\n${g.prompt}`, { label: `verify:${g.key}`, phase: 'Verify', schema: FINDINGS }))
tasks.push(() => agent(`Check-mode review of the visible prose of the HTML page ${PAGE} against the plain-english rules in your instructions (Rules 1-8), plus the project CLAUDE.md term list (/home/jhan/workspace/intel-AMX/CLAUDE.md: e.g. "prompt N" never "ctx N"; AMX arms wording) and these banned words: convoy, refund, "in disguise", swept. Also the project terminology: never call a build without kernels "AMX-off" (that term means the TRON_AMX_DISABLE kill switch of a build with kernels). Read the rendered text (strip tags, include SVG text labels and table cells). Report only real violations: exact phrase, rule, and the corrected text. Do not invent violations. Do not edit files.`, { label: 'verify:english', phase: 'Verify', schema: ENGLISH }))
const results = await parallel(tasks)
const facts = results.slice(0, GROUPS.length).filter(Boolean)
const english = results[GROUPS.length]
const flagged = facts.flatMap(r => r.items.filter(i => i.verdict !== 'upheld').map(i => ({ group: r.group, ...i })))
log(`fact items: ${facts.reduce((a, r) => a + r.items.length, 0)}, not upheld: ${flagged.length}, english violations: ${english ? english.violations.length : 'n/a'}`)

phase('Critic')
const critic = await agent(`${COMMON}

You are the final critic. Six verifiers checked the page's facts; their non-upheld findings are below (JSON). Your job:
1. Attack the page's top-level verdict "Yes: last night's 32.5 TPS is the value we expected once the AMX kernels reached the nightly package." Is the reasoning sound? In particular: the CI night-to-night gain (+15.0 %) mixes the AMX kernels with 32 other merged changes, while our campaign (+14.0 %) isolates the kernels. Does the page say this clearly enough, and is "as expected" still justified? Is the AMD control (andoria-b1a3) able to detect Intel-only non-AMX changes? Is anything claimed as proof that is only indirect?
2. Completeness: what does the user need that the page does not give (e.g. the exact Slack-style prefill string for 09-22, the prefill for AMD, whether the 09-22 prefill is also visible in Talos, what to watch on the next nights)? What claim is unverified or source unread?
3. For each verifier finding below, say whether you agree and give the final fix text to apply.
Verifier findings not upheld:
${JSON.stringify(flagged, null, 1)}
Return a concise structured critique.`, {
  label: 'critic', phase: 'Critic',
  schema: {
    type: 'object',
    properties: {
      verdict_sound: { type: 'boolean' },
      verdict_notes: { type: 'string' },
      missing: { type: 'array', items: { type: 'string' } },
      fixes: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, fix: { type: 'string' }, why: { type: 'string' } }, required: ['where', 'fix', 'why'] } },
    },
    required: ['verdict_sound', 'verdict_notes', 'missing', 'fixes'],
  },
})
return { facts, english, flagged, critic }
