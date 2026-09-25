export const meta = {
  name: 'qwen3-4b-prefill-amx-vs-fpga',
  description: 'Extract every qwen3-4b TTFT measurement (AMX canonical / VNNI-K / FPGA attention), read the prefill mechanism from tron source, then critique completeness',
  phases: [
    { title: 'Extract', detail: 'one agent per result set, structured TTFT rows' },
    { title: 'Mechanism', detail: 'tron + harness source: what prefill does under FPGA attention, what TTFT measures' },
    { title: 'Critique', detail: 'completeness critic over all rows' },
  ],
}

const ROWS_SCHEMA = {
  type: 'object',
  properties: {
    source: { type: 'string' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          campaign: { type: 'string' },
          date_utc: { type: 'string' },
          harness: { type: 'string', description: 'runtron | ci-harness | nightly' },
          machine_share: { type: 'string', description: 'our half | whole 3bda | nightly (remote client)' },
          layout: { type: 'string', description: 'engines x users per engine, proxy or not, client host' },
          model: { type: 'string' },
          tp: { type: 'integer' },
          users_per_engine: { type: 'integer' },
          users_total: { type: 'integer' },
          prompt_length: { type: 'integer' },
          gen_tokens: { type: 'integer' },
          arm_label: { type: 'string' },
          attention: { type: 'string', description: 'cpu | fpga | unknown' },
          cpu_kernel: { type: 'string', description: 'avx | amx-canon | amx-vnnik | amx-mirror | unknown  (what the CPU-scored attention share uses)' },
          amx_kill_switch: { type: 'boolean' },
          build: { type: 'string', description: 'commit / version / deb name' },
          n: { type: 'integer' },
          ttft_ms: { type: 'number' },
          ttft_sd_ms: { type: 'number' },
          ttft_per_rep_ms: { type: 'array', items: { type: 'number' } },
          ttft_definition: { type: 'string', description: 'what this TTFT number is: runtron max prompt-parse over users, harness client mean, etc.' },
          tps_per_user: { type: 'number' },
          file_refs: { type: 'array', items: { type: 'string' }, description: 'absolute file paths (with line numbers where possible) each number came from' },
          caveats: { type: 'string' },
        },
        required: ['campaign', 'harness', 'model', 'tp', 'prompt_length', 'arm_label', 'attention', 'cpu_kernel', 'build', 'n', 'ttft_ms', 'ttft_definition', 'file_refs'],
      },
    },
    notes: { type: 'string' },
    gaps: { type: 'string', description: 'what this source does NOT contain that the question needs' },
  },
  required: ['source', 'rows', 'notes', 'gaps'],
}

const HITS_SCHEMA = {
  type: 'object',
  properties: {
    hits: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          model: { type: 'string' },
          tp: { type: 'integer' },
          users: { type: 'integer' },
          prompt_length: { type: 'integer' },
          hw_attention: { type: 'string', description: 'enabled | disabled | unknown, with the log line that says so' },
          build: { type: 'string' },
          ttft: { type: 'string', description: 'the TTFT value(s) with units as found' },
          note: { type: 'string' },
        },
        required: ['path', 'model', 'prompt_length', 'hw_attention', 'ttft', 'note'],
      },
    },
    searched: { type: 'string', description: 'what was searched and how (commands), so a reader can judge coverage' },
    verdict: { type: 'string' },
  },
  required: ['hits', 'searched', 'verdict'],
}

const MECH_SCHEMA = {
  type: 'object',
  properties: {
    answer: { type: 'string' },
    evidence: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          lines: { type: 'string' },
          quote: { type: 'string' },
          what_it_shows: { type: 'string' },
        },
        required: ['file', 'lines', 'quote', 'what_it_shows'],
      },
    },
    confidence: { type: 'string', description: 'high | medium | low, with one sentence why' },
    open_questions: { type: 'string' },
  },
  required: ['answer', 'evidence', 'confidence', 'open_questions'],
}

