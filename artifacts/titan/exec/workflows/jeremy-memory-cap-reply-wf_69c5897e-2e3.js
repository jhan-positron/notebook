export const meta = {
  name: 'jeremy-memory-cap-reply',
  description: 'Research whether the Asimov emulator image caps AP DRAM bandwidth, then draft and verify a reply to Jeremy',
  phases: [
    { title: 'Research', detail: 'five parallel readers: RTL at image, RTL history, Slack, measured data, lab evidence' },
    { title: 'Draft', detail: 'one drafter writes the reply and its claim list' },
    { title: 'Verify', detail: 'three skeptics check the draft against primary sources' },
  ],
}

const CONTEXT = `
CONTEXT (read fully).
Jibin Han (the user) runs memory-hierarchy benchmarks (cache-mem-perf: latency and bandwidth programs) on the Asimov chip emulator (GA13 Palladium, image hemi_rtws_tlm, RTL commit 0d9e214eb43b of GitHub repo Positron-AI-TSMC/asimov, committed 2026-10-28). Jesse Zhang operates the emulator and delivers results.
Jibin wrote in a status message: "Bill reviewed the data mid week ... pointed out the DRAM latency was suspiciously good. I added more tests and debugged this with Jesse. It turned out the emulator uses some memory model, not real DRAM, and the model is configured providing common response latency regardless of addresses."
Jeremy replied: "I thought the emulator models had been fixed to cap the memory bandwidth to match reality. Are you using an old emulator model?"
We must research and draft Jibin's reply to Jeremy.

Working hypothesis from Jesse's README (written by Jesse's AI agent, so it is a SUGGESTION that must be verified against primary sources): the AP's DRAM (SMS, at 0xC0_0000_0000) is four embedded Cadence AXI memory models on XMS lanes 32-35 ("AUX lanes", Goldcrest pairs 16 and 17) with every delay control zero and no bandwidth cap. A DRAM-like timing profile (61 ns per read, 40 ns write response, a 38.4 GB/s cap) IS in this image but is loaded only on the 32 datapath (weight-fetch) lanes, GC_PAIR_INDEX 0-15, gated by DATAPATH_TIMING. Cited files at 0d9e214: emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv (lines 112-141, 118-119, 643, 689), design/xms/packages/xms_pkg.sv:84-85, emu/hemi_tlm/doc/GC_DDR_TIMING.md (70-80, 86-87), emu/hemi_tlm/tests/gc_avip_timing_tb.sv.
Known history: the timing commits to GC_DDR_TIMING.md are by Thuan Duong, committer date 2026-10-24 (e.g. cbab6b5251fc "emu: model Goldcrest AVIP bandwidth and refresh", 13c8cbfb1d78 "emu: apply timing overrides after startup and restore dry-run support"); a later commit 7ea83a99a090 (nbauer, 2026-11-04) "xms: correct gc lane ordering" touches the same doc.

ACCESS (all read-only; never write, push, post or send anything):
- GitHub: \`gh api repos/Positron-AI-TSMC/asimov/contents/<path>?ref=<sha>\` (add -H "Accept: application/vnd.github.raw" for raw text), commits, compare, pulls, issues, search.
- Lab host: \`ssh -o BatchMode=yes jhan@sw-dev-01 '<cmd>'\`. Jesse's box folder is /home/jzhang/dev/emuMemBenchBox (repos/asimov-rtl clone, evidence/jibin/memory-delay.md, ga13/image, ga13/run, docs, STATUS.md, references/). For git there use \`git -c safe.directory='*' -C <dir> ...\`. Read only. Do not start any emulator job.
- Local project: /home/jhan/workspace/titan/cache-perf/asimov (results/membench-jibin-001..012 with README.md and CSVs; pages; memory notes at /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-asimov/memory/).
- Slack via MCP tools (load with ToolSearch "select:mcp__claude_ai_Slack__slack_search_public_and_private,mcp__claude_ai_Slack__slack_read_thread,mcp__claude_ai_Slack__slack_read_channel,mcp__claude_ai_Slack__slack_search_users"). Jibin's Slack id is U0AST6PF20M. Read only: never send or draft a Slack message.
Write scratch files only under /tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/aead512e-bbe4-4138-adcc-51aaa6cdc0d3/scratchpad/.

OUTPUT RULES: every claim must carry its source (file path + line numbers + commit, or Slack channel + timestamp + author, or CSV file + row). Quote the decisive lines verbatim. Separate "verified in primary source" from "inferred" from "could not determine". If a source is unreachable say so; do not guess.
`

