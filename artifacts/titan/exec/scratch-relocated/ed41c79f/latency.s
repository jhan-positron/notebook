	.file	"latency.c"
	.text
	.p2align 4
	.type	chase, @function
chase:
.LFB66:
	.cfi_startproc
	movq	%rdi, %rax
	testq	%rsi, %rsi
	je	.L2
	xorl	%edx, %edx
	.p2align 4
	.p2align 3
.L3:
	movq	(%rax), %rax
	addq	$8, %rdx
	movq	(%rax), %rax
	movq	(%rax), %rax
	movq	(%rax), %rax
	movq	(%rax), %rax
	movq	(%rax), %rax
	movq	(%rax), %rax
	movq	(%rax), %rax
	cmpq	%rdx, %rsi
	ja	.L3
.L2:
	ret
	.cfi_endproc
.LFE66:
	.size	chase, .-chase
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC5:
	.string	"bad size: %s\n"
	.text
	.p2align 4
	.type	parse_bytes, @function
parse_bytes:
.LFB61:
	.cfi_startproc
	pushq	%r12
	.cfi_def_cfa_offset 16
	.cfi_offset 12, -16
	movq	%rdi, %r12
	subq	$16, %rsp
	.cfi_def_cfa_offset 32
	movq	%rsp, %rsi
	movq	%fs:40, %rax
	movq	%rax, 8(%rsp)
	xorl	%eax, %eax
	call	strtod@PLT
	movq	(%rsp), %rax
	movzbl	(%rax), %edi
	leal	-71(%rdi), %edx
	cmpb	$38, %dl
	ja	.L17
	movl	$1, %esi
	movabsq	$4294967297, %rcx
	shlx	%rdx, %rsi, %rdx
	testq	%rcx, %rdx
	jne	.L11
	movabsq	$274877907008, %rcx
	testq	%rcx, %rdx
	jne	.L12
	movabsq	$68719476752, %rcx
	testq	%rcx, %rdx
	jne	.L23
.L13:
	movq	stderr(%rip), %rdi
	movq	%r12, %rcx
	leaq	.LC5(%rip), %rdx
	movl	$1, %esi
	xorl	%eax, %eax
	call	__fprintf_chk@PLT
	movl	$2, %edi
	call	exit@PLT
	.p2align 4
	.p2align 3
.L11:
	vmovsd	.LC3(%rip), %xmm1
	incq	%rax
	movq	%rax, (%rsp)
.L10:
	cmpq	%rax, %r12
	je	.L13
	cmpb	$0, (%rax)
	jne	.L13
	vxorpd	%xmm2, %xmm2, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L13
	movq	8(%rsp), %rdx
	subq	%fs:40, %rdx
	vmulsd	%xmm0, %xmm1, %xmm0
	vcvttsd2usi	%xmm0, %rax
	jne	.L24
	addq	$16, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 16
	popq	%r12
	.cfi_def_cfa_offset 8
	ret
	.p2align 4
	.p2align 3
.L23:
	.cfi_restore_state
	incq	%rax
	vmovsd	.LC1(%rip), %xmm1
	movq	%rax, (%rsp)
	jmp	.L10
	.p2align 4
	.p2align 3
.L12:
	incq	%rax
	vmovsd	.LC2(%rip), %xmm1
	movq	%rax, (%rsp)
	jmp	.L10
	.p2align 4
	.p2align 3
.L17:
	vmovsd	.LC0(%rip), %xmm1
	jmp	.L10
.L24:
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE61:
	.size	parse_bytes, .-parse_bytes
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC6:
	.string	"usage: latency [--cpu N] [--min S] [--max S] [--sizes a,b,c] [--min-ms MS] [--min-cycles C] [--reps R] [--no-thp]\n  sizes accept K/M/G suffixes; --min..--max doubles\n"
	.text
	.p2align 4
	.type	usage, @function