const COMMON = `
You are a read-only data extractor. Do NOT modify any file, do NOT touch any remote machine (never ssh to delphi-3bda or any other host). Work only on local files under /home/jhan/workspace/intel-AMX and /home/jhan/workspace/ai-runs. Use absolute paths in every command (do not cd).

Context: the question is "for qwen3-4b, is prefill (TTFT, time to first token) better with AMX attention on the CPU (canonical build, or the VNNI-K build of PR 4424) or with attention on the FPGA?". Decode TPS is already known to favour the FPGA. We need every TTFT number for qwen-3-4b (model names ingested-qwen-3-4b-instruct-2507-tp2 / -tp4) with its exact conditions.

Vocabulary you must classify per row:
- attention = 'fpga' when USE_HW_ATTN was unset (tron enables FPGA attention for ingested models when unset; log line "HW attention enabled") and 'cpu' when USE_HW_ATTN=0 (log line "HW attention disabled").
- cpu_kernel = what the CPU-scored attention share used: 'avx' for builds without AMX code (main before PR 3879, e.g. eb2de0265a, nightly debs before 2026-09-18 deb preset) or with the kill switch TRON_AMX_DISABLE=1; 'amx-canon' for PR 3879 / main-with-AMX builds without the VNNI K layout (544ca05c7a, c7844ca2ce, 3faba6d0fd+preset 0594dc54); 'amx-vnnik' for PR 4424 builds with TRON_K_VNNI on (ff680c8020, dc950be5f2, 30c4ac82cb, vnni arms); 'amx-mirror' for K-mirror arms. When an arm is the PR-4424 code with the layout off ("headoff"), classify it as 'amx-canon' and say so in caveats. Use 'unknown' if you cannot tell from the files and say why.
- n = number of repetitions the mean is over.
- Record the TTFT in milliseconds (convert seconds).
- ttft_definition: say exactly what was measured (runtron prints "Parsing the prompt took X s" per request and the campaign summaries take the max over users; the CI harness reports the client-side mean TTFT over users and rounds; say which).
- Put an absolute file path (and line numbers when you can) in file_refs for every number. Do not invent numbers; if a value is not in the files, leave the row out and note it in gaps.
Return the structured object only.`

