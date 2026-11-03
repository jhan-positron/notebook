// stream.S - a linear stream of 64 B lines through the CME, in streaming SVE mode.
//
// uint64_t cmp_stream_hw(const void *p, uint64_t kib, uint64_t pf)
// uint64_t cmp_stream_pf(const void *p, uint64_t kib, uint64_t pf)
// void cmp_copy_sm(void *dst, const void *src, uint64_t n256): below
//   p: the start of the lap, 1 KiB aligned. kib: the lap in KiB (>= 1). pf: bytes ahead of p.
//   Returns the XOR of every 64-bit word of the lap.
//
// One loop pass reads 1 KiB: four LD1B of four vectors each (4 x 256 B at SVL 64 B), each into
// its own registers so all four are in flight, and 16 EORs fold them into z16-z19. cmp_stream_pf
// first issues RPRFM PSTKEEP of 1 KiB at p + pf (the GDN kernel's form: Xm = 1024, gdn_common.h);
// cmp_stream_hw has a NOP in its place, so the two loops differ only in that instruction and the
// hardware prefetcher alone feeds cmp_stream_hw. SMSTART SM zeroes the Z registers, so d8-d15
// (callee-saved) are kept on the stack around it.

	.text
	.arch	armv9-a+sme2

.macro	STREAM name, pfinsn
	.global	\name
	.type	\name, %function
	.p2align 6
\name:
	stp	d8, d9, [sp, #-64]!
	stp	d10, d11, [sp, #16]
	stp	d12, d13, [sp, #32]
	stp	d14, d15, [sp, #48]
	smstart	sm
	ptrue	pn8.b
	ptrue	p0.d
	mov	z16.d, #0
	mov	z17.d, #0
	mov	z18.d, #0
	mov	z19.d, #0
	mov	x3, #1024
	add	x4, x0, x2
	.p2align 6
1:	\pfinsn
	ld1b	{z0.b-z3.b}, pn8/z, [x0]
	ld1b	{z4.b-z7.b}, pn8/z, [x0, #4, mul vl]
	ld1b	{z20.b-z23.b}, pn8/z, [x0, #8, mul vl]
	ld1b	{z24.b-z27.b}, pn8/z, [x0, #12, mul vl]
	eor	z16.d, z16.d, z0.d
	eor	z17.d, z17.d, z1.d
	eor	z18.d, z18.d, z2.d
	eor	z19.d, z19.d, z3.d
	eor	z16.d, z16.d, z4.d
	eor	z17.d, z17.d, z5.d
	eor	z18.d, z18.d, z6.d
	eor	z19.d, z19.d, z7.d
	eor	z16.d, z16.d, z20.d
	eor	z17.d, z17.d, z21.d
	eor	z18.d, z18.d, z22.d
	eor	z19.d, z19.d, z23.d
	eor	z16.d, z16.d, z24.d
	eor	z17.d, z17.d, z25.d
	eor	z18.d, z18.d, z26.d
	eor	z19.d, z19.d, z27.d
	add	x0, x0, #1024
	add	x4, x4, #1024
	subs	x1, x1, #1
	b.ne	1b
	eor	z16.d, z16.d, z17.d
	eor	z18.d, z18.d, z19.d
	eor	z16.d, z16.d, z18.d
	eorv	d0, p0, z16.d
	ptrue	p1.d, vl1
	lastb	x0, p1, z0.d
	smstop	sm
	ldp	d14, d15, [sp, #48]
	ldp	d12, d13, [sp, #32]
	ldp	d10, d11, [sp, #16]
	ldp	d8, d9, [sp], #64
	ret
	.size	\name, . - \name
.endm

	STREAM	cmp_stream_hw, nop
	STREAM	cmp_stream_pf, "rprfm pstkeep, x3, [x4]"

// void cmp_copy_sm(void *dst, const void *src, uint64_t n256)
//   Copies n256 x 256 B (n256 >= 1) in streaming mode: LD1B and ST1B of four vectors, so every store
//   reaches memory as whole 64 B vectors through the CME, the path of the GDN kernel's own state
//   stores. The bench fills SPM with it: a CPU store to SPM on Normal-NC may be split into 8 B beats.
	.global	cmp_copy_sm
	.type	cmp_copy_sm, %function
	.p2align 6
cmp_copy_sm:
	stp	d8, d9, [sp, #-64]!
	stp	d10, d11, [sp, #16]
	stp	d12, d13, [sp, #32]
	stp	d14, d15, [sp, #48]
	smstart	sm
	ptrue	pn8.b
1:	ld1b	{z0.b-z3.b}, pn8/z, [x1]
	st1b	{z0.b-z3.b}, pn8, [x0]
	add	x0, x0, #256
	add	x1, x1, #256
	subs	x2, x2, #1
	b.ne	1b
	smstop	sm
	dsb	sy
	ldp	d14, d15, [sp, #48]
	ldp	d12, d13, [sp, #32]
	ldp	d10, d11, [sp, #16]
	ldp	d8, d9, [sp], #64
	ret
	.size	cmp_copy_sm, . - cmp_copy_sm

	.section .note.GNU-stack, "", %progbits