usage:
.LFB68:
	.cfi_startproc
	pushq	%rax
	.cfi_def_cfa_offset 16
	popq	%rax
	.cfi_def_cfa_offset 8
	leaq	.LC6(%rip), %rdi
	movl	$166, %edx
	movl	$1, %esi
	subq	$8, %rsp
	.cfi_def_cfa_offset 16
	movq	stderr(%rip), %rcx
	call	fwrite@PLT
	movl	$2, %edi
	call	exit@PLT
	.cfi_endproc
.LFE68:
	.size	usage, .-usage
	.section	.rodata.str1.1
.LC8:
	.string	"madvise"
.LC9:
	.string	"nohugepage"
.LC11:
	.string	"--no-thp"
.LC12:
	.string	"--cpu"
.LC13:
	.string	"--min"
.LC14:
	.string	"--max"
.LC15:
	.string	"--min-ms"
.LC17:
	.string	"--min-cycles"
.LC18:
	.string	"--reps"
.LC19:
	.string	"--sizes"
.LC20:
	.string	","
.LC21:
	.string	"sched_setaffinity"
	.section	.rodata.str1.8
	.align 8
.LC22:
	.string	"# latency pointer chase: ns_per_load = elapsed_ns / loads; cpu=%d thp=%s min_ms=%.0f min_cycles=%d reps=%d\n"
	.align 8
.LC23:
	.string	"size_bytes,rep,loads,ns_per_load"
	.align 8
.LC24:
	.string	"size %lu is not a multiple of 512 bytes\n"
	.section	.rodata.str1.1
.LC25:
	.string	"mmap"
.LC26:
	.string	"madvise (continuing)"
.LC27:
	.string	"r"
.LC28:
	.string	"/proc/self/smaps_rollup"
.LC30:
	.string	"AnonHugePages: %ld kB"
	.section	.rodata.str1.8
	.align 8
.LC31:
	.string	"# size_bytes=%lu AnonHugePages_kB=%ld\n"
	.section	.rodata.str1.1
.LC34:
	.string	"%lu,%d,%lu,%.3f\n"
