export const meta = {
  name: 'verify-cread-answer',
  description: 'Three skeptics try to refute the claims about a load-only C read loop and about why k_read has its loops',
  phases: [{ title: 'Refute' }],
}
const DIR = '/home/jhan/workspace/titan/cache-perf'
const COMMON = `Context (read-only task; do NOT ssh to any machine, do NOT edit any file, do NOT compile on remote hosts):
- ${DIR}/bench/bandwidth.c holds k_read (lines 138-148, C read loop with 16 running sums) and k_asmread (lines 173-195, hand-written aarch64 loop: 8 "ldp q" = 16 loads of 16 B, add, cmp, b.lo).
- ${DIR}/crb/results/probe-20261111T210017Z.txt holds the objdump of k_read, k_asmread etc. built by gcc 14.2 on the aarch64 server "CRB" with flags from ${DIR}/bench/Makefile.
- ${DIR}/crb/tmp/agent-scratch/cread-2026-11-12/cread.c holds four new candidate C functions (k_cread, k_cread_loop, k_cread_plain, k_cread_volatile). ${DIR}/crb/tmp/agent-scratch/cread-2026-11-12/probe-cread.txt holds their objdump from CRB (same gcc, same flags, compile only, no run).
- ${DIR}/bench/README.md describes the kernels.
Your job: try to REFUTE the claims below. Check each against the files. Report only what the files or a citable external source (GCC manual, Arm ACLE, AAPCS64) support. For each claim return verdict "holds", "wrong" or "unsupported", with the evidence (file and line, or source). Also list any important caveat that the claims omit. Be concrete and brief.`
const SCHEMA = { type: 'object', properties: { claims: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, verdict: { type: 'string', enum: ['holds', 'wrong', 'unsupported'] }, evidence: { type: 'string' } }, required: ['claim', 'verdict', 'evidence'] } }, omitted_caveats: { type: 'array', items: { type: 'string' } } }, required: ['claims', 'omitted_caveats'] }
const LENSES = [
  { key: 'machine-code', text: `Claims:
1. The loop of k_cread in probe-cread.txt has the same instructions per pass as the loop of k_asmread: 8 ldp q with offsets 0..224, one add of 256 to the pointer, one cmp, one conditional branch back. 11 instructions, 256 B per pass.
2. Differences between k_cread and k_asmread are only: (a) registers q16-q31 instead of q0-q15, (b) cmp operands swapped with b.hi instead of b.lo, which is the same condition, (c) k_asmread saves and restores d8-d15 outside the loop (check the k_asmread listing in probe-20261111T210017Z.txt) and k_cread does not, (d) one extra instruction before the loop that computes end = a + n.
3. k_cread_loop (two nested C loops, one empty asm statement per load) also compiles to 8 ldp q per pass, but its loop has 12 instructions: it keeps a separate index counter (add x2,x2,#0x20) next to the pointer add.
4. k_cread_plain (no asm statement) has no load instruction at all in its loop.
5. k_cread_volatile (volatile pointer, ISO C only) compiles to 16 loads of 8 B (ldr/ldur x) per 128 B, with no 16 B load.
6. The loop of k_read (probe-20261111T210017Z.txt) has 4 ldp q and 8 vector adds per 128 B; the inner j loop and the 16-element array s[] do not exist as a loop or as memory traffic inside the hot loop.
Also check loop alignment: is the loop head of each function aligned differently (address mod 16/64) in a way worth a caveat? Note cread.o is an unlinked object.` },
  { key: 'c-semantics', text: `Claims:
1. In C, a load whose value is never used is dead code, and gcc -O3 deletes it. So a C loop that "only loads" needs something that uses each loaded value.
2. The statement __asm__ volatile("" : : "w"(v)) on aarch64 gcc emits no instruction but forces the value v to be present in a SIMD/FP register at that point ("w" is the aarch64 constraint for FP/SIMD registers), so gcc must emit the load. This is a GNU extension, not ISO C; it is the same idiom as "DoNotOptimize" in Google Benchmark.
3. With ONE asm statement that names 16 values as inputs, all 16 values must be in 16 different registers at the same time.
4. vld1q_u64 from arm_neon.h loads 16 B (two uint64_t) with no alignment requirement beyond that of uint64_t.
5. gcc is free to emit "ldr q" x16 instead of "ldp q" x8 for this source in another compiler version; the source does not guarantee ldp. (gcc 14 has an ldp/stp fusion pass.)
6. k_cread as written (do { ... } while (p < end)) requires n > 0 and n a multiple of 32 words (256 B), the same precondition as k_asmread.
7. The read through a 'const volatile uint64_t *' lvalue forces one 8 B access per element and stops gcc from merging them into 16 B vector loads.
Check each against the GCC manual / ACLE / the source files. You may compile small tests locally (the local machine is x86-64 with gcc 11; an x86 analogue with "x" constraint and SSE is acceptable evidence for claims 1-3, say so) inside a new directory under ${DIR}/crb/tmp/agent-scratch/cread-2026-11-12/ only.` },
  { key: 'purpose', text: `Claims about why k_read is written as it is:
1. k_read has three loops in the source: outer i loop (steps 16 words = 128 B), inner j loop (16 fixed trips), and a final j loop that adds the 16 sums into one value.
2. The inner j loop is only a notation for "16 independent running sums". gcc unrolls and vectorizes it: the machine code has no inner loop, it has 4 ldp q and 8 vector adds into 8 vector registers (each holds 2 of the 16 sums).
3. The purpose of 16 separate sums instead of one is to avoid one serial chain of adds: with one sum each add must wait for the previous add. The source comment at bandwidth.c lines 135-137 states this purpose.
4. The final loop runs once per call, outside the hot loop; it produces the return value. The caller stores the return value to a volatile sink (see pass() in bandwidth.c). That use is what stops the compiler from deleting the loads.
5. k_read is portable C: it is also built on x86 (the comment mentions AVX-512; the Makefile builds bandwidth on any host), while the asm kernels are aarch64 only.
6. bench/README.md says the asm kernels were added because the compiled read loop issues 8 adds per 8 loads.
7. The report page ${DIR}/crb/crb-memory-hierarchy.html (section id "the-read-loop-compiled-from-c") says the C read loop measured 66.8 GB/s and the asm read loop 132.7 GB/s, and that the cause of the gap is not fully established (two hypotheses A and B, a 3:2 loads:adds test not run).
8. A load-only C loop like k_cread would NOT replace that missing 3:2 test; it would only test whether C source that compiles to the same instructions reaches the asm rate.
Check each against the files.` },
]
phase('Refute')
const out = await parallel(LENSES.map(l => () => agent(COMMON + '\n\n' + l.text, { label: 'refute:' + l.key, phase: 'Refute', schema: SCHEMA }).then(r => ({ lens: l.key, r }))))
return out.filter(Boolean)