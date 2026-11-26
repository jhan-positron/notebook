/*
 * bwx_selftest.c - "bwx --selftest": checks what every kernel of bwx.c does
 * to memory. bwx.c includes this file, so the test runs the machine code of
 * the binary that is timed, through the same call() as the benchmark.
 * Model: kernels-2026-11-13/selftest.c.
 *
 * Every buffer ends at a page that cannot be read or written (PROT_NONE) and
 * starts after one. A kernel that touches a byte within one page before the
 * buffer or within one page after it dies with SIGSEGV. The line "call,..."
 * printed before each kernel call names the kernel that died.
 * Exit status 0 means every check passed.
 *
 * Checks for every kernel that stores (write and copy kinds): every word is
 * compared, on whole buffers and on one 256 B block at a page start and at a
 * page end.
 * Checks for every read kernel: the buffer is unchanged and no guard page is
 * touched. The kernel must fault when one page inside its range is made
 * PROT_NONE, for each page of a 3-page range. oldread and oldread2 return a
 * sum: it must equal the sum of all words.
 *
 * Limits. For the read kernels that return nothing, the test proves that
 * every page of the range is touched, not every byte: the objdump listing is
 * the evidence for the bytes. It cannot see in which order a copy kernel
 * loads and stores. It does not check that a kernel preserves the
 * callee-saved registers d8-d15.
 */
static int failures;
static sigjmp_buf fault_jmp;
static volatile uintptr_t fault_addr;

/* n words whose first byte follows a PROT_NONE page and whose last byte
 * precedes one. n * 8 must be a multiple of the page size. */
static uint64_t *guarded(size_t n)
{
    size_t len = n * 8;
    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page_bytes, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED || mprotect(raw + page_bytes, len, PROT_READ | PROT_WRITE) != 0) {
        perror("guarded");
        exit(2);
    }
    return (uint64_t *)(raw + page_bytes);
}

static void unguard(uint64_t *p, size_t n)
{
    munmap((uint8_t *)p - page_bytes, n * 8 + 2 * (size_t)page_bytes);
}

static uint64_t pattern(size_t i, uint64_t salt)
{
    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;
}

static void calling(const struct kdef *kd, size_t n)
{
    printf("call,%s,%zu\n", kd->name, n * 8);
}

static void check(int ok, const struct kdef *kd, const char *what, size_t n)
{
    printf("%s,%s,%zu,%s\n", kd->name, what, n * 8, ok ? "pass" : "FAIL");
    if (!ok)
        failures++;
}

static int is_read(const struct kdef *kd)
{
    return kd->type == T_READ || kd->type == T_OLDREAD;
}

/* The kernel on a whole guarded buffer of n words. */
static void test_size(const struct kdef *kd, size_t n)
{
    struct thread t = { .a = guarded(n), .b = guarded(n) };
    uint64_t *a = t.a, *b = t.b, sum = 0;
    uint64_t v = 0xA5A5F00D12345678ULL + n;
    volatile uint64_t sink = 0;
    int ok = 1;

    /* Every word of the source is different, so a store of the wrong vector
     * or to the wrong offset is seen. */
    for (size_t i = 0; i < n; i++) {
        a[i] = pattern(i, 1);
        b[i] = 0;
        sum += a[i];
    }
    calling(kd, n);
    call(kd, &t, 0, n * 8, v, &sink);
    if (is_read(kd)) {
        /* read: must leave every word as it was (and must not fault) */
        for (size_t i = 0; i < n; i++)
            ok &= a[i] == pattern(i, 1);
        check(ok, kd, "buffer unchanged", n);
        if (kd->type == T_OLDREAD)
            check(sink == sum, kd, "returned sum equals the sum of all words", n);
    } else if (kd->type == T_WRITE) {
        /* write: every word must hold v afterwards; no word may keep the old pattern */
        for (size_t i = 0; i < n; i++)
            ok &= a[i] == v;
        check(ok, kd, "every word equals v", n);
    } else {
        /* copy: destination must equal source word for word; source unchanged */
        for (size_t i = 0; i < n; i++)
            ok &= b[i] == pattern(i, 1);
        check(ok, kd, "destination equals source", n);
        ok = 1;
        for (size_t i = 0; i < n; i++)
            ok &= a[i] == pattern(i, 1);
        check(ok, kd, "source unchanged", n);
    }
    unguard(a, n);
    unguard(b, n);
}

