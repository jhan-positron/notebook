export const meta = {
  name: 'asimov-handoff-checkout',
  description: 'Verify HANDOFF-2026-11-02.md claims against sources, refute contradictions, draft extension plan and Jesse questions',
  phases: [
    { title: 'Verify', detail: 'four readers check handoff claims by area' },
    { title: 'Refute', detail: 'two skeptics per contradicted claim' },
    { title: 'Design', detail: 'two independent extension plans, one judge' },
    { title: 'Critic', detail: 'what is missing' },
  ],
}

const CTX = `
Context you must take as given (read the files for everything else):
- Working folder: /home/jhan/workspace/titan/cache-perf/asimov. The handoff is HANDOFF-2026-11-02.md there. Sibling folders: ../crb (CRB report, plan-2026-11-02.md, codex-review-plan-2026-11-02.md, results/cmn-map.txt, refs/*.pdf), ../bench (homelat.c, latency.c, bandwidth.c, run_sudo.sh).
- Previous session memory notes: /home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf/memory/*.md (asimov-emulator-run-facts.md holds Jesse Zhang's three Slack replies of 2026-10-30).
- New facts after the handoff was written (Slack DM D0AT074U71S, 2026-10-31): Jibin sent Jesse the commit 9c6b8e7 pointer at 11:33 PDT; Jesse said "I will get that started today" at 12:02 PDT; at 12:46 PDT Jesse said the scratchpad (SPM) phase is postponed to a next phase because the stock /dev/asimov-spm driver cannot load on this emulator build (a register range is cut off; loading hangs the CPU), and mapping it by hand risks a kernel crash before the output is saved. No results directory has been received as of 2026-11-01 evening.
- GitHub: jhan-positron/asimov commit 9c6b8e7 (2026-10-31T06:30Z) has cache-mem-perf/{Makefile,README.md,bandwidth.c,common.h,latency.c,run_asimov.sh}. Use "gh api repos/jhan-positron/asimov/contents/cache-mem-perf/<file>?ref=9c6b8e7" with jq '.content' | base64 -d to fetch a file if you need to diff.
- You are read-only: do not edit any file, do not run anything on CRB or any remote machine, do not post to Slack. Local commands (grep, python3 arithmetic, gh api reads, pdftotext on ../crb/refs) are fine.
- Return raw data through the schema, not a human-facing message. Every evidence string must name a file and line (or a PDF page, or a URL).
`

const CLAIMS = {
  type: 'object',
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string', description: 'the handoff claim, quoted or closely paraphrased, with the handoff section' },
          status: { type: 'string', enum: ['confirmed', 'contradicted', 'unverifiable'] },
          evidence: { type: 'string', description: 'file:line or page or URL plus what it says' },
          correction: { type: 'string', description: 'for contradicted: the correct statement. for unverifiable: what source or measurement would settle it. else empty' },
        },
        required: ['claim', 'status', 'evidence', 'correction'],
      },
    },
    extra_findings: { type: 'array', items: { type: 'string' }, description: 'facts the handoff omits that the next session needs, each with a citation' },
  },
  required: ['claims', 'extra_findings'],
}

