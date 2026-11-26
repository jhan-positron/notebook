import sys,re
p='/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/results.md'
t=open(p).read()
i=t.index('## Short version'); j=t.index('## Words used here')
new_top='''## Short version

Neither of the two open questions about a memory benchmark on one Arm test server is resolved: the measurements of one night establish the cause of neither. The second question is reproduced: with 120 threads, the read loop from before the rewrite of 2026-11-13 moved 158.06 to 178.72 GB/s more in total than the rewritten read loop (33.8 to 37.9 % of its own total), under all 8 ways of timing that we tried. For the first question (one thread, 8 MiB buffer) the planned comparisons could not be made, and the user has nine decisions to make (see "Open decisions for the user").

- The numbers of the second sentence are the median of each timing setting, per session [Ref7][Ref21].
- Every run that needs no administrator rights completed. Complete runs are not a complete investigation of the causes.
- The terms of the next section are defined under "Words used here".

## Are the two questions resolved?

**No. The submitted evidence establishes the cause of neither question.** The blocks below keep three things apart: what is measured, what is not established, and which evidence is missing.

**Q1. The small gain of new read over old read at 8 MiB with one thread: not resolved.**

- Measured:
  - The asm read loop ran at two levels with full huge-page coverage. The process medians are 67.29 to 71.73 GB/s in s1 and 67.26 to 71.56 GB/s in s2 (step B4) [Ref8].
  - In step B6 no CPU had a stable high process in either session. So old read was never compared between the two levels [Ref7].
  - Old read at 8 MiB was slower than old read at 1 MiB by a resolved amount. The difference is a position effect: it appears in the 0.3 s interval after an asm read interval, and not after an interval of old read at 1 MiB [Ref7][Ref21].
- Not established:
  - What sets the rate of old read at 8 MiB.
  - What sets the rate of new read at 8 MiB, and why it changes between the two levels. H2 and H3b are "not tested".
  - So the two nearby rates of the run of 2026-11-13 describe the size of the gap. They do not explain it.
- Missing evidence:
  - A controlled comparison of old read between the low and the high level at 8 MiB on one CPU. Step B6 was built for it, and the high level did not occur there.
  - Counters at the high level in the long read-only sequence of step C1. No interval of C1 was high.
  - A test of what changes the level (H2, and H3b through step D2).

**Q1b, a separate question. New C copy against asm copy at 8 MiB: not decided.**

- Measured: new C copy is slower than asm copy in 16 of 16 processes in s1 and in 15 of 16 in s2 (description without labels) [Ref8][Ref21].
- Not established: a resolved difference by the rule of the handoff (the word is "not observed"), and the cause of the difference.
- This result does not answer Q1. It compares two copy loops, not old read with new read.

**Q2. Old read is faster than new read with 120 threads: reproduced, and not resolved.**

- Measured:
  - D is resolved (+) in 16 of 16 settings (8 settings in each of 2 sessions, 4 processes each) [Ref7].
  - With the common stop, 6 s intervals and the common start, the median D is 167.50 GB/s in s1 and 177.66 GB/s in s2. So the difference stays when the whole-pass stop and the short interval are removed [Ref7][Ref21].
  - Old read minus `read_sparse` is +156.64 GB/s in s1 and +166.21 GB/s in s2 (step B5) [Ref7].
- Not established:
  - The mechanism inside the chip. H8 is "not resolved", and H10 is "not tested".
  - The B5 result does not identify the cause. A `nop` does not use the same resources as a vector add [Ref1].
- Missing evidence: a measurement that separates the candidate mechanisms. Step D1 (mesh counters, with root) would test H10 only. It is no guarantee of an explanation.

**Q2b, the write totals: not resolved.** The plan sets no rule for when two totals are separate levels, and H11 is "not resolved" (see "Answers to the expected results").

'''
t=t[:i]+new_top+t[j:]
R=[
('- Parts A, B and C are complete. Part D was not run [Ref2].','- The runs of Parts A, B and C are complete. Part D was not run [Ref2]. The causes of the two questions are not established (see "Are the two questions resolved?").'),
('- What would give it: a B6 session in which one CPU has at least 2 stable low and 2 stable high processes, or new level limits.',
 '- What would give it: a new B6 session in which one CPU has at least 2 stable low and 2 stable high processes. In the two sessions that ran, the high level did not occur in B6.\n- New level limits change the labels of the existing intervals. They cannot add an observation of old read at a level that did not occur.'),
('- What would decide 8 MiB: the user\'s decision on the level limits. The analysis is then rerun on the same files. No new measurement is needed.',
 '- The user\'s decision on the level limits can change the formal word for 8 MiB. That needs a rerun of the analysis on the same files, and no new measurement.\n- The word can also stay undecided after that decision. The rule without labels gives "not resolved" for B1 at 8 MiB in both sessions (see H4).\n- No word of B1 gives the cause of the copy difference.'),
('- The cause inside the chip stays a hypothesis. Part D was not run.','- The cause inside the chip is not established. Part D was not run. Step D1 would test H10 only.'),
('- Only item 7 needs a new run.\n',
 '- Items 1 to 6, 8 and 9 are choices of analysis or of reporting. They need no new run. They can change a result word, and they cannot add an observation that the runs do not hold.\n- So no item, and no combination of items, is a promise that Q1 or Q2 will be resolved. The missing measurements are listed after item 9.\n'),
('   - Options a and b can change the words of H4, H5, H6 and of part 1 of H1. The analysis is then rerun on the same files.',
 '   - Options a and b can change the words of H4, H5, H6 and of part 1 of H1. The analysis is then rerun on the same files.\n   - Q1 can stay unresolved under every option. Part 1 of H1 needs old read at both levels, and B6 has no interval sequence at the high level under the present limits.'),
('Without them H3b and H10 stay "not tested". This is the only item that needs a new run.','Without them H3b and H10 stay "not tested". This is the only item of the list that is a new run. Part D tests these two hypotheses. It is no guarantee that either question will be resolved.'),
]
for a,b in R:
    if t.count(a)!=1: print('COUNT',t.count(a),a[:60]); sys.exit(1)
    t=t.replace(a,b)
k=t.index('## Files')
t=t[:k]+'''**Measurements that are missing.** No item above supplies them. They are not planned, and this file does not ask for them.

- A controlled comparison of old read at 8 MiB between the low and the high level on one CPU (Q1a).
- Counters at the high level in the long read-only sequence of step C1 (Q1c).
- A test of what changes the level: H2, and H3b through step D2 (Q1c).
- A measurement that separates the candidate mechanisms of Q2a inside the chip. Step D1 would test H10 only.

'''+t[k:]
open(p,'w').write(t)
