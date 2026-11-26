export const meta = {
  name: 'gdn-review-round1-findings',
  description: 'Investigate the 7 reviewer findings of round 1 against data and source, and propose exact corrections (read-only)',
  phases: [
    { title: 'Investigate', detail: 'one investigator per finding or group of small findings' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'
const D = '/home/jhan/workspace/intel-AMX/exec/gdn-20261120'

const COMMON = [
  'You help the author of a design page answer a finding of an external reviewer. Your job: check the reviewer\'s claim against the data and the source, establish the facts with evidence, and propose the exact corrections. You do not edit any project file. The author applies the corrections.',
  '',
  'The page: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html (sha256 8a9fbfa5b4a1f2d4ad7d1b78b7583def92bd3cf1ce65ea7a6e6563749be5ec57). Title: "GDN and AMX: design for Qwen3.5 4B". It reports a measured baseline of the Qwen3.5 4B model in tron (an inference program) on the server delphi-3b35, a prediction of what three proposed changes (Part 0: a new loop order for the GDN layers without AMX; Part A: an AMX block kernel for GDN; Part B: an AMX attention kernel for 256-wide heads) would do to the time to first token (TTFT) and to the decode speed, and a software design. Nothing is built yet.',
  'Plain-text extraction of the page: ' + SP + '/page-text.r1c.txt (539 lines; figures appear as [SVG: ...] and [SVG-TEXT: ...] lines). Read the sections that your finding names, and the "Words used here" list at the top.',
  'The review record with all 7 findings: /home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html.review.md (the entry with role=reviewer status=COMMENTS).',
  '',
  'Where things are (all under /home/jhan/workspace/intel-AMX unless noted):',
  '- exec/gdn-20261120/ : gen_design.py (generates the page; most section text is here), design_numbers.py (numbers and text blocks of sections 4 to 7), predict.py (the prediction; formulas and factors), figs_static.py, figs_design.py, figs_data.py, pagelib.py (figures), collect.py (parses run logs into collected.json), analyze_trace.py.',
  '- exec/results/gdn-20261120/ : collected.json (2.7 MB: load it with python and index into it, never print it whole), predictions.json, rt-results.txt, rt/*.log (run logs with the attention statistics lines), trace/*.summary.json, bench/*.txt.',
  '- exec/gdn-20261120/design-checks/ : check scripts with saved outputs (*.out, *.json) in the folders kernel, proto, skeptic, integration, lead, verify-math, verify-cost, verify-fit, review.',
  '- /home/jhan/workspace/ai-runs/tron-qwen35-4b : read-only copy of the tron source at commit 72e1191804 (README.stats.md, h/tron/models/attn_stats.hpp, h/tron/kernels/gated_delta_net.hpp, h/tron/models/self_attention.hpp, src/tron/kernels/amx_attn.cpp and so on).',
  '',
  'Hard rules:',
  '- Read-only. Do not modify, create or delete any file under /home/jhan/workspace. Do not run gen_design.py, predict.py, collect.py or analyze_trace.py as programs (they overwrite outputs). You may import predict.py logic by copying the file into your scratch folder and changing its output path there.',
  '- Do not ssh to any machine. Do not use the network.',
  '- Scratch files go only under ' + SP + '/round1/<finding id>/ (create the folder). If you write a script that computes numbers for the page, keep it small, pure python, deterministic, with a docstring that says what it computes and from which files, and save its output beside it as <name>.out. The author will copy it into the project as evidence.',
  '- Set PYTHONDONTWRITEBYTECODE=1 when you run python.',
  '',
  'Rules for the text you propose (the page follows them): plain English for engineers. Short sentences, one claim per sentence. No idioms, no metaphors, no semicolons. Every number has a unit. Every estimate carries "(est.)". A term from the code or an abbreviation is defined at first use or is in the "Words used here" list. ASCII only (write "x" for times, "us" for microsecond). Do not narrate the history of the page ("we corrected", "previously"). Keep the change as small as the finding allows, and say which other places of the page repeat the same statement and need the same change.',
  '',
  'First decide whether the reviewer is right: yes, partly, or no. If you disagree, give the evidence. Do not agree out of politeness and do not defend the page out of habit. Then give the facts with evidence (file and line, or the command you ran and the value). Then give the proposed changes as a list of (place on the page, exact old text, exact new text). If a change needs new numbers, compute them with a script as described above.',
  '',
].join('\n')

const FINDINGS = [
  {
    id: 'R1',
    prompt: [
      'Finding R1 (verbatim): "Sections 3 and 4, attention time. The prediction scales all of busy_cycles. That counter includes workers waiting for each other in the join. The reported \'attention wait\' also subtracts the average busy time across workers from the wall time of worker 0. That difference cannot identify time spent waiting for K and V alone. At 1 user and prompt 1,024, join wait accounts for 1.449 ms of the 6.038 ms of prefill busy time per worker. At 8 users and prompt 8,192, it accounts for 1.392 ms of the 8.900 ms in decode. Define both timers accurately. State the assumption about which time scales with the kernel, and show how Part B changes if join wait stays fixed, or justify an effective factor for the entire timer. Also identify partial pages as AVX-512 work where a factor comes from a full-page kernel count. Evidence comes from README.stats.md lines 290-298, collect.py lines 97-98, and the six-run medians in collected.json."',
      '',
      'What to establish:',
      '1. The exact definitions of the timers in tron: busy_cycles, join_wait_cycles (is it inside busy_cycles?), wall_cycles_w0, and any other field the page uses. Read README.stats.md around lines 270-310 and h/tron/models/attn_stats.hpp, and how collect.py and predict.py turn them into "attention busy time" (sum over workers / 40) and "attention wait" (wall of worker 0 minus that).',
      '2. Per cell (1 or 8 users x prompt 1,024 / 4,096 / 8,192), for a prefill pass and for a decode step, from the six-run medians in collected.json: busy time per worker, join wait per worker and its share of the busy time, the wall of worker 0, and the page\'s "attention wait". Reproduce the reviewer\'s two numbers (1.449 of 6.038 ms and 1.392 of 8.900 ms).',
      '3. Partial pages. tron\'s AMX attention kernel serves only full 64-token pages. The tokens of the pass in progress sit in a partial page and stay on AVX-512. Find what the statistics record about this (K tokens per path, per page kind, per kernel: look at the attn-stats lines of a run log and at README.stats.md) and compute, per cell, the share of the scored K tokens that lie in full pages, for prefill and for decode. If the statistics do not split it, derive it from the pass structure (128 prompt tokens per pass per user, 64-token pages) and say so.',
      '4. How the factors were derived, to judge what they may be applied to. The prefill factor (2.95 to 3.05 on delphi-3bda) is a fit of whole prefill times T = a p + b p^2 (AVX-512) and a p + b p^2 / s (AMX), see design-checks/review/attn_prefill_fit.py: say which part of the attention time the fitted s speeds up (the part that grows with p^2, which is the full-page work with its waits) and which part stays in the linear term. The low case 1.6 is a count for one full page (design-checks/review/attn_256_l2_count.py). The decode factor (0.9 / 1.0 / 1.17) comes from measured attention time per token on delphi-3bda (Ref19).',
      '5. Recompute the Part B prediction (TTFT per cell at low / working / high, and decode speed) under three assumptions: (a) as on the page: the whole busy time is divided by the factor; (b) only the full-page share of the busy time is divided by the factor, the partial-page share stays; (c) as (b), and the join wait also stays fixed. Give the tables and the summary ranges in the form the page uses ("TTFT falls by X to Y % (est.), range ..."), and the same for Parts A and B together. Write this as a script with a saved output.',
      '6. Recommend which assumption the page should use as its working model and which it should show as a sensitivity, with reasons. Consider: partial pages are certain AVX-512 work. Whether the join wait scales with the kernel is not known (it shrinks with the kernel if it comes from uneven work shares, and it stays if it comes from wake-up latency): look in the data for a hint (does the join wait per pass grow with the prompt length like the kernel time does, or is it flat?).',
      '7. Propose the exact text: accurate definitions for the "Words used here" entries "attention busy time, attention wait" and for the section 3 bullets "Attention busy time" and "Attention wait" (the page says the worker waits for K and V from the FPGA cards: say what the difference of the two timers can and cannot identify), a statement of the assumption in section 4, and the sensitivity result. If predict.py must change, give the exact formula change.',
    ].join('\n'),
  },
  {
    id: 'R2',
    prompt: [
      'Finding R2 (verbatim): "Section 6, task 6. The GDN-only switch compares Part A with Part 0, while the Part A range in section 4 uses today\'s original kernel as its baseline. A correct implementation can fail this pass rule. For 8 users at prompt 1,024 with Part B disabled, the working estimates are 2.235 s for Part 0 and 2.060 s for Part A. That is a 7.8% reduction with the switch and a 29.1% reduction from the original 2.907 s. Specify the runs and denominator for each comparison, including the fixed Part B setting. Use the original baseline for the total Part A range and the paired run for its incremental gain. Evidence comes from predictions.json and the switch definitions in section 5.6."',
      '',
      'What to establish:',
      '1. Read section 6 (the plan table, tasks 1 to 6) and section 5.6 (row "Switches"). For each task that measures TTFT or decode speed in tron (tasks 2, 5 and 6), work out which two builds or switch settings each comparison uses and what each one runs for GDN prefill and for attention. Note what the kill switch (TRON_AMX_DISABLE=1) does once Part 0 exists: with the kill switch set, GDN prefill runs Part 0 and attention runs AVX-512. Check whether task 5 (Part B, "A/B with the kill switch") has the same denominator problem as task 6: when task 5 runs, Part 0 is already in the build, so both arms include Part 0, while the Part B range of section 4 is relative to today\'s build.',
      '2. From predictions.json (and predict.py for the model) compute per cell, at the working values: TTFT of today, of Part 0, of Part A, of Part B alone, of Part 0 with Part B, and of Parts A and B. Then the paired changes: Part A against Part 0 with Part B off, Part A against Part 0 with Part B on, Part B on against off on a Part 0 build, Part B on against off on a Part A build. Give each as seconds and as a percent of the comparison run, and also as a percent of today\'s TTFT. Reproduce the reviewer\'s numbers (2.235 s, 2.060 s, 7.8 %, 29.1 %). Also give the low and high cases where the model defines them without mixing cases (say which combinations you used). Write this as a script with a saved output.',
      '3. Propose new pass rules for tasks 2, 5 and 6 that name, for each comparison: run 1, run 2 (build and switch settings, including the Part B setting), the quantity, and the denominator. Follow the reviewer: the total range of a part is measured against the original build (today\'s kernel, measured again in the same session on the same machine state), and the incremental gain is measured in the paired run with the switch. Keep the rule that Part A must beat Part 0. Keep each table cell short. If the table gets too wide, propose a small second table "Which runs each task compares" under the plan table, and one with the predicted paired changes per cell (working values, est.).',
      '4. Give the exact old and new text for the plan table cells and for the Switches row of section 5.6 if it needs a sentence.',
    ].join('\n'),
  },
  {
    id: 'R3',
    prompt: [
      'Finding R3 (verbatim): "Sections 5.3 and 5.4, FP32 split. The design says each FP32 value is exactly the sum of three bf16 values. Even three bf16 values cannot sum to the smallest positive FP32 subnormal, 2^-149, because every finite bf16 is a multiple of 2^-133. Specify the tested truncation rule for the leading piece and residual pieces. Distinguish exact representation for the supported magnitude range from loss of tiny residuals on the tile. The default round-to-nearest conversion also overflows for some finite inputs above 3.396178e38. Evidence comes from kernel/02_split3_exhaustive.out and verify-math/vm_checks.out part C."',
      '',
      'What to establish:',
      '1. Read design-checks/kernel/02_split3_exhaustive.py and .out, design-checks/kernel/gdn_common.py (bf16_rne, bf16_trunc), design-checks/verify-math/vm_checks.py and .out part C, verify-math/vm_subnormal.py and .out, and the split code of the prototype (design-checks/proto/gdn_block_proto.py). State exactly which split rule each check tested: how the leading piece is made (truncation toward zero or round to nearest even), how the second and third pieces are made, and in which arithmetic the residuals are computed.',
      '2. State the exact results: for which magnitude range the three pieces sum to the FP32 value bit for bit (the page says 9.9e-32 or larger: give the exact power of two and what happens at the top of the range, near the largest FP32 value 3.4028235e38), what happens below that range (which pieces become subnormal bf16 values or zero, how large the lost part is: the page says below 1.2e-38), what happens with round to nearest for the leading piece (the reviewer says it overflows for some finite inputs above 3.396178e38: confirm the threshold from the check output or compute it), and whether the exhaustive check covered every finite FP32 bit pattern including subnormal inputs. Check the reviewer\'s statement that every finite bf16 is a multiple of 2^-133 and that 2^-149 cannot be a sum of bf16 values.',
      '3. Distinguish two different things, as the reviewer asks: (i) exact representation: for which inputs the three pieces add up to the input, as numbers; (ii) what the tile product does with pieces that are subnormal bf16 values (TDPBF16PS treats subnormal inputs as zero and flushes subnormal results to zero), so a piece that exists as a number can still be lost on the tile.',
      '4. Read the page sentences that speak about the split: section 5.3 bullet "The FP32 state", section 5.4 bullets "The 3-piece split is exact", "Below 9.9e-32", "Two pieces are not enough", "Fallback", the "Words used here" entry "piece, plane", and the Tests row of section 5.6. Propose exact new text: section 5.3 must not say "exactly" without the range; section 5.4 must name the rule that was tested (leading piece by truncation, and so on), the range where the sum is exact, what is lost below it, and that round to nearest for the leading piece overflows near the top of the range (with the threshold), and what the design does with non-finite or out-of-range values (the page has a fallback for non-finite start states: say whether the checks cover the top of the range).',
    ].join('\n'),
  },
  {
    id: 'R5',
    prompt: [
      'Finding R5 (verbatim): "Sections 5.3 and 6, block timing. The report gives one 0.2-0.4 us interval for transitions throughout the block. Stage 3 alone has 9,216 consecutive AVX-512 operations per block according to Figure 12. At the report\'s optimistic 0.50 cycles per operation and 2.40 GHz that stage costs 1.92 us (est.) before tile work resumes. Name the phase covered by each estimate, or remove the single interval. Distinguish one phase from the full tile-plus-vector iteration timed by the clock probe. The clock of the proposed kernel can remain an open measurement."',
      '',
      'What to establish:',
      '1. The phases of the proposed block kernel for one value head and one block of 32 tokens, in execution order, from the page (section 5.3 bullets "Stage 1 in detail", "Stage 4 in detail", figure 12, the cost table) and from the counts in design-checks/verify-cost/recount_tiles.out (sections "GDN BLOCK KERNEL (G2)" at C = 32 and "AVX-512 PARTS OF G2") and design-checks/lead/lead_costs.out. For each phase: is it tile work or AVX-512 work, how many instructions, how many times it repeats per block (for example stage 1 takes 16 value columns at a time: 8 repeats), and its length in cycles and in us at 2.40 GHz and at 1.90 GHz. Use the page\'s instruction costs (design_numbers.py: 16.17 cycles per TDPBF16PS, 8.38 per tile load, 16.1 per tile store, 0.50 to 0.613 cycles per AVX-512 operation). Write this as a script with a saved output.',
      '2. Do the same for the attention kernel of Part B: one page visit has two runs of 32 tile products (QK 920.8 cycles, PV 1,120 cycles in recount_tiles.out) with AVX-512 work before, between and after. The page says "about every 0.4 to 0.6 us (est.)" for these.',
      '3. What the clock probe measured (exec/gdn-20261120/clock_probe.cpp, bench/clock-probe.txt, clock-probe2.txt): the short turn is 4 tile products followed by 64 FMAs (35 ns for the whole turn), the long turn is 4,096 tile products followed by 16,384 FMAs (33 us for the whole turn). Give the length of the tile part and of the FMA part of each turn separately, so that the page can compare like with like (one phase against one phase, one full turn against one full turn).',
      '4. Propose exact new text for: section 5.3 bullet "Clock" ("So tile work and AVX-512 work take turns about every 0.2 to 0.4 us (est.). The clock probe covered turns of 35 ns (1.90 GHz) and of 33 us (2.40 GHz) ..."), section 4 clock note bullet "Turn lengths between these two were not probed. The block kernel and the attention kernel both lie between. ...", section 6 open point "Core clock under AMX in tron" ("In the block kernel, tile work and AVX-512 work take turns every 0.2 to 0.4 us (est.). In the attention kernel they take turns about every 0.4 to 0.6 us (est.). The probe covered turns of about 35 ns and of about 33 us. ..."), and section 5.5 bullet "Clock (hypothesis)". The new text must name the phase that each number belongs to, must include stage 3 (the long AVX-512 phase), must say plainly that the phase lengths are estimates from counts, and must keep the clock of both kernels as an open measurement (tasks 3 and 4). A compact table of the phases with their lengths is welcome if it is short (propose it as rows).',
      '5. Check whether the statement "The block kernel and the attention kernel both lie between" (between the two probed turn lengths) is still true for every phase, and say what follows for the working assumption of 2.40 GHz for the block kernel.',
    ].join('\n'),
  },
  {
    id: 'R467',
    prompt: [
      'You handle three small findings: R4, R6 and R7. Treat each one separately and return them all.',
      '',
      'Finding R4 (verbatim): "Figure 2, GDN read equation. The figure calls q a normalized bf16 query and gives the output as q times S. The token kernel multiplies the normalized query by 1/sqrt(key_head_dim) in FP32 before accumulation. At width 128, omitting that factor changes the output magnitude by about 11.31 times. Include the scale and identify where the reference applies it. Figure 12 already shows a scale in the block form. Evidence comes from gated_delta_net.hpp lines 239-242 and 287-296."',
      'For R4: read h/tron/kernels/gated_delta_net.hpp (the whole recurrence function and the notes at the top) in /home/jhan/workspace/ai-runs/tron-qwen35-4b. Establish the exact order of operations of the four lines of the recurrence for one token (recall, correct, write, read): which values are bf16, which FP32, where the scale 1/sqrt(key_head_dim) is applied (to q before the read loop? to the result?), whether k is scaled too, and where rounding to bf16 happens. Then check the four formula lines of figure 2 (in exec/gdn-20261120/figs_static.py, function token_flow: three columns per line: number, step name, formula) and the note under them ("k, q, v are bf16 values. S, decay and delta are FP32."), the "Words used here" entries "recurrence" and "decay, beta", and figure 12 (figs_design.py, block_kernel: the stage 3 formulas and the notes under the box, where "scale" is used but may not be defined). Propose exact new strings for the figure lines and notes. Keep each formula line short: at most 34 characters for a figure 2 formula (monospace, 7.5 px per character, starting at x = 631.5 in a figure 960 px wide) and at most 52 characters for a figure 12 note line. Say whether any other place of the page writes the read step without the scale.',
      '',
      'Finding R6 (verbatim): "Section 3 and Figure 7, \'upper values.\' A longer traced pass does not by itself prove that traced GDN wall time bounds untraced GDN wall time. The trace also uses 32 generated tokens instead of 256 and omits the first decode pass from the mean. Label these as estimates using a traced numerator. The untraced GDN counters proposed in section 5.6 would establish the direction and size of any bias. Apply the same qualification where the 1.8 ms scheduling estimate relies on this being an upper bound."',
      'For R6: find every place of the page that calls the decode GDN shares or a number derived from them "upper values", "upper value", "up to" or "at most" on the ground that the GDN wall comes from a traced run: the section 3 bullet "Limit of the decode numbers", the caption of figure 7 and its takeaway sentence ("GDN takes up to 15 % of a step with 1 user and up to 35 % with 8 users"), the head of the decode table, the block "Seen in the same data" in section 4 ("at most 1.8 ms ... an upper value because ..."), the section 5.1 table row "GDN, decode", and any other. Check in the data whether anything supports the direction of the bias (for example: is the traced GDN wall per decode step larger than a value that can be bounded from untraced runs? The untraced runs have no GDN timer, so probably nothing does: say so). Propose exact new text that labels these numbers as estimates with a traced numerator and an untraced denominator, states the three differences between the traced and the untraced runs (tracing on, 32 instead of 256 generated tokens per user, the first decode pass left out of the traced mean), says that the direction and the size of the bias are not known, and names the measurement that would give them (the untraced GDN wall counter proposed in section 5.6, row "Counters"). The table column "GDN share inside the traced run (%)" can stay.',
      '',
      'Finding R7 (verbatim): "Section 4, \'What would prove the prediction wrong.\' A Part 0 step between 3.5 and 4.6 us does not identify cheaper state movement as its cause. Slower L1 execution or more expensive conversion, normalization or copies can give the same total. Present the cause as a hypothesis and name the component timing that distinguishes it. In the same paragraph, a smaller pass-level saving also does not establish overlap by itself. The report\'s own rest-of-pass clock cost can reduce that saving on a serial path. Specify the controlled comparison needed for that inference."',
      'For R7: read the three bullets under "What would prove the prediction wrong" and the Part 0 basis bullets of the factor table in section 4, and the plan table of section 6 (task 1 measures a stand-alone benchmark of the recurrence at the working-copy size: today\'s kernel and the column-half order, in us per value head per token). Propose exact new text for the Part 0 bullet: the sentence about a step between 3.5 and 4.6 us must present the cheaper movement of the state as one hypothesis among the causes the reviewer lists, and must name the timings that separate them (for example: the recurrence alone on a 32 KiB slice that stays in L1, against the same loop on the 128 KiB working copy, in task 1; and separate timers for the copy into the contiguous buffer, the normalization and the other per-token work in task 2). Propose exact new text for the bullet "The method": say which comparison isolates the serial-path assumption (a comparison without AMX, so that no core clock changes: Part 0 against today\'s build, where the fall of the pass wall must equal the fall of the GDN wall, both measured with untraced counters or both in traced runs), and that for Part A the clock cost on the rest of the pass must be subtracted first. Keep both bullets short.',
    ].join('\n'),
  },
]

const SCHEMA = {
  type: 'object',
  properties: {
    answers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'R1 .. R7' },
          reviewer_right: { type: 'string', enum: ['yes', 'partly', 'no'] },
          verdict: { type: 'string', description: 'two or three sentences: what is true' },
          facts: { type: 'array', items: { type: 'object', properties: { fact: { type: 'string' }, evidence: { type: 'string' } }, required: ['fact', 'evidence'] } },
          changes: { type: 'array', items: { type: 'object', properties: { place: { type: 'string' }, old_text: { type: 'string' }, new_text: { type: 'string' }, file_hint: { type: 'string' } }, required: ['place', 'old_text', 'new_text', 'file_hint'] } },
          numbers: { type: 'string', description: 'tables or key numbers, as plain text' },
          scripts: { type: 'string', description: 'absolute paths of scripts and outputs written in the scratch folder, or empty' },
          open_points: { type: 'string' },
        },
        required: ['id', 'reviewer_right', 'verdict', 'facts', 'changes', 'numbers', 'scripts', 'open_points'],
      },
    },
  },
  required: ['answers'],
}

phase('Investigate')
const results = await parallel(FINDINGS.map(f => () =>
  agent(COMMON + f.prompt, { label: 'investigate:' + f.id, phase: 'Investigate', schema: SCHEMA }).then(r => ({ key: f.id, result: r }))
))
return results.filter(Boolean)
