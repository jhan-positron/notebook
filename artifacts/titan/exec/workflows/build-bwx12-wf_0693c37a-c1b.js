export const meta = {
  name: 'build-bwx12',
  description: 'Add window-depth test kernels to the benchmark runner (bwx12), review them, build and self-test on CRB',
  phases: [{ title: 'Implement' }, { title: 'Review' }, { title: 'Fix and build' }],
}
const S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch'
const CTX = `Context: benchmark runner bwx11 (${S}/bwx11-2026-11-15/bwx11.c, 2703 lines, with build11.sh, bwx11_selftest.c, check_listing11.py; built on the Arm server CRB with gcc 14.2.0, AArch64, Neoverse V3AE). Finding of today: at 120 threads x 256 MiB (64 threads on CPUs 0-63 + 56 on CPUs 64-119), the load-only read loop asmread totals ~300 GB/s, but the same loop with 96 or 128 nop instructions per 256 B (read_nop96, read_nop128) totals 470-476 GB/s, equal to the old read loop with vector adds (oldread, 469 GB/s); read_nop64 gives 330, read_nop32 300. Hypothesis: the depth of the out-of-order window in cache lines (how many lines ahead the core issues loads) decides the total. We need new kernels to test this. New work folder: ${S}/bwx12-2026-11-15/ (create it as a copy of the needed bwx11 files, renamed bwx12.c, build12.sh, bwx12_selftest.c, check_listing12.py; do NOT modify the bwx11 folder).`
const SPEC = `Kernels to ADD in bwx12 (keep every bwx11 kernel unchanged, same machine code and loop placement rules; follow the existing macros/conventions such as DEF_ASMREAD, PLACE, PAD_*, K(name, T_READ/T_WRITE/T_COPY), the --list output, the selftest, the listing check). If MAX seq entries (64) or kernel-table limits need raising, raise them.
 1. read_nop48, read_nop56, read_nop72, read_nop80, read_nop88, read_nop112, read_nop160, read_nop192, read_nop256: asmread + that many nop per 256 B (same macro as read_nop64).
 2. read_dadd2, read_dadd4, read_dadd8, read_dadd16: the asmread loop (8 ldp q0..q15 per 256 B) followed by k NEON adds per iteration, each of the form add vA.2d, vA.2d, vL.2d where vL is a register just loaded in this iteration and vA is an accumulator in v16-v23 (so every add must wait for load data). k=16: all 16 loaded registers are consumed, two per accumulator (this equals the add density of oldread: 8 adds per 128 B). k=8: v0,v2,...,v14. k=4: v0,v4,v8,v12. k=2: v0,v8. Accumulators must be initialised (movi) before the loop. v16-v31 are caller-saved in AAPCS64, v8-v15 low halves are callee-saved (see how asmread handles d8-d15 and do the same).
 3. read_iadd16: the asmread loop followed by 16 NEON adds per iteration that do NOT depend on any load: add vA.2d, vA.2d, vB.2d with vA in v16-v23 and vB in v24-v31 (constants set before the loop). Same instruction count as read_dadd16. It is the control: same execution resources, no waiting on load data.
 4. read_sp24, read_sp32, read_sp40, read_sp48, read_sp56: like read_sparse (128 B per iteration: 4 ldp + N nop + add/cmp/branch) with N = 24, 32, 40, 48, 56.
 5. read_1pl_nop96: read_1pl (one 16 B load per 64 B line, 4 loads per 256 B) plus 96 nop per 256 B iteration.
 6. write_nop32, write_nop96, write_nop128, write_nop256: the asmwrite loop (8 stp q0,q0 per 256 B) plus that many nop per iteration.
 7. copy_nop96, copy_nop192: the asmcopy loop (8 ldp + 8 stp per 256 B) plus that many nop per iteration (nops after the stores).
Loop-start alignment: use the same PAD mechanism so that the new read kernels start at the same offset mod 64 as asmread where the mechanism allows; record the real offsets in offsets.tsv as build11.sh does. The selftest must cover every new kernel (reads: touches every byte range it should and returns; write/copy: memory contents correct). The byte count semantics (n in uint64 words, multiple of 256 B) must match the existing kernels exactly.`
phase('Implement')
const impl = await agent(`${CTX}

Task: implement bwx12 in ${S}/bwx12-2026-11-15/ on this dev machine (x86-64; there is NO AArch64 compiler here, so follow the way bwx11 handles this: read the header comment of bwx11.c and build11.sh and check_listing11.py to see how non-AArch64 stand-ins, the selftest and the listing check work; compile the stand-in build locally with gcc and run the selftest locally if bwx11 supports that).

${SPEC}

Do not log in to CRB in this step. Report: the list of files, what was added (line ranges), the exact asm text of one kernel of each family, any deviation from the spec and why, and how you tested locally.`, { label: 'implement-bwx12', phase: 'Implement' })
phase('Review')
const lenses = [
  ['asm', 'AArch64 assembly correctness of every NEW kernel in bwx12.c: instruction syntax accepted by GNU as, register use and clobber lists (v8-v15 callee-saved low 64 bits, v16-v31 caller-saved), loop bounds (exactly n words, no over-read past the buffer, no skipped bytes), bytes per iteration, that read_dadd* adds really depend on registers loaded in the same iteration and read_iadd16 adds depend on no load, that nop counts are exact, that gcc cannot reorder or drop anything, and that existing kernels are byte-for-byte unchanged in source (diff against the bwx11.c text).'],
  ['harness', 'the kernel table, --list, --seq parsing limits, T_READ/T_WRITE/T_COPY types, PAD/PLACE alignment macros for the new kernels, selftest coverage of every new kernel, build12.sh and check_listing12.py (do they reference bwx12 everywhere, will the listing check accept the new kernels, are sha256/offset records produced, marker-file check and taskset -c 0-119 kept), and anything that would make the CRB build or selftest fail.'],
]
const reviews = await parallel(lenses.map(([k, what]) => () => agent(`${CTX}

An implementer has just written bwx12 in ${S}/bwx12-2026-11-15/ to this spec:
${SPEC}

Implementer's report:
${impl}

Task: review, read-only (do not edit files, do not ssh). Lens: ${what}
Report only concrete defects, each with file:line, what is wrong, and the fix. If you find none, say "no defects" and list what you checked.`, { label: `review-${k}`, phase: 'Review' })))
phase('Fix and build')
const built = await agent(`${CTX}

bwx12 was implemented in ${S}/bwx12-2026-11-15/ to this spec:
${SPEC}

Two reviewers reported:
--- asm review ---
${reviews[0]}
--- harness review ---
${reviews[1]}

Task:
1. Judge each reported defect (verify it against the code), fix the real ones, and re-run the local tests.
2. Build on CRB. Host rules (mandatory): CRB login is ssh -o BatchMode=yes -o ConnectTimeout=15 jhan@192.168.2.45 . Every ssh command line must begin with the marker check: if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi  -- if the marker exists, stop and report. No scp: send files with tar through ssh (tar cf - -C <dir> <files> | ssh ... "<marker check>; mkdir -p ~/cache-perf/bwx12-20261115 && tar xf - -C ~/cache-perf/bwx12-20261115"). Write only under ~/cache-perf. Never sudo. Use CPUs 0-119 only (taskset -c 0-119). Before building, check that no measurement is running: pgrep -x 'bwx11|bwx12' must print nothing; if one runs, wait 60 s and check again (up to 20 min). Read how the bwx11 build was done (build11.sh and ${S}/bwx11-2026-11-15/crb-build-1/) and do the same for bwx12: build, selftest, objdump listing, offsets.tsv, listing check; copy the build records back to ${S}/bwx12-2026-11-15/crb-build-1/.
3. Smoke test on CRB (one thread, CPU 2, 32 KiB and 8 MiB, --min-ms 300, one process, --seq with ALL new kernels plus asmread, asmwrite, asmcopy, oldread): confirm each runs and print the rates.
4. Report: sha256 of the bwx12 binary on CRB and its path; the pass/fail of selftest and listing check; for each NEW kernel the instructions per iteration read from the objdump listing and the loop start offset mod 64; the smoke-test rates table; which review findings were real and what you changed; anything not done.`, { label: 'fix-build-bwx12', phase: 'Fix and build' })
return { impl, reviews, built }