const FINDINGS = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'at most 8 sentences' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          status: { type: 'string', enum: ['verified', 'contradicted', 'inferred', 'undetermined'] },
          source: { type: 'string', description: 'path:lines@commit, Slack channel/ts/author, or CSV file and row' },
          quote: { type: 'string', description: 'verbatim decisive text, may be empty' },
        },
        required: ['claim', 'status', 'source'],
      },
    },
    gaps: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'findings', 'gaps'],
}

const RESEARCH = [
  {
    key: 'rtl-at-image',
    prompt: `TASK: verify, in the primary RTL files at commit 0d9e214eb43b, exactly which memory lanes get the DRAM-like timing/bandwidth profile and which do not.
Read (at ref 0d9e214eb43b, via gh api raw or the lab clone if its HEAD is that commit): emu/hemi_tlm/doc/GC_DDR_TIMING.md (whole file), emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv (find DATAPATH_TIMING, GC_PAIR_INDEX, every delay/bandwidth/refresh control and the values loaded), design/xms/packages/xms_pkg.sv (lane and pair numbering, which pairs are SMS/AUX), and whatever instantiates the lane wrapper for pairs 16 and 17.
Answer with quotes and line numbers:
1. What is the profile (read latency ns, write-response ns, bandwidth cap value and its unit and scope: per lane, per pair, per DDR channel? what real device does the doc say it models?), and how is the cap implemented (scheduler, token bucket, burst gap)?
2. Which lanes get it (GC_PAIR_INDEX range) and which are excluded; the exact condition in code.
3. Does the doc state WHY the four AUX lanes keep zero delay (design decision, limitation, to-do)? Quote any rationale or to-do text.
4. Which lanes serve the Arm application processor's DRAM (SMS at 0xC0_0000_0000)? Confirm from the RTL that SMS = the AUX lanes / pairs 16-17, and that the AP's memory traffic does not go through pairs 0-15.
5. Is the profile applied at build time or at run time ("apply timing overrides after startup")? Is there any run-time switch (plusarg, script, register, env variable) that would have had to be set for the profile to be active, on any lane? Name it.
6. What do pairs 0-15 serve (weight-fetch datapath)? Could a CPU benchmark reach them at all?`,
  },
  {
    key: 'rtl-history',
    prompt: `TASK: establish whether the emulator image (RTL 0d9e214eb43b, 2026-10-28) is "old" relative to the fix that caps memory bandwidth, and what changed later.
Using gh api on Positron-AI-TSMC/asimov:
1. Find the PR(s) that added the Goldcrest AVIP timing / bandwidth / refresh model (commits by Thuan Duong with committer date 2026-10-24: cbab6b5251fc, 3395329fa405, a6f5be9cb06d, e691a198f2c1, be7fe447d366, 13c8cbfb1d78 and neighbours). Give PR number, title, merge date, author, and quote the PR description parts that state scope (which lanes) and intent ("match reality"? cap value?).
2. Prove with the compare API whether those commits are ancestors of 0d9e214eb43b (so the image contains the fix).
3. List every commit on main after 0d9e214eb43b up to today (2026-11-10) that touches emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv, emu/hemi_tlm/doc/GC_DDR_TIMING.md, design/xms/packages/xms_pkg.sv, or other files that define the SMS/AUX lane memory models. For each, say whether it changes which lanes get timing (in particular 7ea83a99a090 "xms: correct gc lane ordering": read its diff). At current main HEAD, do the AUX/SMS lanes still have zero delay and no cap? Quote the current doc lines.
4. Search issues and PRs (open and closed) for work to add timing or a bandwidth cap to the SMS / AUX lanes / AP DRAM (keywords: SMS timing, AUX lane, DDR timing, bandwidth cap, LPDDR, AVIP timing, GC_DDR_TIMING, memory model latency). Report numbers, titles, states.
5. How many commits is main ahead of 0d9e214eb43b, and is there any newer released emulator image mentioned in the repo (release notes, tags, emu docs)?`,
  },
  {
    key: 'slack',
    prompt: `TASK: find the Slack context of Jeremy's remark and what "the emulator models had been fixed to cap the memory bandwidth to match reality" refers to.
1. Find Jibin's status message containing "Bill reviewed the data mid week" (search from:<@U0AST6PF20M>, last 5 days, DMs and channels; also try keywords "memory model", "common response latency") and Jeremy's reply ("cap the memory bandwidth", "old emulator model"). Report channel, timestamps, Jeremy's full name, Slack id, title/role (slack_search_users), and the full text of Jibin's message and any other replies in that thread. If search fails, read recent history of likely channels/DMs. If still not found, say so.
2. Search all of Slack (several phrasings, since 2026-09-01) for the earlier work Jeremy may mean: "bandwidth" with "emulator"/"emulation"/"Palladium"/"AVIP"/"Goldcrest"/"DDR timing"/"memory model"/"LPDDR"/"refresh"/"38.4", messages by Thuan Duong about timing, messages by Jeremy about emulator memory bandwidth. Report who said what, when, where, with quotes: what was fixed, on which lanes or memories, with what cap value, and whether anyone stated that the AP/SMS/AUX memory is or is not covered.
3. Search for any statement about AP DRAM / SMS lanes timing in the emulator ("AUX lanes", "SMS", "zero-delay", "host-model DRAM").
4. Also look in Jibin's DM with Jesse Zhang (DM channel D0AT074U71S) from 2026-11-04 onward for what Jesse (or his bot) said about the memory model, bandwidth caps, or newer images.
Report each finding with channel, ts, author and a verbatim quote.`,
  },
  {
    key: 'measured-data',
    prompt: `TASK: extract, by running scripts over the CSVs (no estimates), the measured AP DRAM numbers that bear on "is memory bandwidth capped to match reality".
Folder: /home/jhan/workspace/titan/cache-perf/asimov/results/ (membench-jibin-001..012; the latest full boot is 011 = boot F1, results/bootF1; run 3 = 004; boot B = 006 prefetchers off; boot E = 010). Read the READMEs' CSV format notes and the memory note files asimov-run2-state.md and asimov-run6-results.md for orientation, then compute from the raw CSVs:
1. DRAM-sized streaming bandwidth (GB/s), per boot where available: one-core read, write and copy at the largest footprints (16-32 MiB and above); multi-core read and write (2, 4, 8 cores; per-cluster placement rows); the highest aggregate DRAM read and write rate ever measured in any boot, with file, row and footprint.
2. DRAM latency: the random pointer-chain ns per load at 8 MiB flushed and 32 MiB, and the address-order vs random pair on boot B (52.762 vs 52.739 ns).
3. From Jesse's READMEs (grep all 12 for "cap", "38.4", "memory model", "LPDDR", "not silicon", "embedded emulator memory"), quote every statement about the AP DRAM model and about bandwidth caps, with README path and line.
4. State what a 38.4 GB/s cap would mean against the data: list each measured DRAM-footprint row that exceeds 38.4 GB/s (if any), since a row above the cap is direct evidence that no such cap applies to AP DRAM. Note honestly whether those rows are truly DRAM-served (footprint far above SLC capacity, flushed or first-touch) or could be served by caches; give the cache capacities stated in the READMEs/pages.
5. If any page or README states what the real AP memory is expected to deliver (real LPDDR5X bandwidth or latency for the AP), quote it; otherwise say "not stated".
Give exact file names and row text for every number.`,
  },
  {
    key: 'lab-evidence',
    prompt: `TASK: read Jesse's evidence on the lab host and determine how the image was built and run with respect to memory-model timing.
On sw-dev-01 under /home/jzhang/dev/emuMemBenchBox:
1. Read evidence/jibin/memory-delay.md in full (71 lines). Report its claims and which files it cites; note which claims are marked inference.
2. Check repos/asimov-rtl: what commit is checked out (git -c safe.directory='*' rev-parse HEAD)? If it is 0d9e214eb43b, open the cited lines of emu/hemi_tlm/agents/goldcrest_ew_fullconn_avip.sv, design/xms/packages/xms_pkg.sv and emu/hemi_tlm/doc/GC_DDR_TIMING.md and confirm or contradict memory-delay.md's reading, quoting the lines.
3. Read ga13/image and ga13/run (README, manifests, scripts, logs; list first, then read what is relevant), docs/PLAN.md, docs/REQUEST.md, STATUS.md, CLAUDE.md, GOAL.md: which emulator image/release is used (name, build date, RTL commit, who built it), is it the latest available release on GA13 (look for other image directories or release listings the box references, and any note of newer releases), and does the run flow apply or skip any timing override (search for "timing", "DATAPATH_TIMING", "dry-run", "override", "avip", "bandwidth", "delay" in the run scripts and logs).
4. In the emulator run logs of the latest boots (results/jibin/membench-jibin-011 and neighbours, plus any ga13/run logs), look for lines printed by the timing model at startup (profile loaded, lanes configured, zero-delay AUX lanes). Quote them if present.
5. Look in references/asimov-bench for "host-model DRAM" or any statement about AP DRAM in the emulator, and quote it.
Read only. Do not launch anything on the emulator.`,
  },
]