phase('Extract')
const SOURCES = [
  {
    key: 'p0perf-20260913',
    prompt: `${COMMON}
Source: /home/jhan/workspace/intel-AMX/exec/results/p0perf-20260913/ (summary.md, summary.json, rt-results.txt, cells/). Also read the report /home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/Sunday-CI-layout-results.html for stated caveats about TTFT (strip tags with sed). Campaign facts: head 544ca05c7a (AMX canonical), our half, arms off (TRON_AMX_DISABLE=1, USE_HW_ATTN=0), on (USE_HW_ATTN=0), fpga (USE_HW_ATTN unset AND TRON_AMX_DISABLE=1). Extract: runtron cells (8 users, prompt 1024, tp2/tp4, off/on) and CI-harness cells (tp2 = 2 engines x 2 users, tp4 = 1 engine x 4 users; off/on/fpga), per-rep TTFT values, and the per-engine TTFT values. Verify the arm definitions in cells/ or rt-results.txt (grep for USE_HW_ATTN and TRON_AMX_DISABLE and "HW attention").`,
  },
  {
    key: 'wedperf-20260916',
    prompt: `${COMMON}
Sources: /home/jhan/workspace/intel-AMX/exec/results/wedperf-20260916/ (summary.md, summary.json, rt-results.txt), /home/jhan/workspace/intel-AMX/exec/results/wedperf-gen1536-20260916/, /home/jhan/workspace/intel-AMX/exec/results/wedperf-attr-20260916/, /home/jhan/workspace/intel-AMX/exec/results/wedperf-attr2-20260916/. Base = eb2de0265a (main before PR 3879 = no AMX code), target = ff680c8020 (PR 4424 head: AMX + VNNI K). Cells with attn=cpu are USE_HW_ATTN=0; attn=fpga are USE_HW_ATTN unset. Extract only the qwen-3-4b rows (tp2 and tp4, 8 users, prompt 1024, both attn modes; the gen1536 variant; the attribution blocks which have more arms: read their summary.md to learn what each arm is, e.g. p3879 = PR 3879 canonical). Confirm the arm/binary identities from rt-results.txt log lines ("Version:", "HW attention enabled/disabled").`,
  },
  {
    key: 'issue4500-20260918',
    prompt: `${COMMON}
Source: /home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918/ (summary.md, summary.json, rt-results.txt, m6/summary.md, m6/summary.json, reading.html, traces/analysis.md). All runtron cells here ran with FPGA attention (HW attn enabled). Arms: base = c7844ca2ce (main with AMX dispatch, row-major K = amx-canon), headoff = ff680c8020 built with TRON_K_VNNI off (amx-canon, note it), vnni/vnni2 = ff680c8020 VNNI on (amx-vnnik), vnnikill = vnni + TRON_AMX_DISABLE=1 (cpu_kernel avx, kill switch true), head30 = 30c4ac82cb. Blocks m1 (8 users), m1b (2 and 4 users), m2 (early-launch knob minb1/minb100), m3 (traced), m4 (perf counters). Block m6 = rinzler + the nightly client on our half (tp2 2 users, tp4 4 users; arms base = nightly deb 2026.09.18-3faba6d0 which has NO AMX code -> avx; target = ci-mimic target deb = main + PR 4424 -> amx-vnnik; targetkill; baseminb1; targetminb1). Extract every qwen-3-4b TTFT row including m6's TTFT if recorded (look in m6/summary.md, m6/summary.json and m6/cells/). Also extract from traces/analysis.md any PREFILL-pass timing (prefill pass ms, Save K in prefill, attention in prefill) if the traces cover prefill; say clearly if they are decode-only.`,
  },
  {
    key: 'vnnik4-models-20260915',
    prompt: `${COMMON}
Source: /home/jhan/workspace/intel-AMX/exec/results/vnnik4-models-20260915/ (results.txt, summary.txt, rt/, smoke/). The cell=fpga rows are qwen-3-4b tp2 with USE_HW_ATTN unset: arm base = runtron.p0perf13 = 544ca05c7a (AMX canonical build, NO kill switch -> the CPU share runs amx-canon), arm new = runtron.vnnik4 = dc950be5f2 (VNNI K pre-rebase -> amx-vnnik). Extract the smoke (1 user, 128 tokens) and rt (8 users, 256 tokens) TTFT values with the exact "Parsing the prompt took" lines (all 8 per run; report max and also the list). Also check /home/jhan/workspace/intel-AMX/exec/results/vnnik4-20260915/summary.md for qwen-3-4b CPU-attention rows (USE_HW_ATTN=0: base vs vnni at prompt 1024/2048/8192) and include them.`,
  },
  {
    key: 'ci-mimic+canon-ci-20260918',
    prompt: `${COMMON}
Sources: /home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/ (base-pass1/summary.txt + perf.json, target-pass1/summary.txt + perf.json, caveats.html, notes3.html, report-v4.html) and /home/jhan/workspace/intel-AMX/exec/results/canon-ci-20260918/ (canon/summary.txt + perf.json, caveats.html, notes.html, report-v2.html). These are whole-machine runs of the nightly perf phase (4 tp2 engines / 2 tp4 engines behind Caddy, 8 users total, prompt 1024, 1536 generated, 10 rounds), FPGA attention on (USE_HW_ATTN unset in production units). Arms: ci-mimic base = nightly deb 2026.09.18-3faba6d0 (no AMX code -> avx); ci-mimic target = main 3faba6d0 + PR 4424 deb (amx-vnnik); canon-ci canon = deb 2026.09.18-0594dc54-jhan-ci-canon (main + deb preset AMX on, no PR 4424 -> amx-canon). Extract the qwen-3-4b tp2 and tp4 TTFT (mean over users x rounds) from the RESULT lines, and from perf.json the per-user or per-round TTFT distribution if present (report p95/min/max if available). Read caveats.html (strip tags) and record the client-host-load caveat for TTFT in the caveats field. Also state how the harness computes TTFT if the reports say.`,
  },
  {
    key: 'q4b-swattn-20260919',
    prompt: `${COMMON}
Source: /home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919/ (summary.txt, summary.json, configs-used.json, base-pass1..3/, canon-pass1..3/, check-8u-p8192/, RUNBOOK.md) and the report /home/jhan/workspace/intel-AMX/CI-test/status/Saturday-qwen3-4b.html (strip tags). Whole machine, nightly layout (4 tp2 engines behind Caddy, 2 users per engine = 8 users), USE_HW_ATTN=0 on BOTH arms (CPU attention), base = nightly deb 2026.09.18-3faba6d0 (avx), canon = deb 2026.09.18-0594dc54-jhan-ci-canon (amx-canon). Nine prompt lengths 1024..8192. Extract per prompt length the TTFT mean per arm, the per-pass TTFT values (3 passes each), the client-host load / Caddy flags, and the check cell (8 users on one engine? read the runbook) TTFT. Report what the report says about the TTFT definition and about the client host load during this run.`,
  },
  {
    key: 'nightly-reference',
    prompt: `${COMMON}
Sources: /home/jhan/workspace/intel-AMX/exec/results/nightly_stats.json, /home/jhan/workspace/intel-AMX/exec/results/nightly_rows.json, /home/jhan/workspace/intel-AMX/exec/results/nightly_reference.json, and /home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/reference/ (nightly-reference-final.json, nightly_stats.json, the granite_*.txt logs, parse_perf.py). These describe the nightly CI (systems_test on host system-ci-runner, remote client, Caddy proxy, FPGA attention, tron deb of the day = main, no AMX before 2026-09-18). Extract the qwen-3-4b tp2 and tp4 TTFT per night (date, tron version, ttft_ms mean, p95 if present) and the 13-night mean/sd. One row per night per tp (harness 'nightly', attention fpga, cpu_kernel avx unless the tron version is at or after a build that compiled AMX in the deb: check whether ANY nightly deb in the series had AMX; memory says the deb preset enabling AMX was proposed in PR 4505 and NOT merged as of 2026-09-21, so all nightly debs are avx; state this assumption). Also report whether the nightly logs record the client host load.`,
  },
  {
    key: 'vnnik-cpu-runtron',
    prompt: `${COMMON}
Sources: /home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/summary.md (+ summary.json, rt-results.txt), /home/jhan/workspace/intel-AMX/exec/results/vnnik2-20260915/summary.md, /home/jhan/workspace/intel-AMX/exec/results/vnnik2-confirm-20260915/, /home/jhan/workspace/intel-AMX/exec/results/vnnik5-20260916/ and vnnik7-20260916/ if they have summaries. These are runtron cells on our half with USE_HW_ATTN=0 (CPU attention), qwen-3-4b tp2/tp4, 8 users, prompts 1024/2048/8192. Arms: off = kill switch (avx), base = 544ca05c7a canonical (amx-canon), vnni/vnni0 = VNNI K layout (amx-vnnik), vnnioff = vnni + kill switch (avx, layout on), a/b/ab = VNNI K variants (read the summary headers or rt-results.txt to learn what a, b, ab are; ab became the later head). Extract all qwen-3-4b TTFT rows. Confirm USE_HW_ATTN=0 from the log lines ("HW attention disabled").`,
  },
  {
    key: 'more-testing-r1+p0perf-20260911',
    prompt: `${COMMON}
Sources: /home/jhan/workspace/intel-AMX/exec/results/more-testing-r1/cells/ingested-qwen-3-4b-instruct-2507-tp4__{off,canon,mirror,off__rep2}/ (CI harness perf cells, one engine, 8 users, prompt 1024, gen 1536, USE_HW_ATTN=0 in every arm, head 60d66d9c04; off = kill switch avx, canon = amx-canon, mirror = amx-mirror), plus /home/jhan/workspace/intel-AMX/PR3879/more-testing/round-1/status.md and results.html for the summarised TTFT. And /home/jhan/workspace/intel-AMX/exec/results/p0perf-20260911/ (summary.md/json: runtron 8u and CI-harness 8 users on ONE engine, our half, head 47f6f2dceb, off/on, USE_HW_ATTN=0). Extract every qwen-3-4b TTFT row (runtron and CI harness), with the per-rep values.`,
  },
  {
    key: 'sweep-other-fpga-ttft',
    schema: 'hits',
    prompt: `${COMMON}
Task: multi-modal sweep for ANY qwen-3-4b run with FPGA attention (USE_HW_ATTN unset, log line "HW attention enabled for model 'ingested-qwen-3-4b") at a PROMPT LENGTH OTHER THAN 1024, anywhere under /home/jhan/workspace/intel-AMX/exec/results/ (all subdirectories, including dd/, slot1/, t4/, g1-20260908/, g3-lite-20260908/, ctxfill*/, fence*/, perf-round-*/, more-testing-r1/soak*, router/, single-attn-*, thp-*, tilec-*, expert-replicas-*, qwen8u8k-*.txt) and under /home/jhan/workspace/intel-AMX/{PR3879,CI-test,VNNIed-K-in-place,definitive-decode,rampup,perf-model,tmp}/ (html/md reports), and /home/jhan/workspace/intel-AMX/exec/logs/. Search several ways: (1) grep -rl "HW attention enabled" then for each file the nearby "--prompt-length" / "prompt=" / "Parsing the prompt took" lines; (2) grep for "USE_HW_ATTN" together with "qwen" in campaign scripts under /home/jhan/workspace/intel-AMX/exec/ to find campaigns whose fpga arms used other prompt lengths; (3) grep html/md reports for "FPGA" near "8192" or "4096" or "2048" with "qwen". For each hit report prompt length, users, build, and the TTFT values. Also report explicitly whether any qwen-3-4b FPGA-attention TTFT exists at prompt > 1024 (this is the key gap check). Be thorough: list the commands you ran in 'searched'.`,
  },
]

