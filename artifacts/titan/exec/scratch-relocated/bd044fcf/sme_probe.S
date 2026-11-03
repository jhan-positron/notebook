	.arch	armv9.3-a+sve2+sme2
	.text
	.globl	probe
probe:
	smstart
	rdsvl	x1, #1
	ptrue	pn8.b
	ld1b	{z0.b - z3.b}, pn8/z, [x0]
	ld1b	{z4.b - z7.b}, pn8/z, [x0, #4, mul vl]
	st1b	{z0.b - z3.b}, pn8, [x0]
	ptrue	p0.d
	ld1d	{z8.d}, p0/z, [x0]
	ptrue	p1.d, vl1
	lastb	x2, p1, z8.d
	ldr	d1, [x0]
	fmov	x3, d1
	prfm	pldl1keep, [x0, #256]
	dsb	sy
	smstop
	ret