const AREAS = [
  {
    key: 'code-state',
    prompt: `Check every claim in HANDOFF-2026-11-02.md sections "State of the Asimov work", "Rules that still apply" and "Files to read first" that concerns the local sources (latency.c, bandwidth.c, common.h, run_asimov.sh, Makefile, README.md). Specifically verify, with file:line evidence:
(a) local sources are byte-identical to GitHub commit 9c6b8e7 cache-mem-perf (fetch and diff each of the six files);
(b) run_asimov.sh runs the latency chase on CPU 2 only, and which phases use CPUs 4, 6, 8 and 2-9;
(c) latency.c uses fresh chains and DC CIVAC flush as the handoff says, and how a fresh chain is built (does chain 0's warm-up walk the same lines as chains 1..K-1, so a prefetcher could learn line addresses?);
(d) perf events 0x03, 0x17, 0xA2 as stated;
(e) the hugepage count (256 pages of 2 MiB) the README promises: compute the actual peak footprint of each phase from run_asimov.sh and bandwidth.c and say whether 256 pages suffice, including the fresh-chain 32 MiB sweep and the 8-thread 16 MiB-per-thread bandwidth row;
(f) the chip-time estimate "about 2 s": recompute from the loads per row in run_asimov.sh (sizes, reps, passes, threads) using 120 ns per DRAM load, 30 ns per SLC load (est.) and 10 GB/s per core bandwidth (est.), and report the total and the three largest rows;
(g) what happens in run_asimov.sh now that SPM is postponed (is the SPM phase skipped cleanly when /dev/asimov-spm is absent?), and whether anything else in the script or README depends on SPM;
(h) the handoff says the README "explains every test"; list any run_asimov.sh row the README table does not cover.
Also list extra facts in the code the handoff omits (for example the --build-cpu option in ../bench/latency.c that the handoff says exists in the CRB code but does the Asimov latency.c have it?).`,
  },
  {
    key: 'crb-carryover',
    prompt: `Check every numbered claim in HANDOFF-2026-11-02.md section "What the CRB work established that carries over" (items 1 to 5) and the "Open questions" item 3 (chip-time budget) against ../crb/crb-memory-hierarchy.html, ../crb/plan-2026-11-02.md, ../crb/codex-review-plan-2026-11-02.md, ../crb/results/cmn-map.txt, ../bench/homelat.c, ../bench/run_sudo.sh and the CSVs under ../crb/results/followup3-*/. Specifically:
(1) the map file path, that it needs debugfs and root, and that drivers/perf/arm-cmn.c has arm_cmn_map_show (fetch https://raw.githubusercontent.com/torvalds/linux/master/drivers/perf/arm-cmn.c and cite the line; also check whether the driver's map output is guarded by a Kconfig or debugfs option that Jesse's minimal kernel may lack);
(2) the counter-based home classification method in homelat.c (which step, which event name, how many probes, whether the codex review found defects the handoff should have carried over, for example the P1 single-event misassignment and the fill-coverage gcd defect);
(3) the three prefetcher lessons: find the exact comment lines in homelat.c and the plan that state them, and whether the Asimov latency.c method (fresh chains + flush) is actually "safer" or whether the CRB lesson "a fill chain walked every repeat is learned" also applies to the Asimov latency.c warm-up (chain 0 walked twice over the same lines);
(4) the numbers 394 GB/s and 173 GB/s: find them in the followup3 CSVs (writegrid or similar) and confirm the placements;
(5) the numbers 25.4 ns, 30.5 ns, 0.2 ns and the CPU ids 94 and 56: find them in the followup3 per-core CSV;
(6) the "80 chip-seconds, 262,144 probes, about 128 counter reads per probe" arithmetic: recompute from homelat.c (probe loop, loads per probe, counters per read) and the plan's "about 300 us per probe", and state what the per-probe cost is made of (syscalls versus the 256 flush-and-load repeats).
Also report whether the handoff claim "The CRB work in ../crb is finished except for one root-only run" matches the plan and the codex review (which open items remain, and whether the codex review's P1 items were applied to homelat.c; cite line numbers that show the current fill routine and classification acceptance).`,
  },
  {
    key: 'topology',
    prompt: `Check the topology and mesh claims in HANDOFF-2026-11-02.md ("Words used here", "Topology from the RTL", "What the Asimov extension would measure") and the Asimov memory notes. Do the following:
(1) The handoff says DSU ports are at crosspoints 12, 23, 32, 43, 52 and home nodes at 13, 24, 33, 44, 53, "so each DSU is one hop from its home node", and later "Expect a 1-hop to 4-hop spread". Work out, for the two plausible id conventions (id = 10*x + y, or id = 10*y + x, Manhattan distance between crosspoints), the hop count from each DSU port to each of the 5 home nodes as a 5 by 5 table, and state the real min and max spread per DSU. Say explicitly that the convention is unknown and which single fact from Jesse (the yml or the CMN_uArch_Spec) settles it. Use python3 for the arithmetic.
(2) The Arm CMN S3 TRM is at ../crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf. Use pdftotext (or python) to find and cite the pages that describe: how a request node selects the home node for an address (the system address map, SAM, and the address hashing / "HN-S hashing" or striping configuration), whether the hash is programmable, the node id encoding (x, y, port, device bits), and whether locking SLC ways (OCM-like "way partition" or "lock") changes address-to-home mapping. Quote the sentence and the page number for each.
(3) The CRB map (../crb/results/cmn-map.txt) shows what the Linux driver prints. State what the equivalent Asimov map would look like for 5 home nodes and 5 DSU ports (RN-F type names), and which fields confirm the RTL yml claim.
(4) The memory note asimov-emulator-run-facts.md says the architecture spec v1.7 had a home node on each DSU crosspoint, but current RTL has 5 HN-S shared by all cores, one hop away. Say whether the handoff is consistent with that, and whether the OCM region n to home node n mapping is stated as a fact or an assumption (cite the note).
(5) The handoff says "Every address has exactly one home node, chosen by a hash of the physical address" and that with 5 nodes "each buffer's lines are spread over all 5 slices". Check the TRM: with 5 (a non power of two) home nodes, how does CMN S3 distribute addresses (does it support non-power-of-two HN-S counts, and with what granule)? Cite the page. This decides whether a 256 KiB OCM region can be "one region per home node" at the same time as DRAM addresses being hashed across 5 nodes.
(6) Linux arm-cmn PMU: from the kernel documentation (https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/perf/arm-cmn.rst) and driver source, confirm the names bynodeid and nodeid, and that an event like hns_pocq_reqs_recvd_read exists for CMN S3 (cite the driver line defining it). Also check whether the driver needs the CMN's DTC (debug trace controller) to be present in the RTL config, which an emulator build might cut (the SPM driver was cut this way).`,
  },
  {
    key: 'expectations',
    prompt: `Read ocm-interpretation.html in the working folder and crb-validation/20261031T073509Z/ (the run of the same sources on CRB). Report:
(1) Every expected Asimov number the page states (latency per level, OCM per region, bandwidth), with its basis (which Jesse fact, which CRB number, "est." or measured), as a list; flag any number that is presented without "est." though it is an estimate.
(2) Whether ocm-interpretation.html already says anything about per-slice latency, hop count, or home-node mapping that the handoff's "What the Asimov extension would measure" section should reuse or that contradicts it.
(3) From the crb-validation run: what did the fresh-chain and flushed sweeps give on CRB at 256 KiB to 8 MiB (ns per load, refills per load), and does the flushed single pass agree with the fresh chain at the same size? This decides the handoff claim that "latency.c already uses fresh chains and an explicit flush, which is the safer method". Cite the CSV lines.
(4) Chip time for the proposed extension: a per-slice chain of L lines homed at one node, flushed, walked once from each of 4 cores (CPU 2, 4, 6, 8) for 5 nodes, 3 repeats, plus the existing SLC-regime fresh chase (sizes 512K to 3M, 3 chains) from 3 more cores. Compute chip seconds for L = 1024, 2048 and 4096 lines at an assumed 60 ns (est.) per SLC load and 2 us (est.) per DC CIVAC line flush... actually do not assume the flush cost: find in crb-validation sanity-flush.csv or all.txt what a flushed pass costs relative to a fresh pass on CRB, and use that ratio. Show the arithmetic.
(5) Does the README or the HTML mention the SPM driver risk, and what changes now that Jesse postponed SPM (which rows disappear, which "runs last" rule becomes moot)?`,
  },
]