const extracted = await parallel(SOURCES.map(s => () =>
  agent(s.prompt, {
    label: `extract:${s.key}`,
    phase: 'Extract',
    schema: s.schema === 'hits' ? HITS_SCHEMA : ROWS_SCHEMA,
  }).then(r => ({ key: s.key, result: r }))
))

phase('Mechanism')
const MECH_COMMON = `
You are a read-only code reader. Do NOT modify files, do NOT build anything, do NOT touch remote machines. Use absolute paths (no cd). Source trees: tron main as of 2026-09-10 at /home/jhan/workspace/ai-runs/tron-main-ro (commit 1279137d), and the PR 4424 branch at /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K (commit 30c4ac82cb; has AMX + VNNI K; the AMX code of PR 3879 merged into main on 2026-09-15 so tron-main-ro predates it). Key files: h/tron/models/hw_attn_config.hpp (engagement point 127), src/tron/gof.cpp + h/tron/gof.hpp (populate / staging K into the FPGA's HBM), src/tron/models/full.hpp or similar (attention dispatch: hwattention vs CPU workers), the hwattention scheduler files (grep -ri "hwattention\\|hw_attn\\|early_launch\\|EARLY_LAUNCH_MIN_B" h/ src/), amx_attn_iface / attn kernels (grep -ri "amx" h/tron src/tron in the PR tree). Quote the lines you rely on with file:line. Distinguish what the code says from what you infer.`