/* One block of 256 B (32 words) at word offset off inside one guarded page.
 * Words of the page outside the 256 B must keep their old value. */
static void test_block(const struct kdef *kd, size_t off)
{
    size_t n = (size_t)page_bytes / 8, m = 32;
    struct thread t = { .a = guarded(n), .b = guarded(n) };
    uint64_t *a = t.a, *b = t.b;
    uint64_t v = 0x0123456789ABCDEFULL;
    volatile uint64_t sink = 0;
    int ok = 1;

    for (size_t i = 0; i < n; i++) {
        a[i] = pattern(i, 3);
        b[i] = pattern(i, 4);
    }
    calling(kd, m);
    call(kd, &t, off * 8, m * 8, v, &sink);
    if (is_read(kd)) {
        for (size_t i = 0; i < n; i++)
            ok &= a[i] == pattern(i, 3);
        check(ok, kd, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);
    } else if (kd->type == T_WRITE) {
        for (size_t i = 0; i < n; i++)
            ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));
        check(ok, kd, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);
    } else {
        for (size_t i = 0; i < n; i++)
            ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4)) && a[i] == pattern(i, 3);
        check(ok, kd, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);
    }
    unguard(a, n);
    unguard(b, n);
}

static void on_fault(int sig, siginfo_t *si, void *ctx)
{
    (void)sig;
    (void)ctx;
    fault_addr = (uintptr_t)si->si_addr;
    siglongjmp(fault_jmp, 1);
}

/* Read kernels: a range of 3 pages, with one page inside it made PROT_NONE.
 * The kernel must fault, and the fault address must lie in that page. This
 * shows that the kernel touches every page of its range. */
static void test_touch(const struct kdef *kd)
{
    size_t n = 3 * (size_t)page_bytes / 8;
    struct thread t = { .a = guarded(n) };
    struct sigaction sa, old;
    volatile uint64_t sink = 0;

    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_fault;
    sa.sa_flags = SA_SIGINFO;
    sigaction(SIGSEGV, &sa, &old);
    for (volatile int j = 0; j < 3; j++) {
        uint8_t *pg = (uint8_t *)t.a + (size_t)j * (size_t)page_bytes;
        volatile int faulted = 0;
        mprotect(pg, (size_t)page_bytes, PROT_NONE);
        fault_addr = 0;
        calling(kd, n);
        if (sigsetjmp(fault_jmp, 1) == 0)
            call(kd, &t, 0, n * 8, 0, &sink);
        else
            faulted = 1;
        mprotect(pg, (size_t)page_bytes, PROT_READ | PROT_WRITE);
        check(faulted && fault_addr >= (uintptr_t)pg && fault_addr < (uintptr_t)pg + (uintptr_t)page_bytes, kd,
              j == 0 ? "faults in page 0 of 3 when it is PROT_NONE"
                     : j == 1 ? "faults in page 1 of 3 when it is PROT_NONE" : "faults in page 2 of 3 when it is PROT_NONE",
              n);
    }
    sigaction(SIGSEGV, &old, NULL);
    unguard(t.a, n);
}

static int selftest(void)
{
    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */
    printf("# selftest: page_bytes=%ld kernels=%d (%s); columns: kernel,check,bytes,result\n", page_bytes, K_COUNT,
           STANDIN ? "STAND-IN kernels, not AArch64" : "aarch64");
    if (page_bytes % 256 != 0) {
        fprintf(stderr, "page size is not a multiple of 256\n");
        return 2;
    }
    /* whole buffers of 1 page, 3 pages and 1 MiB */
    size_t words[] = { (size_t)page_bytes / 8, 3 * (size_t)page_bytes / 8, (1UL << 20) / 8 };
    /* one block: at the start of a page (guard before it) and at the end (guard after it) */
    size_t offs[] = { 0, (size_t)page_bytes / 8 - 32 };
    for (int k = 0; k < K_COUNT; k++) {
        for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)
            test_size(&kernels[k], words[i]);
        for (size_t i = 0; i < 2; i++)
            test_block(&kernels[k], offs[i]);
        if (is_read(&kernels[k]))
            test_touch(&kernels[k]);
    }
    printf("# failures=%d\n", failures);
    return failures ? 1 : 0;
}