phase('Verify')
const verified = await parallel(AREAS.map(a => () =>
  agent(`${CTX}\n\nYour area: ${a.key}.\n${a.prompt}\n\nRead HANDOFF-2026-11-02.md first in full. Be exhaustive: every claim in your area gets a row, including ones you confirm. Mark a claim contradicted only when a cited source says otherwise; mark unverifiable when no local source or fetchable document settles it.`,
    { label: `verify:${a.key}`, phase: 'Verify', schema: CLAIMS })
))
const areas = verified.map((v, i) => ({ key: AREAS[i].key, result: v })).filter(x => x.result)
log(`verify: ${areas.length}/${AREAS.length} areas returned`)

const contradicted = areas.flatMap(a => a.result.claims.filter(c => c.status === 'contradicted').map(c => ({ ...c, area: a.key })))
log(`contradicted claims to refute: ${contradicted.length}`)

phase('Refute')
const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'true if the contradiction itself is wrong, i.e. the handoff was right or the point is moot' },
    reason: { type: 'string' },
    evidence: { type: 'string' },
  },
  required: ['refuted', 'reason', 'evidence'],
}
const refuted = await pipeline(contradicted,
  c => parallel([0, 1].map(k => () => agent(`${CTX}\n\nA verifier claims the handoff is wrong. Handoff claim: "${c.claim}". Verifier's evidence: ${c.evidence}. Verifier's correction: ${c.correction}.\n\nYour job is to REFUTE the verifier (lens ${k === 0 ? 'read the primary source yourself and check whether the verifier misread it' : 'check whether the verifier used the wrong file, a stale version, or a convention the handoff never claimed'}). Default to refuted=true if the evidence does not clearly support the correction. Cite file:line.`,
    { label: `refute:${c.area}:${k}`, phase: 'Refute', schema: VERDICT }))),
  (votes, c) => ({ ...c, survives: votes.filter(Boolean).filter(v => !v.refuted).length >= 1 && votes.filter(Boolean).filter(v => v.refuted).length < 2, votes: votes.filter(Boolean) })
)
const corrections = refuted.filter(Boolean)
log(`corrections surviving: ${corrections.filter(c => c.survives).length}/${corrections.length}`)

phase('Design')
const factsText = JSON.stringify({
  confirmed: areas.flatMap(a => a.result.claims.filter(c => c.status === 'confirmed').map(c => c.claim + ' [' + c.evidence + ']')),
  corrections: corrections.filter(c => c.survives).map(c => ({ claim: c.claim, correction: c.correction, evidence: c.evidence })),
  unverifiable: areas.flatMap(a => a.result.claims.filter(c => c.status === 'unverifiable').map(c => c.claim + ' -> ' + c.correction)),
  extra: areas.flatMap(a => a.result.extra_findings),
}, null, 1)

