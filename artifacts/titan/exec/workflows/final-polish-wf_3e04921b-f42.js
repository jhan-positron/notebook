export const meta = {
  name: 'final-polish',
  description: 'Add four supplementary evaluations to the final-data script and the report generator, with review (local only)',
  phases: [{ title: 'Build' }, { title: 'Review' }],
}
const COMMON = `
Context. Read first: /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-progress.md (newest entries last; the last entry explains item 1 below), the decisions file /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx8-2026-11-14/DECISIONS-bwx8.md from "## Second agent, 2026-11-15" to the end, and A/final8.txt.
Names: N = /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel ; A = N/tackle-8mb-analysis ; R = /home/jhan/workspace/titan/cache-perf/crb/results .
Files you may change: A/final8.py, A/test_final8.py, A/report_final.py, A/test_report_final.py (and the generated A/final8.json, A/final8.txt, N/tackle-8mb-report.html by re-running the generators). Nothing else. Local machine only; NEVER run ssh/scp or contact CRB or any delphi/andoria machine. Python 3 standard library only. No "cd" into /tmp; use the scratchpad for temporary files. Follow the skills "plain-english" and "dataviz" for every text and chart you add (light background only).
Session 2 of round 4 (steps ZC, ZD, ZN, ZM) and of step ZS is still being measured; the code must keep working with whatever folders exist and give the both-session wording by itself when they arrive.
Principle: the verdicts by the recorded rules stay exactly as they are. Every addition below is a SUPPLEMENTARY evaluation: it is labelled in the output as "supplementary, defined after the data was seen", it is printed beside the recorded verdict, and it never replaces it.`

const BUILD = `${COMMON}
YOUR TASK: four additions, each in final8.py (json + txt, with tests in test_final8.py that can fail) and shown in report_final.py (with the table-number test of test_report_final.py still passing).
1. YP against the round 1 series. The up-switch windows of the 60 s runs of round 1 (step S4, both sessions; take them from the data: the recurring up times of item 5 in window units, expected 21, 44, 67, 90, 114, 137 and 179) form the reference series U. For a pad P the prediction is the set { u - P/80 : u in U } cut to the windows 0 to 99. For every padded process of YP (both sessions) report: its up windows, the predicted windows, how many of its ups lie within 1 window of a predicted window, and how many predicted windows have an up within 1 window given that the process was at the low level just before that window (a process at the high level cannot show an up; use the level segmentation that final8 already has; if that is too costly, report the first count only and say so). Then per pad, CPU and session the share of ups that match, and one summary line per session and overall. Do the same for the recurring falls of round 1 (expected windows 16, 42, 69, 95, 122, 148, 168, 194) as a second table. In the report: add this to section 7.3 under the recorded verdict, and make the pad figure draw the predicted positions from U (hollow marks) so both sessions can be read; keep the recorded verdict text.
2. Old read without its vector adds. Kernel read_sparse (step XN) has the same loads and the same count of instructions per 128 B as old read, with 9 no-operation instructions in place of the 8 vector adds. Report per CPU and session the 32 KiB cell medians of old read (step S2) and of read_sparse (step XN) and their ratio, and the same at 1 MiB and 8 MiB. In the report (section 4 or 2) state it as a test that changed the old loop: removing the adds raises the 32 KiB rate from about 66.7 to about 133 GB/s, so the adds (not the loads) set the cost of old read; say that the two kernels differ also in loop offset (4 against 40 modulo 64, from the decisions file / build record) as a limit.
3. The prefetch family at 1 MiB (steps YC, YF), both sessions: per CPU and session the share of asmread first-level long misses that each prefetch kernel keeps at 1 MiB and at 8 MiB, and the rate difference to asmread (cell medians) at both sizes. State under the recorded verdict of rule 3: at 1 MiB the prefetch removes X to Y % of the misses and the rate is Z GB/s lower in all cells (fill the numbers from the data; if a cell disagrees, say so). Keep "not confirmed" for H1b as the recorded verdict.
4. Gain predicted from two rates (steps ZN, XN, S2, YF/ZD for asmread): for each slow kernel k (old read, read_nop96, read_nop128) and each CPU and session: C_k (32 KiB cell median), the asmread 8 MiB cell 5th and 95th percentile (the two levels), the predicted gain range at 8 MiB = level / C_k - 1, and the measured gain = asmread 8 MiB cell median / kernel 8 MiB cell median - 1 ; inside the predicted range or not. Add the table to section 4 of the report.
Run both generators and all four test files. Final message: what was added where, pass counts, and the numbers of items 1 to 4 in short tables.`

const report = await agent(BUILD, { label: 'build:polish', phase: 'Build' })
const review = await agent(`${COMMON}
YOU ARE THE REVIEWER of four additions that another agent made for this task:
---
${BUILD}
---
Its report:
---
${report}
---
Re-run A/final8.py and A/report_final.py first (new folders may have arrived). Check: (1) no recorded verdict changed (diff the "claims" block of final8.txt against a run of the code with the additions disabled, or against the copy in the scratchpad if the builder left one; if none, check by reading the diff of final8.py); (2) each addition is labelled supplementary and computed correctly: recompute at least 3 numbers of each of the 4 items from the raw csv files with your own short script; (3) the wording in the report claims no more than the data (plain-english Check mode on the added prose; verdict words exact); (4) the page still renders well at 1200 px and 390 px (headless Chrome, look at the changed figures). Fix defects in place, re-run all four test files. Final message: defects found and fixed, recomputed numbers, pass counts, remaining weaknesses.`, { label: 'review:polish', phase: 'Review' })
return { report, review }