phase('Research')
const research = (await parallel(RESEARCH.map(r => () =>
  agent(CONTEXT + '\n' + r.prompt, { label: `research:${r.key}`, phase: 'Research', schema: FINDINGS })
    .then(res => res ? { key: r.key, ...res } : null)
))).filter(Boolean)
log(`research returned ${research.length}/${RESEARCH.length} reports`)
const missing = RESEARCH.map(r => r.key).filter(k => !research.some(r => r.key === k))
if (missing.length) log(`MISSING research reports: ${missing.join(', ')}`)

const researchText = JSON.stringify(research, null, 1)

phase('Draft')
const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    reply_short: { type: 'string', description: 'the Slack reply, 3 to 6 short sentences' },
    reply_with_detail: { type: 'string', description: 'a longer variant with the evidence bullets, at most 12 lines' },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: { claim: { type: 'string' }, source: { type: 'string' }, status: { type: 'string' } },
        required: ['claim', 'source', 'status'],
      },
    },
    open_points: { type: 'array', items: { type: 'string' } },
  },
  required: ['reply_short', 'reply_with_detail', 'claims', 'open_points'],
}
const draft = await agent(CONTEXT + `
TASK: draft Jibin's Slack reply to Jeremy from the research reports below. Use only claims marked verified, or label a point as inferred/unknown. Do not relay Jesse's agent's README statements unless a research report verified them in a primary source.
The reply must directly answer both of Jeremy's sentences: (a) was the model fixed to cap memory bandwidth, and does that fix cover the memory Jibin measured; (b) is the image an old model (give its RTL commit date against the date of the fix, and whether current main differs for the measured memory).
Style: plain English, short sentences, one claim per sentence, no idioms, every number with a unit, define project names at first use in a few words, no preamble or pleasantries, neutral tone, written in first person as Jibin. State what is still unknown and who could settle it. Slack plain text (bullets with "- " allowed), no tables.
Give two variants: reply_short (3 to 6 sentences) and reply_with_detail (at most 12 lines). List every factual claim used with its source, and list open points.

RESEARCH REPORTS (JSON):
` + researchText, { label: 'draft reply', phase: 'Draft', schema: DRAFT_SCHEMA })

