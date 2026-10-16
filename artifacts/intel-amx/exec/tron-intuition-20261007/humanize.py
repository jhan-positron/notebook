#!/usr/bin/env python3
"""Build tron-intuition-claude-humanized.html: the same generator, figures and numbers as
gen_intuition.py, with the prose edited per the humanize-writing skill (rewrite mode, formal register).
Every edit below is a (source text, replacement) pair applied to the generator source; the script
fails if an old string is missing, so the two pages cannot drift apart silently."""
import re, os, sys

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_intuition.py")
OUT = "/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/tron-intuition-claude-humanized.html"

EDITS = [
 # header
 ('Every number is measured and cited unless marked est. Generator: exec/tron-intuition-20261007/gen_intuition.py.',
  'Every number is measured and cited unless marked est. This is the humanized edition of tron-intuition-claude.html: same figures and numbers, prose revised (generator exec/tron-intuition-20261007/gen_intuition.py plus humanize.py).'),
 # short version: lead with the claim, no bold inside the list
 ('<div class="short"><b>Short version.</b> A decode step of tron is one forward over all layers for all users of one engine, and its time is other work (the weight multiplies on the FPGA cards, about flat in context) plus attention (which re-reads the whole context every step, so it grows with prompt length and with users per engine). AMX changes only the attention page visits that run on the CPU, on a full 64-token page, for a model whose attention shape fits the kernel. So the estimate by hand is: count those visits, price them with the per-unit costs, and pass the saving to the forward through the layer\'s waits and overlaps.',
  '<div class="short"><b>Short version.</b> AMX changes one thing in a decode step: the attention page visits that run on the CPU, on a full 64-token page, for a model whose attention shape fits the kernel. The step\'s time is other work (the weight multiplies on the FPGA cards, about flat in context) plus attention, which re-reads the whole context every step and so grows with prompt length and with users per engine. The estimate by hand is to count those visits, put a cost on each from the per-unit measurements, and pass the saving to the forward through the layer\'s waits and overlaps.'),
 ('<li><b>llama-3.1-8b</b> gains: +3 % at 8 users and prompt 1024 in lockstep decode, +16 % at prompt 8192, +11 to +14 % in the CI harness at 8 users per engine.</li>',
  '<li>llama-3.1-8b gains +3 % at 8 users and prompt 1024 in lockstep decode, +16 % at prompt 8192, and +11 to +14 % in the CI harness at 8 users per engine.</li>'),
 ('<li><b>qwen-2.5-32b</b> gains nothing today.', '<li>qwen-2.5-32b gains nothing today.'),
 ('<li><b>gpt-oss</b> runs attention on the FPGA', '<li>gpt-oss runs attention on the FPGA'),
 # words
 ('Every page visit then runs on the AVX loop. Same visits, same key counts, different speed.',
  'Every page visit then runs on the AVX loop. The visits and key counts stay the same, and only the speed changes.'),
 # section 2
 ('These are the facts to keep in memory. Each has one measured number attached so that a guess can be checked against it.',
  'Each rule carries one measured number, so a guess can be checked against it.'),
 ('"The path is chosen per page visit, not per model and not per token.",',
  '"The path is chosen for each page visit, so one model runs on several paths in one step.",'),
 ('"Users per engine is the lever in CI, not users in total.",', '"In CI the lever is users per engine.",'),
 ('A TPS step on the night AMX arrived is not proof: on 2026-09-23 qwen-3-4b tp4 rose +18.3 % and gpt-oss-120b +12.8 %, both AoF rows with 0 AMX visits, in a package with two other merges',
  'A TPS step on the night AMX arrived does not prove the kernel caused it. On 2026-09-23 qwen-3-4b tp4 rose +18.3 % and gpt-oss-120b +12.8 %, both AoF rows with 0 AMX visits, in a package with two other merges'),
 # section 5
 ('"5. What a unit costs, and why the kernel\'s gain is 1.3x and not 8x"', '"5. What a unit costs, and why the kernel gains 1.3x per unit"'),
 ('Two consequences for estimates. First, use the row that matches the context: 0.50 us saved per unit at prompt 256, 0.66 at 2048, 0.75 at 8192 (canonical kernel). Second, the AMX tile does useful work on 4 of its 16 rows in private decode (one query token per user, 4 query heads per KV head), so the 8x instruction-level figure never applies to decode. It applies to prefill, where many query tokens share a page [make-sense-amx-vs-avx.html section 4].',
  'Two consequences follow for estimates. First, use the row that matches the context: 0.50 us saved per unit at prompt 256, 0.66 at 2048, 0.75 at 8192 (canonical kernel). Second, in private decode the AMX tile does useful work on 4 of its 16 rows (one query token per user, 4 query heads per KV head). The instruction-level 8x is reached only in prefill, where many query tokens share a page [make-sense-amx-vs-avx.html section 4].'),
 ('"Takeaway: once the pages come from DRAM the unit sits near the memory time whatever the arithmetic does. AMX saves 0.5 to 1.0 us of 3.6 us (1.26x with the canonical kernel), not the 1.1 us it saves when the page is hot. Sources:',
  '"Once the pages come from DRAM the unit sits near the memory time whatever the arithmetic does. AMX then saves 0.5 to 1.0 us of 3.6 us (1.26x with the canonical kernel). With the page hot in L2 it saves 1.1 us. Sources:'),
 # figure 2 panel (a) red note
 ('red="the kernel shortens the jobs (busy per job 98 -> 89 us, mean over workers) but not the period.",',
  'red="the kernel shortens the jobs (busy per job 98 -> 89 us, mean over workers). The period stays at 247 us.",'),
 # recipe steps: no bold labels
 ('"<b>Fix the cell.</b> Model, tp, users per engine U, prompt length, attention mode (AoF or CPU), and the two arms (kill switch vs kernel, or AVX build vs AMX build). Take the context at mid-run: prompt plus 128 generated tokens.",',
  '"Fix the cell: model, tp, users per engine U, prompt length, attention mode (AoF or CPU), and the two arms (kill switch vs kernel, or AVX build vs AMX build). Take the context at mid-run, prompt plus 128 generated tokens.",'),
 ('"<b>Decide what is on the CPU.</b> Figure 3: under AoF only the 1-to-4-key tails and the sliding-window layers are on the CPU, and no page is full. Under CPU attention every page is on the CPU.",',
  '"Decide what is on the CPU with Figure 3. Under AoF only the 1-to-4-key tails and the sliding-window layers are on the CPU, and no page is full. Under CPU attention every page is on the CPU.",'),
 ('"<b>Count the kernel-eligible visits per forward per worker.</b> U x (layers on the CPU) x KV heads x full pages per user, divided by the attention workers (Table 1 gives the worker counts the split heuristic chose). Only models that pass the shape gate have any.",',
  '"Count the kernel-eligible visits per forward per worker: U x (layers on the CPU) x KV heads x full pages per user, divided by the attention workers (Table 1 gives the worker counts the split heuristic chose). Only models that pass the shape gate have any.",'),
 ('"<b>Price them.</b> Saving per worker per forward = visits x (AVX unit - AMX unit) at that context: 0.50 us at prompt 256, 0.66 us at 2048, 0.75 us at 8192 (Figure 4). This is the drop in T2 summed over a worker\'s jobs.",',
  '"Put a cost on them. The saving per worker per forward is visits x (AVX unit - AMX unit) at that context: 0.50 us at prompt 256, 0.66 us at 2048, 0.75 us at 8192 (Figure 4). This is the drop in T2 summed over a worker\'s jobs.",'),
 ('"<b>Pass the saving to the forward.</b> One minibatch, or attention over 90 % of the forward: 1:1. llama at 8 users and a short prompt: about one third. New T1 = T1 - pass x saving. Gain = T1 / new T1 - 1.",',
  '"Pass the saving to the forward. With one minibatch, or with attention over 90 % of the forward, the pass is 1:1. For llama at 8 users and a short prompt it is about one third. New T1 = T1 - pass x saving, and the gain is T1 / new T1 - 1.",'),
 ('"<b>Check against an anchor.</b> Table 1, Figure 5 or the nightly rows. When no anchor exists, name the cell to run (TRON_ATTN_STATS=1, both arms) instead of trusting the number.",',
  '"Check against a reference cell: Table 1, Figure 5 or the nightly rows. When none exists, name the cell to run (TRON_ATTN_STATS=1, both arms) instead of trusting the number.",'),
 # example A
 ('Measured: busy per job fell from 103 to 91 us over 64 jobs per worker per forward = 0.77 ms.',
  'The measurement agrees: busy per job fell from 103 to 91 us over 64 jobs per worker per forward, 0.77 ms.'),
 ('Measured: T1 8.92 -> 8.66 ms, TPS 110.7 -> 113.9 per user = +2.9 %.',
  'The run measured T1 8.92 -> 8.66 ms and TPS 110.7 -> 113.9 per user, +2.9 %.'),
 ('Measured drop of T2 over the 64 jobs: (679 - 574) us x 64 = 6.7 ms.',
  'The measured drop of T2 over the 64 jobs was (679 - 574) us x 64 = 6.7 ms.'),
 ('Measured: 39.64 ms, TPS 21.4 -> 24.8 = +16.0 %.', 'The run measured 39.64 ms and TPS 21.4 -> 24.8, +16.0 %.'),
 # example B
 ('Measured: TPS -0.9 % at prompt 1024 and -0.5 % at prompt 8192 with the kernel on, busy per job equal within 1 %, 0 AMX visits in both cells',
  'The runs measured TPS -0.9 % at prompt 1024 and -0.5 % at prompt 8192 with the kernel on, busy per job equal within 1 %, and 0 AMX visits in both cells'),
 ('The useful question for qwen3-4b is therefore AoF vs CPU attention, not AMX vs AVX: at prompt 1024 and 8 users AoF gives 126.6 TPS per user against 79.5 with CPU attention and the kernel (1.6x).',
  'For qwen3-4b the question that matters is AoF vs CPU attention. At prompt 1024 and 8 users AoF gives 126.6 TPS per user against 79.5 with CPU attention and the kernel (1.6x).'),
 # example C
 ('means a kernel for its shape would pay. The map answers in four lines.")', 'means a kernel for its shape would pay.")'),
 ('"<b>What is on the CPU.</b> The 18 card layers keep a 1-to-4-key tail', '"On the CPU: the 18 card layers keep a 1-to-4-key tail'),
 ('"<b>Kernel-eligible visits.</b> One full page per (user, KV head, sliding layer) per step: 8 x 8 x 18 = 1,152 per forward, holding half of those layers\' keys. Today the shape gate (64 wide, kv_mul 8) sends them to the AVX loop.",',
  '"Kernel-eligible visits: one full page per (user, KV head, sliding layer) per step, 8 x 8 x 18 = 1,152 per forward. They hold half of those layers\' keys. Today the shape gate (64 wide, kv_mul 8) sends them to the AVX loop.",'),
 ('"<b>Time.</b> Busy per job in a sliding-window layer is 36.0 us (29.4 us scoring plus 6.6 us join wait), 18 jobs per worker per forward = 0.65 ms = 6.3 % of the 10.26 ms forward (Figure 2d). The join wait does not change with a kernel, so the ceiling for any kernel is the 0.53 ms of scoring = 5.2 % of T1.",',
  '"Time: busy per job in a sliding-window layer is 36.0 us (29.4 us scoring plus 6.6 us join wait), and 18 jobs per worker per forward make 0.65 ms, 6.3 % of the 10.26 ms forward (Figure 2d). The join wait does not change with a kernel, so the ceiling for any kernel is the 0.53 ms of scoring, 5.2 % of T1.",'),
 ('"<b>Price.</b> On the fitting models the kernel cut decode busy per job by 12 to 16 % while taking 96 to 99 % of the keys (Table 1: llama 103 -> 91 us, qwen 229 -> 193 us). Half the keys at that rate is 6 to 8 % of 0.65 ms = 0.04 to 0.05 ms per forward = 0.4 to 0.5 % of T1 (est.). Pass 1:1 (one minibatch). So the answer is: under 1 % of decode TPS, with 5.2 % as the ceiling.",',
  '"Cost: on the fitting models the kernel cut decode busy per job by 12 to 16 % while taking 96 to 99 % of the keys (Table 1: llama 103 -> 91 us, qwen 229 -> 193 us). Half the keys at that rate is 6 to 8 % of 0.65 ms, 0.04 to 0.05 ms per forward, 0.4 to 0.5 % of T1 (est.). The pass is 1:1 (one minibatch). So the answer is under 1 % of decode TPS, with 5.2 % as the ceiling.",'),
 ('Two cautions that the map makes visible. The 128-key window of one KV head is 32 KiB and stays in cache across steps. So the per-key cost there is the cache-regime one, not the 3.6 us DRAM unit (Insufficient data for the exact value: only a built kernel measures it). Prefill has more room than decode.',
  'One caution: the 128-key window of one KV head is 32 KiB and stays in cache across steps, so the per-key cost there is the cache-regime one and the 3.6 us DRAM unit does not apply (Insufficient data for the exact value: only a built kernel measures it). Another: prefill has more room than decode.'),
 # example D
 ('Predicted AMX gain today: 0.', 'So the predicted AMX gain today is 0.'),
 # section 8
 ('Six cards. Cards 1 to 3 are the inputs of the recipe. Cards 4 to 6 are how to measure and where to read more.',
  'Cards 1 to 3 below are the inputs of the recipe. Cards 4 to 6 say how to measure and where to read more.'),
 ('"Card 4: switches, commands, and where the counters appear"', '"Card 4: how to run a cell and where the counters appear"'),
 ('"Card 5: measured anchors beyond Table 1"', '"Card 5: reference measurements beyond Table 1"'),
 ('caption="Table 3. Anchors to check an estimate against. Each row names its harness and layout: never compare across harnesses."',
  'caption="Table 3. Reference measurements to check an estimate against. Each row names its harness and layout, and numbers from different harnesses are not comparable."'),
 # section 9 edge 1
 ('Hypothesis: in continuous batching a user\'s decode steps share forwards with other users\' prefill chunks, and the kernel speeds those jobs 1.7x to 2.5x, so the per-user token interval drops more than the pure decode step. Measurement that decides it: the TRON_ATTN_STATS exit report of one rinzler engine under the CI harness, both arms, reading the T1 sums of the decode_like and prompt_or_mixed classes.',
  'One hypothesis: in continuous batching a user\'s decode steps share forwards with other users\' prefill chunks, and the kernel speeds those jobs 1.7x to 2.5x, so the per-user token interval drops more than the pure decode step. The measurement that decides it is the TRON_ATTN_STATS exit report of one rinzler engine under the CI harness, both arms, with the T1 sums of the decode_like and prompt_or_mixed classes.'),
]

def strip_bold(src, start_marker, end_marker):
    i = src.index(start_marker); j = src.index(end_marker, i)
    seg = src[i:j].replace("<b>", "").replace("</b>", "")
    return src[:i] + seg + src[j:]

def main():
    src = open(GEN).read()
    for old, new in EDITS:
        n = src.count(old)
        if n != 1:
            sys.exit("edit not applicable (%d matches): %s" % (n, old[:90]))
        src = src.replace(old, new)
    # bold labels inside the edges list and the Card 6 file list
    src = strip_bold(src, 'def section_edges():', 'def section_sources():')
    src = strip_bold(src, 'H3("8f", "Card 6: where the detail lives")', '    return s\n\ndef section_edges')
    src = src.replace('OUT = "/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/tron-intuition-claude.html"',
                      'OUT = "%s"' % OUT)
    ns = {"__name__": "gen_intuition_humanized", "__file__": GEN}
    exec(compile(src, GEN, "exec"), ns)
    ns["build"]()
    print("edits applied:", len(EDITS))

if __name__ == "__main__":
    main()