const mechQuestions = [
  {
    key: 'prefill-under-fpga',
    prompt: `${MECH_COMMON}
Question: when FPGA attention is enabled for qwen-3-4b (ingested model, USE_HW_ATTN unset, log "HW attention enabled ... engagement=127"), what happens to ATTENTION DURING PREFILL (prompt parse) of a 1024-token prompt? Specifically: (a) does the FPGA score the prefill queries (positions >= 127) or only decode queries, i.e. is the prompt's attention computed on the CPU workers regardless? (b) which positions / tokens are always scored on the CPU (the 0-126 engagement window, the tail not yet in HBM)? (c) what extra work sits inside TTFT in the FPGA path (gof::populate staging of K/V into the FPGA, DMA, launch), and where does it run (forward thread vs attention workers)? (d) in an FPGA-attention run of a build that has the AMX kernel (PR 3879 / 4424), does the AMX dense kernel run during prefill, and for which part? Answer with code evidence. Observed data to reconcile (state whether your reading is consistent with it): CI layout, prompt 1024, tp2 with 2 users per engine, same binary 544ca05c7a: CPU attention with kill switch TTFT 909 ms, CPU attention with AMX 727 ms, FPGA attention with kill switch 761 ms. Whole machine, same canonical AMX deb 0594dc54: FPGA attention 516 ms vs CPU attention 517 ms; nightly deb (no AMX) FPGA attention ~510 ms vs CPU attention 674 ms.`,
  },
  {
    key: 'ttft-definitions',
    prompt: `${MECH_COMMON}
Question: what exactly do the two TTFT numbers measure? (1) runtron with -u 8 --prompt-length 1024: read the runtron source (grep -rn "Parsing the prompt took" in /home/jhan/workspace/ai-runs/tron-main-ro) and determine whether the 8 users' prompts are parsed one after another on the same engine (so the "max over users" = the 8th prefill's completion time, i.e. about 8 prefill passes) or in one batched pass; what the timer brackets (tokenization? K/V save? first token sampling?). (2) The CI harness (systems_test at /home/jhan/workspace/ai-runs/systems_test: testlib/tps.py, scripts/perf.py; and our driver /home/jhan/workspace/intel-AMX/exec/ci-mimic-20260918/st_ci_perf.py or exec/q4b-swattn-20260919/st_ci_perf.py): how TTFT is measured (client timestamp to first streamed token? includes tokenization and proxy hop?), how it is aggregated (mean over users and rounds? running average?), whether users start staggered, and how 8 users over 4 engines become 2 per engine (Caddy lb policy if visible). (3) Therefore: is a runtron 8-user TTFT comparable to a CI-harness 2-users-per-engine TTFT? Explain the ratio one should expect. Answer with code evidence.`,
  },
  {
    key: 'fpga-prefill-scaling',
    prompt: `${MECH_COMMON}
Question: how should FPGA-attention prefill cost scale with prompt length compared with CPU AMX attention prefill, for qwen-3-4b (36 layers, 8 KV heads x 128, 32 query heads, tp2)? From the code: (a) does the FPGA attention path have a per-token or per-page staging cost (gof::populate per KV page? per token?) that grows linearly with prompt length, and is it on the critical path of prefill? (b) is there any per-request cap on how many prompt tokens the FPGA handles (kv_slot_extent=36? HBM capacity per slot? max context on the card)? (c) does the CPU attention path (AMX dense kernel over KV pages, PR 3879) have quadratic cost in prompt length during prefill (each query block against all earlier pages)? (d) hence, which one is expected to win TTFT at prompt 4096 and 8192, and why? Label anything not in the code as a hypothesis. Also report the qwen-3-4b HW attention parameters printed in the log line "HW attention enabled for model 'ingested-qwen-3-4b-instruct-2507-tp2': max_layers=36 engagement=127 kv_slot_extent=36 hw_attn_params { kv_head_size: 128 n_kv_heads: 8 ..." - find where these fields are defined and what kv_slot_extent means.`,
  },
]