const PLAN = {
  type: 'object',
  properties: {
    questions_for_jesse: { type: 'array', items: { type: 'object', properties: { question: { type: 'string' }, why: { type: 'string' }, one_line_test: { type: 'string' } }, required: ['question', 'why', 'one_line_test'] } },
    measurements: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, what: { type: 'string' }, cores: { type: 'string' }, chip_seconds_est: { type: 'number' }, depends_on_answer: { type: 'string' }, code_change: { type: 'string' } }, required: ['name', 'what', 'cores', 'chip_seconds_est', 'depends_on_answer', 'code_change'] } },
    do_not_do: { type: 'array', items: { type: 'string' } },
    rationale: { type: 'string' },
  },
  required: ['questions_for_jesse', 'measurements', 'do_not_do', 'rationale'],
}
const angles = [
  'budget-first: every row must be justified against the 46 min per chip second cost and the fact that no results from the first run have arrived yet; prefer measurements that reuse existing binaries with new arguments',
  'method-first: start from the prefetcher and cache-state pitfalls found on CRB and from the CMN S3 TRM facts; prefer measurements whose cache state is provable with the available PMU counters',
]
const plans = await parallel(angles.map((angle, i) => () => agent(`${CTX}\n\nVerified facts and corrections from the previous phase:\n${factsText}\n\nDesign the Asimov extension the handoff asks for (mesh topology check, home-node mapping, per-slice latency, per-core average, write placement), from the angle: ${angle}. Read the handoff, run_asimov.sh, latency.c, ../bench/homelat.c and ocm-interpretation.html before answering. Rewrite the handoff's three open questions for Jesse and the design team so that each has a one-line test he can run or a document pointer, add any question the verified facts show is missing (for example the crosspoint id convention and the HN-S hash granule), and drop any that the facts already answer. Every chip-second number is an estimate: show the arithmetic in the 'what' field. No code is to be written now; describe the code change in one sentence each.`,
  { label: `design:${i}`, phase: 'Design', schema: PLAN })))
const goodPlans = plans.filter(Boolean)

const JUDGE = {
  type: 'object',
  properties: {
    final_questions: { type: 'array', items: { type: 'object', properties: { question: { type: 'string' }, why: { type: 'string' }, one_line_test: { type: 'string' } }, required: ['question', 'why', 'one_line_test'] } },
    final_measurements: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, what: { type: 'string' }, cores: { type: 'string' }, chip_seconds_est: { type: 'number' }, depends_on_answer: { type: 'string' }, code_change: { type: 'string' } }, required: ['name', 'what', 'cores', 'chip_seconds_est', 'depends_on_answer', 'code_change'] } },
    do_not_do: { type: 'array', items: { type: 'string' } },
    disagreements: { type: 'array', items: { type: 'string' }, description: 'where the two plans differ and which was chosen, with the reason' },
  },
  required: ['final_questions', 'final_measurements', 'do_not_do', 'disagreements'],
}
const judged = await agent(`${CTX}\n\nVerified facts:\n${factsText}\n\nTwo independent plans:\n${JSON.stringify(goodPlans, null, 1)}\n\nMerge them into one plan. Keep every question that a verified fact does not already answer, merge duplicates, keep the one-line tests. For measurements, keep the cheapest set that answers the handoff's goals; drop anything whose cache state cannot be shown with the PMU counters the code already reads (0x03, 0x17, 0xA2) or with the mesh counters, and say so in do_not_do. Check each chip-second estimate's arithmetic yourself with python3 and correct it.`,
  { label: 'judge', phase: 'Design', schema: JUDGE })

phase('Critic')
const CRIT = { type: 'object', properties: { missing: { type: 'array', items: { type: 'string' } }, wrong: { type: 'array', items: { type: 'string' } } }, required: ['missing', 'wrong'] }
const critic = await agent(`${CTX}\n\nHere is the verified-facts list:\n${factsText}\n\nAnd the merged plan:\n${JSON.stringify(judged, null, 1)}\n\nAs a completeness critic: what did the verification not check that the handoff states (list the handoff sentences nobody verified)? What in the plan contradicts a rule in the handoff's "Rules that still apply" or Jesse's run instructions (results as a directory, compact output, flush before every timed OCM pass, say which cores and how many 2 MiB pages)? What question for Jesse is still missing? Cite file:line for each item.`,
  { label: 'critic', phase: 'Critic', schema: CRIT })

return { areas, corrections, plans: goodPlans, judged, critic }