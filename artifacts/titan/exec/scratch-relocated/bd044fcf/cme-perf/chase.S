// chase.S - dependent 64 B loads through the CME, in streaming SVE mode.
//
// uint64_t cmp_chase(uint64_t p, uint64_t hops)
//   p: the address of a ring line. The first 8 B of each line hold the address of the next line.
//   Returns the address reached after `hops` loads (hops >= 1).
//
// Each hop is LD1D of the line (a streaming load, so it goes through the CME and its L1), then
// LASTB moves the first element to a general register for the next address. The predicate is
// VL1, so only the first 8 B are read from the vector. SMSTART SM zeroes the Z registers, so
// d8-d15 (callee-saved) are kept on the stack around it.

	.text
	.arch	armv9-a+sme
	.global	cmp_chase
	.type	cmp_chase, %function
	.p2align 6
cmp_chase:
	stp	d8, d9, [sp, #-64]!
	stp	d10, d11, [sp, #16]
	stp	d12, d13, [sp, #32]
	stp	d14, d15, [sp, #48]
	smstart	sm
	ptrue	p0.d, vl1
	.p2align 6
1:	ld1d	{z0.d}, p0/z, [x0]
	lastb	x0, p0, z0.d
	subs	x1, x1, #1
	b.ne	1b
	smstop	sm
	ldp	d14, d15, [sp, #48]
	ldp	d12, d13, [sp, #32]
	ldp	d10, d11, [sp, #16]
	ldp	d8, d9, [sp], #64
	ret
	.size	cmp_chase, . - cmp_chase

	.section .note.GNU-stack, "", %progbits