const mechanism = await parallel(mechQuestions.map(q => () =>
  agent(q.prompt, { label: `mech:${q.key}`, phase: 'Mechanism', schema: MECH_SCHEMA })
    .then(r => ({ key: q.key, result: r }))
))

phase('Critique')
const rowsDump = JSON.stringify(extracted.filter(Boolean), null, 1)
const mechDump = JSON.stringify(mechanism.filter(Boolean), null, 1)
const critique = await agent(`You are a completeness critic. Read-only; local files only; absolute paths; no remote machines.
The question: for qwen-3-4b, is prefill (TTFT) better with AMX attention on the CPU (canonical build or the VNNI-K build) or with attention on the FPGA? Decode TPS already known to favour the FPGA.

Below are the extracted TTFT rows from every result set we know of, and three code-reading answers about mechanism. Your job: (1) list what is MISSING for a definitive answer (a condition not measured, a comparison that is not apples-to-apples, a number that appears in one summary but conflicts with another, a caveat that undermines a comparison); (2) for each conflict between rows (same campaign/arm, different numbers), open the referenced files and say which is right; (3) name the 3-6 cleanest paired comparisons in the data (same binary or same day, same harness, same layout, only attention mode differs) and compute their TTFT deltas in ms and percent; (4) say whether any FPGA-attention TTFT exists for qwen-3-4b at prompt lengths above 1024; (5) propose the single measurement that would close the biggest gap (name the campaign script to fork under /home/jhan/workspace/intel-AMX/exec/ and the arms). Return plain text with sections 1-5.

EXTRACTED ROWS:
${rowsDump}

MECHANISM ANSWERS:
${mechDump}`, { label: 'critic:completeness', phase: 'Critique' })

return { extracted, mechanism, critique }