phase('Verify')
const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['sound', 'needs-fixes', 'wrong'] },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          sentence: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'primary source with quote' },
          fix: { type: 'string' },
        },
        required: ['sentence', 'problem', 'fix'],
      },
    },
    confirmed: { type: 'array', items: { type: 'string' }, description: 'claims you re-checked yourself in a primary source and found correct' },
  },
  required: ['verdict', 'issues', 'confirmed'],
}
const LENSES = [
  { key: 'rtl', prompt: `LENS: RTL facts. Independently re-open the primary RTL files (gh api at ref 0d9e214eb43b and at current main) and try to REFUTE every RTL statement in the draft: which lanes get the timing profile, the cap value/unit/scope, that the AP DRAM lanes have zero delay and no cap, the dates and ancestry of the fix relative to the image, and what current main does. Do not trust the research reports; read the files yourself.` },
  { key: 'data', prompt: `LENS: measured data and logic. Independently recompute from the CSVs under /home/jhan/workspace/titan/cache-perf/asimov/results/ every number in the draft, and try to REFUTE the reasoning: does any quoted bandwidth row really show DRAM-served traffic above the cap (or could caches serve it)? Is the latency argument (same delay regardless of address order) stated correctly? Does the draft overstate anything (e.g. says "no cap" where the evidence only shows "no configured cap in RTL")?` },
  { key: 'reader', prompt: `LENS: Jeremy as reader. Jeremy is a senior colleague who believes the emulator models were fixed to cap memory bandwidth. Check: does the reply answer both of his sentences directly in its first two sentences? Is anything defensive, vague, or likely to trigger a follow-up question that the research already answers (who made the fix, which memory it covers, what it would take to cover AP DRAM)? Is every project name defined, every number given with a unit, no idioms, one claim per sentence? Does it name what is unknown and who settles it? Also check that Jibin's original statement ("common response latency regardless of addresses") is consistent with the reply. Propose exact rewordings.` },
]
const verdicts = (await parallel(LENSES.map(l => () =>
  agent(CONTEXT + `
TASK: adversarially review this draft reply to Jeremy. ${l.prompt}
Default to reporting a problem when you cannot confirm a statement in a primary source.

DRAFT (JSON):
${JSON.stringify(draft, null, 1)}

RESEARCH REPORTS the drafter used (JSON, treat as unverified):
${researchText}`, { label: `verify:${l.key}`, phase: 'Verify', schema: VERDICT })
    .then(v => v ? { lens: l.key, ...v } : null)
))).filter(Boolean)
if (verdicts.length < LENSES.length) log(`only ${verdicts.length}/${LENSES.length} verifiers returned`)

return { research, missing, draft, verdicts }