.LC35:
	.string	"%lu,best,%lu,%.3f\n"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB69:
	.cfi_startproc
	endbr64
	leaq	8(%rsp), %r10
	.cfi_def_cfa 10, 0
	andq	$-64, %rsp
	pushq	-8(%r10)
	pushq	%rbp
	movq	%rsp, %rbp
	.cfi_escape 0x10,0x6,0x2,0x76,0
	pushq	%r15
	pushq	%r14
	pushq	%r13
	pushq	%r12
	pushq	%r10
	.cfi_escape 0xf,0x3,0x76,0x58,0x6
	.cfi_escape 0x10,0xf,0x2,0x76,0x78
	.cfi_escape 0x10,0xe,0x2,0x76,0x70
	.cfi_escape 0x10,0xd,0x2,0x76,0x68
	.cfi_escape 0x10,0xc,0x2,0x76,0x60
	pushq	%rbx
	subq	$1024, %rsp
	.cfi_escape 0x10,0x3,0x2,0x76,0x50
	movl	%edi, -984(%rbp)
	movq	%rsi, -1000(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -56(%rbp)
	xorl	%eax, %eax
	cmpl	$1, %edi
	jle	.L28
	vmovsd	.LC7(%rip), %xmm3
	xorl	%r14d, %r14d
	movl	$1, %ebx
	movq	$0, -1024(%rbp)
	movl	$1, -1032(%rbp)
	movl	$2, -1060(%rbp)
	movl	$3, -1028(%rbp)
	movl	$-1, -1008(%rbp)
	movq	%r14, -1016(%rbp)
	vmovsd	%xmm3, -992(%rbp)
	jmp	.L41
	.p2align 4
	.p2align 3
.L152:
	leaq	.LC12(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	cmpl	-984(%rbp), %r15d
	setl	%r15b
	testl	%eax, %eax
	jne	.L30
	testb	%r15b, %r15b
	jne	.L146
.L30:
	leaq	.LC13(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L31
	testb	%r15b, %r15b
	jne	.L147
.L31:
	leaq	.LC14(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L32
	testb	%r15b, %r15b
	jne	.L148
.L32:
	leaq	.LC15(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L33
	testb	%r15b, %r15b
	jne	.L149
.L33:
	leaq	.LC17(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L34
	testb	%r15b, %r15b
	jne	.L150
.L34:
	leaq	.LC18(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L35
	testb	%r15b, %r15b
	je	.L35
	movq	-1000(%rbp), %rax
	movl	$10, %edx
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	strtol@PLT
	movl	%eax, -1028(%rbp)
	.p2align 4
	.p2align 3
.L29:
	cmpl	%ebx, -984(%rbp)
	jle	.L151
.L41:
	movq	-1000(%rbp), %rax
	movslq	%ebx, %r12
	leaq	.LC11(%rip), %rsi
	leal	1(%rbx), %r15d
	salq	$3, %r12
	movq	(%rax,%r12), %r13
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L152
	movl	%r15d, %ebx
	movl	$0, -1032(%rbp)
	cmpl	%ebx, -984(%rbp)
	jg	.L41
.L151:
	movq	-1024(%rbp), %rsi
	movl	%r14d, -1064(%rbp)
	movq	-1016(%rbp), %r14
	testq	%rsi, %rsi
	leaq	-1(%r14), %rax
	cmove	%r14, %rsi
	cmpq	%rax, %rsi
	jbe	.L43
	movl	-1064(%rbp), %ebx
	movslq	%ebx, %rcx
	cmpl	$64, %ecx
	je	.L28
	movl	$63, %edx
	leal	1(%rcx), %eax
	leaq	-832(%rbp), %rdi
	subl	%ebx, %edx
	cltq
	leaq	2(%rcx,%rdx), %rcx
	jmp	.L44
	.p2align 4
	.p2align 3
.L45:
	incq	%rax
	cmpq	%rcx, %rax
	je	.L28
.L44:
	movq	%r14, -8(%rdi,%rax,8)
	addq	%r14, %r14
	leaq	-1(%r14), %rdx
	cmpq	%rdx, %rsi
	ja	.L45
	movl	%eax, -1064(%rbp)
.L43:
	movl	-1064(%rbp), %ecx
	movl	-1028(%rbp), %esi
	testl	%ecx, %ecx
	sete	%al
	testl	%esi, %esi
	setle	%dl
	orb	%dl, %al
	jne	.L28
	movl	-1060(%rbp), %edx
	testl	%edx, %edx
	jle	.L28
	movl	-1008(%rbp), %ebx
	testl	%ebx, %ebx
	jns	.L153
.L46:
	vmovsd	-992(%rbp), %xmm3
	movl	-1032(%rbp), %eax
	leaq	.LC8(%rip), %rcx
	leaq	.LC22(%rip), %rsi
	vmulsd	.LC16(%rip), %xmm3, %xmm0
	movl	-1028(%rbp), %r9d
	movl	$1, %edi
	movl	-1060(%rbp), %r8d
	movl	-1008(%rbp), %edx
	testl	%eax, %eax
	leaq	.LC9(%rip), %rax
	cmove	%rax, %rcx
	movl	$1, %eax
	call	__printf_chk@PLT
	leaq	.LC23(%rip), %rdi
	call	puts@PLT
	leaq	-832(%rbp), %rax
	movq	$0, -1040(%rbp)
	movq	%rax, -1072(%rbp)
.L72:
	movq	-1072(%rbp), %rax
	movq	-1040(%rbp), %rcx
	movq	(%rax,%rcx,8), %rax
	movq	%rax, -1024(%rbp)
	testl	$511, %eax
	jne	.L154
	leaq	2097151(%rax), %r13
	movq	%rax, %rbx
	xorl	%r9d, %r9d
	movl	$-1, %r8d
	andq	$-2097152, %r13
	movl	$34, %ecx
	movl	$3, %edx
	xorl	%edi, %edi
	leaq	2097152(%r13), %rax
	shrq	$6, %rbx
	movq	%rax, %rsi
	movq	%rax, -1056(%rbp)
	call	mmap@PLT
	movq	%rax, -1048(%rbp)
	cmpq	$-1, %rax
	je	.L155
	movl	$15, %edx
	subl	-1032(%rbp), %edx
	leaq	2097151(%rax), %r12
	movq	%r13, %rsi
	andq	$-2097152, %r12
	movq	%r12, %rdi
	movq	%r12, %r15
	call	madvise@PLT
	testl	%eax, %eax
	jne	.L156
.L52:
	movabsq	$-7046029254386353131, %rax
	leaq	-1(%rbx), %rsi
	movq	%r12, %rdx
	movq	%rax, rng_state(%rip)
	xorl	%eax, %eax
	testq	%rbx, %rbx
	je	.L55
	.p2align 4
	.p2align 3
.L53:
	movq	%rax, (%rdx)
	incq	%rax
	addq	$64, %rdx
	cmpq	%rax, %rbx
	jne	.L53
	testq	%rsi, %rsi
	je	.L56
.L55:
	movq	%rsi, %rdi
	movabsq	$-7046029254386353131, %rcx
	salq	$6, %rdi
	addq	%r12, %rdi
	movq	%rdi, %r8
	.p2align 4
	.p2align 3
.L54:
	movq	%rcx, %rdx
	movq	(%r8), %r9
	subq	$64, %r8
	salq	$13, %rdx
	xorq	%rcx, %rdx
	movq	%rdx, %rax
	shrq	$7, %rax
	xorq	%rdx, %rax
	xorl	%edx, %edx
	movq	%rax, %rcx
	salq	$17, %rcx
	xorq	%rax, %rcx
	movq	%rcx, %rax
	divq	%rsi
	salq	$6, %rdx
	addq	%r12, %rdx
	movq	(%rdx), %rax
	movq	%rax, 64(%r8)
	decq	%rsi
	movq	%r9, (%rdx)
	jne	.L54
	movq	%rcx, rng_state(%rip)
	movq	%rbx, %rcx
	salq	$6, %rcx
	subq	%rcx, %rdi
	movq	%rax, 128(%rdi)
	movq	%r9, (%rdx)
	testq	%rbx, %rbx
	je	.L63
	cmpq	$7, %rbx
	jbe	.L56
	movq	%rbx, %r10
	vpbroadcastq	%r12, %zmm3
	leaq	64(%r12), %r9
	leaq	128(%r12), %r8
	shrq	$3, %r10
	leaq	192(%r12), %rdi
	leaq	256(%r12), %rsi
	leaq	320(%r12), %rcx
	salq	$9, %r10
	leaq	384(%r12), %rdx
	leaq	448(%r12), %rax
	addq	%r12, %r10
	.p2align 4
	.p2align 3
.L57:
	vmovdqa64	(%r12), %zmm0
	vmovdqa64	(%r8), %zmm1
	addq	$512, %r12
	addq	$512, %r9
	vmovdqa64	.LC29(%rip), %zmm7
	vmovdqa64	(%rdx), %zmm2
	addq	$512, %r8
	addq	$512, %rdi
	addq	$512, %rsi
	addq	$512, %rcx
	addq	$512, %rdx
	addq	$512, %rax
	vpermt2q	-512(%rdi), %zmm7, %zmm1
	vpermt2q	-512(%r9), %zmm7, %zmm0
	vpermt2q	-512(%rax), %zmm7, %zmm2
	vpermt2q	%zmm1, %zmm7, %zmm0
	vmovdqa64	-512(%rsi), %zmm1
	vpermt2q	-512(%rcx), %zmm7, %zmm1
	vpermt2q	%zmm2, %zmm7, %zmm1
	vpermt2q	%zmm1, %zmm7, %zmm0
	vpsllq	$6, %zmm0, %zmm0
	vpaddq	%zmm3, %zmm0, %zmm0
	vmovq	%xmm0, -512(%r12)
	vextracti64x2	$0x1, %ymm0, %xmm1
	vpextrq	$1, %xmm0, -512(%r9)
	vextracti64x4	$0x1, %zmm0, %ymm0
	vmovq	%xmm1, -512(%r8)
	vpextrq	$1, %xmm1, -512(%rdi)
	vmovq	%xmm0, -512(%rsi)
	vpextrq	$1, %xmm0, -512(%rcx)
	vextracti64x2	$0x1, %ymm0, %xmm0
	vmovq	%xmm0, -512(%rdx)
	vpextrq	$1, %xmm0, -512(%rax)
	cmpq	%r10, %r12
	jne	.L57
	movq	%rbx, %rsi
	andq	$-8, %rsi
	cmpq	%rsi, %rbx
	je	.L143
	vzeroupper
.L56:
	movq	%rsi, %rdx
	movl	$6, %edi
	salq	$6, %rdx
	leaq	(%r15,%rdx), %rcx
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	leaq	1(%rsi), %rax
	cmpq	%rax, %rbx
	jbe	.L63
	leaq	64(%r15,%rdx), %rcx
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	leaq	2(%rsi), %rax
	cmpq	%rax, %rbx
	jbe	.L63
	leaq	128(%r15,%rdx), %rcx
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	leaq	3(%rsi), %rax
	cmpq	%rax, %rbx
	jbe	.L63
	leaq	192(%r15,%rdx), %rcx
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	leaq	4(%rsi), %rax
	cmpq	%rbx, %rax
	jnb	.L63
	leaq	256(%r15,%rdx), %rcx
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	leaq	5(%rsi), %rax
	cmpq	%rax, %rbx
	jbe	.L63
	leaq	320(%r15,%rdx), %rcx
	addq	$6, %rsi
	shlx	%rdi, (%rcx), %rax
	addq	%r15, %rax
	movq	%rax, (%rcx)
	cmpq	%rsi, %rbx
	jbe	.L63
	leaq	384(%r15,%rdx), %rdx
	shlx	%rdi, (%rdx), %rax
	addq	%r15, %rax
	movq	%rax, (%rdx)
.L63:
	leaq	.LC27(%rip), %rsi
	leaq	.LC28(%rip), %rdi
	call	fopen@PLT
	movq	%rax, %r14
	testq	%rax, %rax
	je	.L157
	movq	$-1, -976(%rbp)
	leaq	-976(%rbp), %r13
	leaq	-320(%rbp), %r12
	jmp	.L64
	.p2align 4
	.p2align 3
.L65:
	xorl	%eax, %eax
	movq	%r13, %rdx
	leaq	.LC30(%rip), %rsi
	movq	%r12, %rdi
	call	__isoc99_sscanf@PLT
	cmpl	$1, %eax
	je	.L66
.L64:
	movq	%r14, %rdx
	movl	$256, %esi
	movq	%r12, %rdi
	call	fgets@PLT
	testq	%rax, %rax
	jne	.L65
.L66:
	movq	%r14, %rdi
	call	fclose@PLT
	movq	-976(%rbp), %rcx
.L59:
	movq	-1024(%rbp), %r14
	leaq	.LC31(%rip), %rsi
	movl	$1, %edi
	xorl	%eax, %eax
	movq	%rbx, %r12
	movq	%r14, %rdx
	call	__printf_chk@PLT
	cmpq	$67108863, %r14
	ja	.L67
	movl	$1048576, %eax
	xorl	%edx, %edx
	divq	%rbx
	imulq	%rbx, %rax
	movq	%rax, %r12
.L67:
	movq	%r15, %rdi
	movq	%rbx, %rsi
	call	chase
	vmovsd	.LC10(%rip), %xmm3
	movq	$0, -1016(%rbp)
	movl	$0, -1000(%rbp)
	movq	%rax, %r15
	movslq	-1060(%rbp), %r14
	imulq	%rbx, %r14
	vmovsd	%xmm3, -1008(%rbp)
	.p2align 4
	.p2align 3
.L71:
	movq	%r13, %rsi
	movl	$1, %edi
	xorl	%ebx, %ebx
	call	clock_gettime@PLT
	vxorpd	%xmm7, %xmm7, %xmm7
	vcvtsi2sdq	-968(%rbp), %xmm7, %xmm0
	vmovsd	%xmm0, %xmm0, %xmm1
	vcvtsi2sdq	-976(%rbp), %xmm7, %xmm0
	vfmadd132sd	.LC32(%rip), %xmm0, %xmm1
	vmovsd	%xmm1, -984(%rbp)
	.p2align 4
	.p2align 3
.L122:
	movq	%r15, %rdi
	movq	%r12, %rsi
	addq	%r12, %rbx
	call	chase
	movq	%r13, %rsi
	movl	$1, %edi
	movq	%rax, %r15
	call	clock_gettime@PLT
	vxorpd	%xmm4, %xmm4, %xmm4
	vmovsd	-992(%rbp), %xmm6
	vcvtsi2sdq	-968(%rbp), %xmm4, %xmm0
	vcvtsi2sdq	-976(%rbp), %xmm4, %xmm1
	vfmadd132sd	.LC32(%rip), %xmm1, %xmm0
	vsubsd	-984(%rbp), %xmm0, %xmm0
	vcomisd	%xmm0, %xmm6
	ja	.L122
	cmpq	%r14, %rbx
	jb	.L122
	vmulsd	.LC33(%rip), %xmm0, %xmm0
	vcvtusi2sdq	%rbx, %xmm4, %xmm1
	movl	-1000(%rbp), %ecx
	movq	%rbx, %r8
	movq	-1024(%rbp), %rdx
	leaq	.LC34(%rip), %rsi
	movl	$1, %edi
	movl	$1, %eax
	vdivsd	%xmm1, %xmm0, %xmm1
	vmovsd	%xmm1, %xmm1, %xmm0
	vmovsd	%xmm1, -984(%rbp)
	call	__printf_chk@PLT
	vmovsd	-1008(%rbp), %xmm3
	vmovsd	-984(%rbp), %xmm1
	vcomisd	%xmm1, %xmm3
	cmovbe	-1016(%rbp), %rbx
	vminsd	%xmm3, %xmm1, %xmm2
	incl	-1000(%rbp)
	movl	-1000(%rbp), %eax
	vmovsd	%xmm2, -1008(%rbp)
	movq	%rbx, -1016(%rbp)
	cmpl	%eax, -1028(%rbp)
	jg	.L71
	movq	-1024(%rbp), %rdx
	vmovsd	%xmm2, %xmm2, %xmm0
	movq	%rbx, %rcx
	leaq	.LC35(%rip), %rsi
	movl	$1, %edi
	movl	$1, %eax
	movq	%r15, sink(%rip)
	call	__printf_chk@PLT
	movq	stdout(%rip), %rdi
	call	fflush@PLT
	movq	-1056(%rbp), %rsi
	movq	-1048(%rbp), %rdi
	call	munmap@PLT
	incq	-1040(%rbp)
	movq	-1040(%rbp), %rax
	cmpl	%eax, -1064(%rbp)
	jg	.L72
	movq	-56(%rbp), %rax
	subq	%fs:40, %rax
	jne	.L158
	addq	$1024, %rsp
	xorl	%eax, %eax
	popq	%rbx
	popq	%r10
	.cfi_remember_state
	.cfi_def_cfa 10, 0
	popq	%r12
	popq	%r13
	popq	%r14
	popq	%r15
	popq	%rbp
	leaq	-8(%r10), %rsp
	.cfi_def_cfa 7, 8
	ret
.L35:
	.cfi_restore_state
	leaq	.LC19(%rip), %rsi
	movq	%r13, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L28
	testb	%r15b, %r15b
	je	.L28
	movq	-1000(%rbp), %rax
	movq	8(%rax,%r12), %rdi
	leaq	.LC20(%rip), %r12
	movq	%r12, %rsi
	call	strtok@PLT
	movq	%rax, %rdi
	testq	%rax, %rax
	je	.L145
	cmpl	$64, %r14d
	je	.L28
	movslq	%r14d, %r15
	leaq	-832(%rbp), %r13
	jmp	.L39
	.p2align 4
	.p2align 3
.L40:
	incq	%r15
	cmpl	$64, %r15d
	je	.L28
.L39:
	call	parse_bytes
	xorl	%edi, %edi
	movq	%r12, %rsi
	leal	1(%r15), %r14d
	movq	%rax, 0(%r13,%r15,8)
	call	strtok@PLT
	movq	%rax, %rdi
	testq	%rax, %rax
	jne	.L40
.L145:
	addl	$2, %ebx
	jmp	.L29
.L146:
	movq	-1000(%rbp), %rax
	movl	$10, %edx
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	strtol@PLT
	movl	%eax, -1008(%rbp)
	jmp	.L29
.L147:
	movq	-1000(%rbp), %rax
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	parse_bytes
	movq	%rax, -1016(%rbp)
	jmp	.L29
.L148:
	movq	-1000(%rbp), %rax
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	parse_bytes
	movq	%rax, -1024(%rbp)
	jmp	.L29
.L149:
	movq	-1000(%rbp), %rax
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	strtod@PLT
	vdivsd	.LC16(%rip), %xmm0, %xmm3
	vmovsd	%xmm3, -992(%rbp)
	jmp	.L29
.L150:
	movq	-1000(%rbp), %rax
	movl	$10, %edx
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%r12), %rdi
	call	strtol@PLT
	movl	%eax, -1060(%rbp)
	jmp	.L29
.L156:
	leaq	.LC26(%rip), %rdi
	call	perror@PLT
	jmp	.L52
.L143:
	vzeroupper
	jmp	.L63
.L153:
	leaq	-960(%rbp), %rdx
	movl	$32, %ecx
	xorl	%eax, %eax
	movq	%rdx, %rdi
	rep stosl
	cmpl	$1023, %ebx
	jg	.L47
	movslq	%ebx, %rax
	movl	$1, %ecx
	shrq	$6, %rax
	shlx	%rbx, %rcx, %rcx
	orq	%rcx, (%rdx,%rax,8)
.L47:
	xorl	%edi, %edi
	movl	$128, %esi
	call	sched_setaffinity@PLT
	testl	%eax, %eax
	je	.L46
	leaq	.LC21(%rip), %rdi
	call	perror@PLT
	movl	$2, %edi
	call	exit@PLT
.L154:
	movq	stderr(%rip), %rdi
	movq	%rax, %rcx
	leaq	.LC24(%rip), %rdx
	movl	$1, %esi
	xorl	%eax, %eax
	call	__fprintf_chk@PLT
	movl	$2, %edi
	call	exit@PLT
.L28:
	call	usage
.L158:
	call	__stack_chk_fail@PLT
.L157:
	orq	$-1, %rcx
	leaq	-976(%rbp), %r13
	jmp	.L59
.L155:
	leaq	.LC25(%rip), %rdi
	call	perror@PLT
	movl	$2, %edi
	call	exit@PLT
	.cfi_endproc
.LFE69:
	.size	main, .-main
	.local	rng_state
	.comm	rng_state,8,8
	.local	sink
	.comm	sink,8,8
	.section	.rodata.cst8,"aM",@progbits,8
	.align 8
.LC0:
	.long	0
	.long	1072693248
	.align 8
.LC1:
	.long	0
	.long	1083179008
	.align 8
.LC2:
	.long	0
	.long	1093664768
	.align 8
.LC3:
	.long	0
	.long	1104150528
	.align 8
.LC7:
	.long	858993459
	.long	1070805811
	.align 8
.LC10:
	.long	966823146
	.long	1177108057
	.align 8
.LC16:
	.long	0
	.long	1083129856
	.section	.rodata
	.align 64
.LC29:
	.quad	0
	.quad	2
	.quad	4
	.quad	6
	.quad	8
	.quad	10
	.quad	12
	.quad	14
	.section	.rodata.cst8
	.align 8
.LC32:
	.long	-400107883
	.long	1041313291
	.align 8
.LC33:
	.long	0
	.long	1104006501
	.ident	"GCC: (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x3
3:
	.align 8
4:
