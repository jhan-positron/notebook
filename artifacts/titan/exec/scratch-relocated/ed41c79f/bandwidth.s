	.file	"bandwidth.c"
	.text
	.p2align 4
	.type	k_read, @function
k_read:
.LFB78:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rdi, %rdx
	movl	$16, %ecx
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	andq	$-64, %rsp
	subq	$192, %rsp
	movq	%fs:40, %rax
	movq	%rax, 184(%rsp)
	xorl	%eax, %eax
	movq	%rsp, %rdi
	rep stosq
	testq	%rsi, %rsi
	je	.L2
	decq	%rsi
	vpxor	%xmm0, %xmm0, %xmm0
	shrq	$4, %rsi
	vmovdqa64	%zmm0, %zmm1
	leaq	1(%rsi), %rcx
	.p2align 4
	.p2align 3
.L3:
	incq	%rax
	vpaddq	(%rdx), %zmm1, %zmm1
	vpaddq	64(%rdx), %zmm0, %zmm0
	subq	$-128, %rdx
	cmpq	%rcx, %rax
	jb	.L3
	vmovdqa64	%zmm1, (%rsp)
	vmovdqa64	%zmm0, 64(%rsp)
.L2:
	vmovdqa64	(%rsp), %zmm2
	vpaddq	64(%rsp), %zmm2, %zmm0
	movq	184(%rsp), %rdx
	subq	%fs:40, %rdx
	vextracti64x4	$0x1, %zmm0, %ymm1
	vpaddq	%ymm0, %ymm1, %ymm1
	vextracti64x2	$0x1, %ymm1, %xmm0
	vpaddq	%xmm1, %xmm0, %xmm0
	vpsrldq	$8, %xmm0, %xmm1
	vpaddq	%xmm1, %xmm0, %xmm0
	vmovq	%xmm0, %rax
	jne	.L11
	vzeroupper
	leave
	.cfi_remember_state
	.cfi_def_cfa 7, 8
	ret
.L11:
	.cfi_restore_state
	vzeroupper
	call	__stack_chk_fail@PLT
	.cfi_endproc
.LFE78:
	.size	k_read, .-k_read
	.p2align 4
	.type	k_write, @function
k_write:
.LFB79:
	.cfi_startproc
	movq	%rsi, %rcx
	testq	%rsi, %rsi
	je	.L27
	leaq	-1(%rsi), %rax
	cmpq	$6, %rax
	jbe	.L19
	shrq	$3, %rsi
	vpbroadcastq	%rdx, %zmm0
	movq	%rdi, %rax
	salq	$6, %rsi
	addq	%rdi, %rsi
	.p2align 4
	.p2align 3
.L15:
	vmovdqu64	%zmm0, (%rax)
	addq	$64, %rax
	cmpq	%rax, %rsi
	jne	.L15
	movq	%rcx, %rax
	andq	$-8, %rax
	testb	$7, %cl
	je	.L26
.L14:
	movq	%rcx, %rsi
	subq	%rax, %rsi
	leaq	-1(%rsi), %r8
	cmpq	$2, %r8
	jbe	.L17
	movq	%rsi, %r8
	vpbroadcastq	%rdx, %ymm0
	andq	$-4, %r8
	vmovdqu	%ymm0, (%rdi,%rax,8)
	addq	%r8, %rax
	cmpq	%r8, %rsi
	je	.L26
.L17:
	leaq	0(,%rax,8), %rsi
	leaq	1(%rax), %r8
	movq	%rdx, (%rdi,%rsi)
	cmpq	%rcx, %r8
	jnb	.L26
	addq	$2, %rax
	movq	%rdx, 8(%rdi,%rsi)
	cmpq	%rax, %rcx
	jbe	.L26
	movq	%rdx, 16(%rdi,%rsi)
	vzeroupper
	ret
	.p2align 4
	.p2align 3
.L26:
	vzeroupper
.L27:
	ret
.L19:
	xorl	%eax, %eax
	jmp	.L14
	.cfi_endproc
.LFE79:
	.size	k_write, .-k_write
	.p2align 4
	.type	k_copy, @function
k_copy:
.LFB80:
	.cfi_startproc
	testq	%rdx, %rdx
	je	.L43
	leaq	-1(%rdx), %rax
	cmpq	$6, %rax
	jbe	.L35
	movq	%rdx, %rcx
	xorl	%eax, %eax
	shrq	$3, %rcx
	salq	$6, %rcx
	.p2align 4
	.p2align 3
.L31:
	vmovdqu64	(%rsi,%rax), %zmm0
	vmovdqu64	%zmm0, (%rdi,%rax)
	addq	$64, %rax
	cmpq	%rcx, %rax
	jne	.L31
	movq	%rdx, %rax
	andq	$-8, %rax
	testb	$7, %dl
	je	.L42
.L30:
	movq	%rdx, %rcx
	subq	%rax, %rcx
	leaq	-1(%rcx), %r8
	cmpq	$2, %r8
	jbe	.L33
	leaq	0(,%rax,8), %r8
	vmovdqu	(%rsi,%r8), %ymm1
	vmovdqu	%ymm1, (%rdi,%r8)
	movq	%rcx, %r8
	andq	$-4, %r8
	addq	%r8, %rax
	cmpq	%r8, %rcx
	je	.L42
.L33:
	leaq	0(,%rax,8), %rcx
	movq	(%rsi,%rcx), %r8
	movq	%r8, (%rdi,%rcx)
	leaq	1(%rax), %r8
	cmpq	%r8, %rdx
	jbe	.L42
	movq	8(%rsi,%rcx), %r9
	addq	$2, %rax
	movq	%r9, 8(%rdi,%rcx)
	cmpq	%rax, %rdx
	jbe	.L42
	movq	16(%rsi,%rcx), %rax
	movq	%rax, 16(%rdi,%rcx)
	vzeroupper
	ret
	.p2align 4
	.p2align 3
.L42:
	vzeroupper
.L43:
	ret
.L35:
	xorl	%eax, %eax
	jmp	.L30
	.cfi_endproc
.LFE80:
	.size	k_copy, .-k_copy
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC0:
	.string	"usage: bandwidth [--threads T --cpus LIST] [--bytes B] [--kernel read|write|copy|all] [--min-ms MS] [--reps R] [--no-thp]\n"
	.text
	.p2align 4
	.type	usage, @function
usage:
.LFB83:
	.cfi_startproc
	pushq	%rax
	.cfi_def_cfa_offset 16
	popq	%rax
	.cfi_def_cfa_offset 8
	leaq	.LC0(%rip), %rdi
	movl	$122, %edx
	movl	$1, %esi
	subq	$8, %rsp
	.cfi_def_cfa_offset 16
	movq	stderr(%rip), %rcx
	call	fwrite@PLT
	movl	$2, %edi
	call	exit@PLT
	.cfi_endproc
.LFE83:
	.size	usage, .-usage
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC1:
	.string	"sched_setaffinity"
.LC2:
	.string	"mmap"
.LC3:
	.string	"madvise (continuing)"
	.text
	.p2align 4
	.type	worker, @function
worker:
.LFB82:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdi, %r13
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$264, %rsp
	.cfi_def_cfa_offset 320
	movq	%fs:40, %rax
	movq	%rax, 248(%rsp)
	xorl	%eax, %eax
	movl	$3, %eax
	shrx	%rax, 4104+cfg(%rip), %r15
	call	getpid@PLT
	movslq	0(%r13), %rdx
	cltq
	movq	4104+cfg(%rip), %r12
	movq	$1, 48(%rsp)
	leaq	1(%rdx,%rax), %rdx
	movabsq	$-7046029254386353131, %rax
	imulq	%rax, %rdx
	movq	%rdx, 40(%rsp)
	cmpq	$8388608, %r12
	ja	.L47
	movl	$8388608, %eax
	xorl	%edx, %edx
	divq	%r12
	movq	%rax, 48(%rsp)
.L47:
	movl	4+cfg(%rip), %esi
	testl	%esi, %esi
	jne	.L90
.L48:
	addq	$2097151, %r12
	xorl	%r9d, %r9d
	movl	$-1, %r8d
	movl	$34, %ecx
	andq	$-2097152, %r12
	movl	$3, %edx
	xorl	%edi, %edi
	leaq	2097152(%r12), %rsi
	call	mmap@PLT
	movq	%rax, %rbp
	cmpq	$-1, %rax
	je	.L55
	addq	$2097151, %rbp
	movl	$14, %edx
	movq	%r12, %rsi
	andq	$-2097152, %rbp
	cmpl	$1, 4140+cfg(%rip)
	movq	%rbp, %rdi
	adcl	$0, %edx
	call	madvise@PLT
	testl	%eax, %eax
	jne	.L91
.L53:
	movq	40(%rsp), %rdx
	movq	%rbp, 8(%r13)
	movq	%r15, %rsi
	movq	%rbp, %rdi
	call	k_write
	movl	4120+cfg(%rip), %ecx
	testl	%ecx, %ecx
	jne	.L92
.L54:
	leaq	96(%rsp), %rax
	movq	40(%rsp), %rcx
	xorl	%r14d, %r14d
	movq	%rax, 24(%rsp)
	movq	48(%rsp), %rax
	addq	%rcx, %rax
	movq	%rax, 56(%rsp)
.L59:
	leaq	4112+cfg(%rip), %rax
	movl	%r14d, 64(%rsp)
	movl	(%rax,%r14,4), %edx
	testl	%edx, %edx
	jne	.L58
.L61:
	incq	%r14
	cmpq	$3, %r14
	jne	.L59
	movq	248(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L93
	addq	$264, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	xorl	%eax, %eax
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
.L58:
	.cfi_restore_state
	movl	4136+cfg(%rip), %eax
	testl	%eax, %eax
	jle	.L61
	movq	%r14, %rax
	movl	$0, 68(%rsp)
	movq	%r13, 16(%rsp)
	salq	$9, %rax
	addq	%r13, %rax
	movq	%rax, 72(%rsp)
	.p2align 4
	.p2align 3
.L70:
	movq	16(%rsp), %rax
	movq	8(%rax), %rdi
	cmpq	$1, %r14
	je	.L62
	cmpl	$2, 64(%rsp)
	jne	.L94
	movq	16(%rax), %r8
	movq	%rdi, %rsi
	movq	%r15, %rdx
	movq	%r8, %rdi
	call	k_copy
.L64:
	leaq	bar(%rip), %rdi
	xorl	%ebx, %ebx
	call	pthread_barrier_wait@PLT
	movq	24(%rsp), %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	vxorpd	%xmm4, %xmm4, %xmm4
	movq	$0, 8(%rsp)
	vcvtsi2sdq	104(%rsp), %xmm4, %xmm0
	vmovsd	%xmm0, %xmm0, %xmm1
	vcvtsi2sdq	96(%rsp), %xmm4, %xmm0
	vfmadd132sd	.LC4(%rip), %xmm0, %xmm1
	vmovsd	%xmm1, 32(%rsp)
	.p2align 4
	.p2align 3
.L69:
	movq	8(%rsp), %rax
	movq	%rbx, %r13
	movq	56(%rsp), %rbp
	movq	40(%rsp), %r12
	addq	%rax, %rbp
	addq	%rax, %r12
	movq	%rbp, %rbx
	movq	16(%rsp), %rbp
	jmp	.L68
	.p2align 4
	.p2align 3
.L66:
	movq	16(%rbp), %r8
	movq	%rdi, %rsi
	movq	%r15, %rdx
	movq	%r8, %rdi
	call	k_copy
	movq	4104+cfg(%rip), %rax
	addq	%rax, %rax
.L67:
	incq	%r12
	addq	%rax, %r13
	cmpq	%r12, %rbx
	je	.L95
.L68:
	movq	8(%rbp), %rdi
	cmpq	$1, %r14
	je	.L65
	cmpl	$2, 64(%rsp)
	je	.L66
	movq	%r15, %rsi
	incq	%r12
	call	k_read
	movq	%rax, 88(%rsp)
	movq	4104+cfg(%rip), %rax
	addq	%rax, %r13
	cmpq	%r12, %rbx
	jne	.L68
.L95:
	movq	24(%rsp), %rsi
	movl	$1, %edi
	movq	48(%rsp), %rcx
	movq	%r13, %rbx
	addq	%rcx, 8(%rsp)
	call	clock_gettime@PLT
	vxorpd	%xmm2, %xmm2, %xmm2
	vcvtsi2sdq	96(%rsp), %xmm2, %xmm1
	vcvtsi2sdq	104(%rsp), %xmm2, %xmm0
	vfmadd132sd	.LC4(%rip), %xmm1, %xmm0
	vmovsd	4128+cfg(%rip), %xmm1
	vsubsd	32(%rsp), %xmm0, %xmm0
	vcomisd	%xmm0, %xmm1
	ja	.L69
	movq	72(%rsp), %rax
	leaq	bar(%rip), %rdi
	movq	%r13, 24(%rax)
	vmovsd	%xmm0, 32(%rax)
	movq	%rax, %rbx
	call	pthread_barrier_wait@PLT
	addq	$16, %rbx
	incl	68(%rsp)
	movq	%rbx, 72(%rsp)
	movl	68(%rsp), %eax
	cmpl	%eax, 4136+cfg(%rip)
	jg	.L70
	movq	16(%rsp), %r13
	jmp	.L61
	.p2align 4
	.p2align 3
.L65:
	movq	%r12, %rdx
	movq	%r15, %rsi
	call	k_write
	movq	4104+cfg(%rip), %rax
	jmp	.L67
.L94:
	movq	%r15, %rsi
	call	k_read
	movq	%rax, 88(%rsp)
	jmp	.L64
.L62:
	movq	40(%rsp), %rdx
	movq	%r15, %rsi
	call	k_write
	jmp	.L64
.L90:
	movl	4(%r13), %esi
	leaq	112(%rsp), %rdx
	xorl	%eax, %eax
	movl	$16, %ecx
	movq	%rdx, %rdi
	rep stosq
	movslq	%esi, %rax
	cmpq	$1023, %rax
	jbe	.L96
.L49:
	xorl	%edi, %edi
	movl	$128, %esi
	call	sched_setaffinity@PLT
	testl	%eax, %eax
	jne	.L97
	movq	4104+cfg(%rip), %r12
	jmp	.L48
.L92:
	movq	4104+cfg(%rip), %rax
	xorl	%r9d, %r9d
	movl	$-1, %r8d
	movl	$34, %ecx
	movl	$3, %edx
	xorl	%edi, %edi
	leaq	2097151(%rax), %r12
	andq	$-2097152, %r12
	leaq	2097152(%r12), %rsi
	call	mmap@PLT
	movq	%rax, %rbp
	cmpq	$-1, %rax
	je	.L55
	addq	$2097151, %rbp
	movl	$14, %edx
	movq	%r12, %rsi
	andq	$-2097152, %rbp
	cmpl	$1, 4140+cfg(%rip)
	movq	%rbp, %rdi
	adcl	$0, %edx
	call	madvise@PLT
	testl	%eax, %eax
	jne	.L98
.L57:
	movq	40(%rsp), %rdx
	movq	%rbp, 16(%r13)
	movq	%r15, %rsi
	movq	%rbp, %rdi
	call	k_write
	jmp	.L54
.L91:
	leaq	.LC3(%rip), %rdi
	call	perror@PLT
	jmp	.L53
.L96:
	shrq	$6, %rax
	movl	$1, %ecx
	shlx	%rsi, %rcx, %rcx
	orq	%rcx, (%rdx,%rax,8)
	jmp	.L49
.L98:
	leaq	.LC3(%rip), %rdi
	call	perror@PLT
	jmp	.L57
.L97:
	leaq	.LC1(%rip), %rdi
	call	perror@PLT
	movl	$2, %edi
	call	exit@PLT
.L93:
	call	__stack_chk_fail@PLT
.L55:
	leaq	.LC2(%rip), %rdi
	call	perror@PLT
	movl	$2, %edi
	call	exit@PLT
	.cfi_endproc
.LFE82:
	.size	worker, .-worker
	.section	.rodata.str1.1
.LC9:
	.string	"madvise"
.LC10:
	.string	"nohugepage"
.LC15:
	.string	"--no-thp"
.LC16:
	.string	"--threads"
.LC17:
	.string	"--cpus"
.LC18:
	.string	","
.LC19:
	.string	"bad cpu list: %s\n"
	.section	.rodata.str1.8
	.align 8
.LC20:
	.string	"bad cpu list: more than %d cpus\n"
	.section	.rodata.str1.1
.LC21:
	.string	"--bytes"
.LC22:
	.string	"bad size: %s\n"
.LC23:
	.string	"--min-ms"
.LC25:
	.string	"--reps"
.LC26:
	.string	"--kernel"
.LC27:
	.string	"all"
.LC28:
	.string	"read"
.LC29:
	.string	"write"
.LC30:
	.string	"copy"
.LC31:
	.string	"--threads requires --cpus\n"
	.section	.rodata.str1.8
	.align 8
.LC32:
	.string	"warning: %d threads on %d cpus: cpus are oversubscribed\n"
	.section	.rodata.str1.1
.LC33:
	.string	"setup"
.LC34:
	.string	"pthread_create"
	.section	.rodata.str1.8
	.align 8
.LC35:
	.string	"# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; threads=%d bytes_per_thread=%lu min_ms=%.0f thp=%s\n"
	.align 8
.LC36:
	.string	"kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps"
	.align 8
.LC38:
	.string	"%s,%d,%lu,%d,%lu,%.4f,%.2f,%.2f,%.2f,%.2f\n"
	.section	.rodata.str1.1
.LC39:
	.string	"%s,%d,%lu,best,,,%.2f,,,\n"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB84:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$104, %rsp
	.cfi_def_cfa_offset 160
	movl	%edi, 8(%rsp)
	movq	%rsi, 16(%rsp)
	movq	%fs:40, %rax
	movq	%rax, 88(%rsp)
	xorl	%eax, %eax
	movq	.LC14(%rip), %rax
	movq	$1048576, 4104+cfg(%rip)
	movl	$1, 4120+cfg(%rip)
	movq	%rax, 4112+cfg(%rip)
	cmpl	$1, %edi
	jle	.L100
	movl	$1, %ebx
	movl	$0, 32(%rsp)
	leaq	cfg(%rip), %r13
	jmp	.L127
	.p2align 4
	.p2align 3
.L230:
	movl	$0, 4140+cfg(%rip)
	movl	%r14d, %ebx
.L102:
	cmpl	%ebx, 8(%rsp)
	jle	.L229
.L127:
	movq	16(%rsp), %rax
	movslq	%ebx, %rbp
	leaq	.LC15(%rip), %rsi
	leal	1(%rbx), %r14d
	salq	$3, %rbp
	movq	(%rax,%rbp), %r12
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	je	.L230
	leaq	.LC16(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	cmpl	8(%rsp), %r14d
	setl	%r14b
	testl	%eax, %eax
	jne	.L103
	testb	%r14b, %r14b
	jne	.L231
.L103:
	leaq	.LC17(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	sete	%r8b
	movl	%r8d, %r15d
	andb	%r14b, %r15b
	jne	.L232
	leaq	.LC21(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L114
	testb	%r14b, %r14b
	jne	.L233
.L114:
	leaq	.LC23(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L121
	testb	%r14b, %r14b
	jne	.L234
.L121:
	leaq	.LC25(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L122
	testb	%r14b, %r14b
	jne	.L235
.L122:
	leaq	.LC26(%rip), %rsi
	movq	%r12, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L228
	testb	%r14b, %r14b
	je	.L228
	movq	16(%rsp), %rax
	leaq	.LC27(%rip), %rsi
	movq	8(%rax,%rbp), %rbp
	movq	$0, 4112+cfg(%rip)
	movl	$0, 4120+cfg(%rip)
	movq	%rbp, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L124
	movq	.LC14(%rip), %rax
	movl	$1, 4120+cfg(%rip)
	addl	$2, %ebx
	movq	%rax, 4112+cfg(%rip)
	cmpl	%ebx, 8(%rsp)
	jg	.L127
.L229:
	cmpl	$0, 32(%rsp)
	je	.L100
	cmpl	$0, 4+cfg(%rip)
	je	.L236
.L100:
	movl	cfg(%rip), %r12d
	testl	%r12d, %r12d
	jle	.L228
	movl	4136+cfg(%rip), %eax
	decl	%eax
	cmpl	$31, %eax
	ja	.L228
	testb	$127, 4104+cfg(%rip)
	jne	.L228
	movl	4+cfg(%rip), %r8d
	testl	%r8d, %r8d
	je	.L128
	cmpl	%r8d, %r12d
	jg	.L237
.L128:
	movslq	%r12d, %rax
	movl	$1568, %esi
	movq	%rax, %rdi
	call	calloc@PLT
	movq	%rax, 16(%rsp)
	testq	%rax, %rax
	je	.L129
	leaq	bar(%rip), %r14
	leal	1(%r12), %edx
	xorl	%esi, %esi
	movq	%r14, %rdi
	call	pthread_barrier_init@PLT
	movl	%eax, %r15d
	testl	%eax, %eax
	jne	.L129
	movl	cfg(%rip), %edx
	testl	%edx, %edx
	jle	.L131
	movq	16(%rsp), %rbx
	xorl	%r13d, %r13d
	leaq	cfg(%rip), %rbp
	leaq	worker(%rip), %r12
	jmp	.L135
.L134:
	movl	0(%rbp), %edx
	incl	%r13d
	addq	$1568, %rbx
	cmpl	%r13d, %edx
	jle	.L131
.L135:
	movl	4+cfg(%rip), %ecx
	movl	%r13d, (%rbx)
	movl	$-1, %eax
	testl	%ecx, %ecx
	je	.L133
	movl	%r13d, %eax
	cltd
	idivl	%ecx
	movslq	%edx, %rdx
	movl	8(%rbp,%rdx,4), %eax
.L133:
	xorl	%esi, %esi
	movl	%eax, 4(%rbx)
	leaq	1560(%rbx), %rdi
	movq	%rbx, %rcx
	movq	%r12, %rdx
	call	pthread_create@PLT
	testl	%eax, %eax
	je	.L134
	leaq	.LC34(%rip), %rdi
	movl	$2, %r15d
	call	perror@PLT
.L99:
	movq	88(%rsp), %rax
	subq	%fs:40, %rax
	jne	.L238
	addq	$104, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	movl	%r15d, %eax
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
.L124:
	.cfi_restore_state
	leaq	.LC28(%rip), %rsi
	movq	%rbp, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L125
	movl	$1, 4112+cfg(%rip)
	addl	$2, %ebx
	jmp	.L102
.L231:
	movq	16(%rsp), %rax
	movl	$10, %edx
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%rbp), %rdi
	call	strtol@PLT
	movl	$1, 32(%rsp)
	movl	%eax, 0(%r13)
	jmp	.L102
.L232:
	movq	16(%rsp), %rax
	movq	8(%rax,%rbp), %rdi
	leaq	.LC18(%rip), %rbp
	movq	%rbp, %rsi
	call	strtok@PLT
	movq	%rax, %r14
	testq	%rax, %rax
	je	.L105
	leaq	80(%rsp), %rax
	leaq	72(%rsp), %r12
	movl	%ebx, 40(%rsp)
	movq	%rax, 24(%rsp)
	movq	%r14, %rax
	movl	%r15d, %r14d
	movq	%rax, %r15
	.p2align 4
	.p2align 3
.L113:
	movq	%r15, %rdi
	movl	$10, %edx
	movq	%r12, %rsi
	call	strtol@PLT
	movq	72(%rsp), %rdi
	movq	%rax, %rbx
	cmpq	%r15, %rdi
	je	.L109
	movzbl	(%rdi), %eax
	movq	%rbx, %r8
	cmpb	$45, %al
	je	.L239
.L107:
	testb	%al, %al
	jne	.L109
	movq	%rbx, %rax
	shrq	$63, %rax
	cmpq	%rbx, %r8
	setl	%dl
	orl	%eax, %edx
	cmpq	$1023, %r8
	setg	%al
	orb	%al, %dl
	jne	.L109
	movslq	4+cfg(%rip), %rsi
	movl	$1024, %ecx
	subl	%esi, %ecx
	movq	%rsi, %rax
	subq	%rbx, %rsi
	addq	%rbx, %rcx
	leaq	0(%r13,%rsi,4), %rsi
	jmp	.L112
	.p2align 4
	.p2align 3
.L156:
	movl	%r14d, %edx
.L112:
	cmpq	%rcx, %rbx
	je	.L240
	movl	%ebx, 8(%rsi,%rbx,4)
	incq	%rbx
	incl	%eax
	cmpq	%rbx, %r8
	jge	.L156
	movq	%rbp, %rsi
	xorl	%edi, %edi
	movl	%eax, 4+cfg(%rip)
	call	strtok@PLT
	movq	%rax, %r15
	testq	%rax, %rax
	jne	.L113
	movl	40(%rsp), %ebx
	addl	$2, %ebx
	jmp	.L102
.L108:
	movq	%r15, 72(%rsp)
	.p2align 4
	.p2align 3
.L109:
	movq	%r15, %rcx
	leaq	.LC19(%rip), %rdx
.L227:
	movq	stderr(%rip), %rdi
	movl	$1, %esi
	xorl	%eax, %eax
	call	__fprintf_chk@PLT
	movl	$2, %edi
	call	exit@PLT
.L239:
	movq	24(%rsp), %rsi
	incq	%rdi
	movl	$10, %edx
	call	strtol@PLT
	movq	72(%rsp), %rdi
	movq	%rax, %r8
	movq	80(%rsp), %rax
	leaq	1(%rdi), %rdx
	cmpq	%rdx, %rax
	je	.L108
	movq	%rax, 72(%rsp)
	cmpq	%r15, %rax
	je	.L109
	movzbl	(%rax), %eax
	jmp	.L107
.L233:
	movq	16(%rsp), %rax
	leaq	80(%rsp), %rsi
	movq	8(%rax,%rbp), %r12
	movq	%r12, %rdi
	call	strtod@PLT
	movq	80(%rsp), %rax
	movzbl	(%rax), %edi
	leal	-71(%rdi), %ecx
	cmpb	$38, %cl
	ja	.L157
	movl	$1, %edx
	shlx	%rcx, %rdx, %rdx
	movabsq	$4294967297, %rcx
	testq	%rcx, %rdx
	jne	.L116
	movabsq	$274877907008, %rcx
	testq	%rcx, %rdx
	jne	.L117
	movabsq	$68719476752, %rcx
	testq	%rcx, %rdx
	jne	.L241
.L118:
	movq	%r12, %rcx
	leaq	.LC22(%rip), %rdx
	jmp	.L227
	.p2align 4
	.p2align 3
.L125:
	leaq	.LC29(%rip), %rsi
	movq	%rbp, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L126
	movl	$1, 4116+cfg(%rip)
	addl	$2, %ebx
	jmp	.L102
.L234:
	movq	16(%rsp), %rax
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%rbp), %rdi
	call	strtod@PLT
	vdivsd	.LC24(%rip), %xmm0, %xmm0
	vmovsd	%xmm0, 4128+cfg(%rip)
	jmp	.L102
.L235:
	movq	16(%rsp), %rax
	movl	$10, %edx
	xorl	%esi, %esi
	addl	$2, %ebx
	movq	8(%rax,%rbp), %rdi
	call	strtol@PLT
	movl	%eax, 4136+cfg(%rip)
	jmp	.L102
.L126:
	leaq	.LC30(%rip), %rsi
	movq	%rbp, %rdi
	call	strcmp@PLT
	testl	%eax, %eax
	jne	.L228
	movl	$1, 4120+cfg(%rip)
	addl	$2, %ebx
	jmp	.L102
.L240:
	testb	%dl, %dl
	je	.L111
	movl	%eax, 4+cfg(%rip)
.L111:
	movq	stderr(%rip), %rdi
	movl	$1024, %ecx
	leaq	.LC20(%rip), %rdx
	movl	$1, %esi
	xorl	%eax, %eax
	call	__fprintf_chk@PLT
	movl	$2, %edi
	call	exit@PLT
.L131:
	vmovsd	.LC24(%rip), %xmm0
	cmpl	$0, 4140+cfg(%rip)
	leaq	.LC10(%rip), %rax
	leaq	.LC9(%rip), %r8
	vmulsd	4128+cfg(%rip), %xmm0, %xmm0
	movq	4104+cfg(%rip), %rcx
	leaq	.LC35(%rip), %rsi
	movl	$1, %edi
	leaq	kernel_name(%rip), %r13
	cmove	%rax, %r8
	movl	$1, %eax
	xorl	%ebp, %ebp
	call	__printf_chk@PLT
	leaq	.LC36(%rip), %rdi
	call	puts@PLT
	leaq	4112+cfg(%rip), %rax
	movl	%r15d, 60(%rsp)
	movq	%rax, 40(%rsp)
	movq	16(%rsp), %rax
	addq	$1568, %rax
	movq	%rax, 48(%rsp)
.L150:
	movq	40(%rsp), %rax
	movl	(%rax), %ecx
	testl	%ecx, %ecx
	jne	.L242
.L137:
	addq	$32, %rbp
	addq	$4, 40(%rsp)
	addq	$8, %r13
	cmpq	$96, %rbp
	jne	.L150
	cmpl	$0, cfg(%rip)
	movl	60(%rsp), %r15d
	jle	.L99
	movq	16(%rsp), %rbx
	xorl	%r12d, %r12d
	leaq	cfg(%rip), %rbp
	addq	$1560, %rbx
.L152:
	movq	(%rbx), %rdi
	xorl	%esi, %esi
	incl	%r12d
	addq	$1568, %rbx
	call	pthread_join@PLT
	cmpl	%r12d, 0(%rbp)
	jg	.L152
	jmp	.L99
.L242:
	cmpl	$0, 4136+cfg(%rip)
	jle	.L160
	vmovsd	.LC11(%rip), %xmm4
	movq	%rbp, %rbx
	xorl	%r15d, %r15d
	vxorpd	%xmm9, %xmm9, %xmm9
	salq	$4, %rbx
	addq	16(%rsp), %rbx
	leaq	.LC38(%rip), %r12
	vmovsd	%xmm4, 8(%rsp)
.L149:
	movq	%r14, %rdi
	vmovsd	%xmm9, 32(%rsp)
	movl	%r15d, 24(%rsp)
	call	pthread_barrier_wait@PLT
	movq	%r14, %rdi
	call	pthread_barrier_wait@PLT
	leaq	cfg(%rip), %rax
	vmovsd	32(%rsp), %xmm9
	vxorps	%xmm7, %xmm7, %xmm7
	movl	(%rax), %r10d
	movq	.LC37(%rip), %rax
	movl	24(%rsp), %r9d
	testl	%r10d, %r10d
	vmovq	%rax, %xmm8
	jle	.L161
	leal	-1(%r10), %esi
	movq	.LC13(%rip), %rdi
	movq	%rbx, %rax
	xorl	%ecx, %ecx
	imulq	$98, %rsi, %rsi
	vmovsd	%xmm9, %xmm9, %xmm6
	vmovsd	%xmm9, %xmm9, %xmm3
	vmovsd	%xmm9, %xmm9, %xmm5
	addq	%rbp, %rsi
	vmovq	%rdi, %xmm2
	addq	%r15, %rsi
	salq	$4, %rsi
	addq	48(%rsp), %rsi
	.p2align 4
	.p2align 3
.L146:
	vmovsd	32(%rax), %xmm1
	movq	24(%rax), %rdx
	addq	$1568, %rax
	vcvtusi2sdq	%rdx, %xmm7, %xmm0
	addq	%rdx, %rcx
	vdivsd	%xmm1, %xmm0, %xmm0
	vmaxsd	%xmm5, %xmm1, %xmm5
	vdivsd	%xmm8, %xmm0, %xmm0
	vminsd	%xmm2, %xmm0, %xmm2
	vmaxsd	%xmm3, %xmm0, %xmm3
	vaddsd	%xmm0, %xmm6, %xmm6
	cmpq	%rsi, %rax
	jne	.L146
.L139:
	vcvtusi2sdq	%rcx, %xmm7, %xmm0
	vdivsd	%xmm5, %xmm0, %xmm1
	movq	0(%r13), %rdx
	movq	4104+cfg(%rip), %r8
	vmovsd	%xmm9, 24(%rsp)
	subq	$8, %rsp
	.cfi_def_cfa_offset 168
	vmovsd	%xmm5, %xmm5, %xmm0
	movq	%r12, %rsi
	movl	$1, %edi
	movl	$5, %eax
	incq	%r15
	addq	$16, %rbx
	vdivsd	%xmm8, %xmm1, %xmm1
	vmaxsd	16(%rsp), %xmm1, %xmm4
	vmovsd	%xmm4, 16(%rsp)
	vcvtsi2sdl	%r10d, %xmm7, %xmm4
	vdivsd	%xmm4, %xmm6, %xmm4
	pushq	%rcx
	.cfi_def_cfa_offset 176
	movl	%r10d, %ecx
	call	__printf_chk@PLT
	cmpl	%r15d, 4136+cfg(%rip)
	popq	%rax
	.cfi_def_cfa_offset 168
	popq	%rdx
	.cfi_def_cfa_offset 160
	vmovsd	24(%rsp), %xmm9
	jg	.L149
.L138:
	vmovsd	8(%rsp), %xmm0
	leaq	cfg(%rip), %rax
	movq	4104+cfg(%rip), %r8
	leaq	.LC39(%rip), %rsi
	movl	(%rax), %ecx
	movq	0(%r13), %rdx
	movl	$1, %edi
	movl	$1, %eax
	call	__printf_chk@PLT
	movq	stdout(%rip), %rdi
	call	fflush@PLT
	jmp	.L137
.L161:
	movq	.LC13(%rip), %rax
	xorl	%ecx, %ecx
	vmovsd	%xmm9, %xmm9, %xmm6
	vmovsd	%xmm9, %xmm9, %xmm3
	vmovsd	%xmm9, %xmm9, %xmm5
	vmovq	%rax, %xmm2
	jmp	.L139
.L241:
	vmovsd	.LC6(%rip), %xmm1
	incq	%rax
	movq	%rax, 80(%rsp)
.L115:
	cmpq	%rax, %r12
	je	.L118
	cmpb	$0, (%rax)
	jne	.L118
	vxorpd	%xmm2, %xmm2, %xmm2
	vcomisd	%xmm0, %xmm2
	jnb	.L118
	vmulsd	%xmm1, %xmm0, %xmm0
	addl	$2, %ebx
	vcvttsd2usi	%xmm0, %rax
	movq	%rax, 4104+cfg(%rip)
	jmp	.L102
.L117:
	incq	%rax
	vmovsd	.LC7(%rip), %xmm1
	movq	%rax, 80(%rsp)
	jmp	.L115
.L116:
	incq	%rax
	vmovsd	.LC8(%rip), %xmm1
	movq	%rax, 80(%rsp)
	jmp	.L115
.L157:
	vmovsd	.LC5(%rip), %xmm1
	jmp	.L115
.L237:
	movq	stderr(%rip), %rdi
	movl	%r12d, %ecx
	leaq	.LC32(%rip), %rdx
	movl	$1, %esi
	xorl	%eax, %eax
	call	__fprintf_chk@PLT
	movl	cfg(%rip), %r12d
	jmp	.L128
.L129:
	leaq	.LC33(%rip), %rdi
	movl	$2, %r15d
	call	perror@PLT
	jmp	.L99
.L105:
	addl	$2, %ebx
	jmp	.L102
.L236:
	movq	stderr(%rip), %rcx
	movl	$26, %edx
	movl	$1, %esi
	leaq	.LC31(%rip), %rdi
	call	fwrite@PLT
.L228:
	call	usage
.L238:
	call	__stack_chk_fail@PLT
.L160:
	vmovsd	.LC11(%rip), %xmm4
	vmovsd	%xmm4, 8(%rsp)
	jmp	.L138
	.cfi_endproc
.LFE84:
	.size	main, .-main
	.local	bar
	.comm	bar,32,32
	.data
	.align 32
	.type	cfg, @object
	.size	cfg, 4144
cfg:
	.long	1
	.zero	4124
	.long	0
	.long	1071644672
	.long	3
	.long	1
	.section	.data.rel.ro.local,"aw"
	.align 16
	.type	kernel_name, @object
	.size	kernel_name, 24
kernel_name:
	.quad	.LC28
	.quad	.LC29
	.quad	.LC30
	.section	.rodata.cst8,"aM",@progbits,8
	.align 8
.LC4:
	.long	-400107883
	.long	1041313291
	.align 8
.LC5:
	.long	0
	.long	1072693248
	.align 8
.LC6:
	.long	0
	.long	1083179008
	.align 8
.LC7:
	.long	0
	.long	1093664768
	.align 8
.LC8:
	.long	0
	.long	1104150528
	.align 8
.LC11:
	.long	0
	.long	-1074790400
	.align 8
.LC13:
	.long	966823146
	.long	1177108057
	.align 8
.LC14:
	.long	1
	.long	1
	.align 8
.LC24:
	.long	0
	.long	1083129856
	.align 8
.LC37:
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
