/*
 * bwx8_selftest.c - "bwx8 --selftest": checks what every kernel of bwx8.c
 * does to memory, and the accounting of the trial mode. bwx8.c includes this
 * file, so the test runs the machine code of the binary that is timed,
 * through the same call() as the benchmark. The kernel checks are the text of
 * bwx_selftest.c. test_trial() at the end is new.
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
 *
 * Checks of the trial mode (test_trial): one trial with all phases and bins
 * runs through run_trial(), the function that the trial mode uses. Every
 * window must hold whole passes and whole groups of passes between clock
 * reads, must last at least its duration, and must not start before the
 * window before it ended. The last bin of a window must hold the bytes of
 * the window. The sink check must pass on a clean buffer and must fail after
 * one word of the buffer is changed.
 *
 * Checks of the rows (test_emit): emit_trial(), the function that prints the
 * rows of a trial, runs on a record with known values. The printed text is
 * compared: the C rows hold differences of two readings, the post P row holds
 * the second snapshot, the E row holds CPU time and the two context-switch
 * counts in their own fields, and the X rows coverage_na, count_multiplexed
 * and sink are printed.
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

static void trial_check(int ok, const char *what, size_t bytes)
{
    printf("trial,%s,%zu,%s\n", what, bytes, ok ? "pass" : "FAIL");
    if (!ok)
        failures++;
}

static int kernel_named(const char *name)
{
    int k = 0;
    while (k < K_COUNT && strcmp(name, kernels[k].name))
        k++;
    if (k == K_COUNT) {
        fprintf(stderr, "selftest: no kernel %s\n", name);
        exit(2);
    }
    return k;
}

/* The trial mode on a guarded buffer of 1 MiB whose words all hold w.v. */
static void test_trial(void)
{
    size_t bytes = 1UL << 20, n = bytes / 8;
    int oldread = kernel_named("oldread"), rd = kernel_named("read"), asmread = kernel_named("asmread");
    struct trial p = { .nwin = 3, .win_ms = 12, .count = CS_CLOSED, .bins = 1,
                       .prev = { asmread, bytes, 4 }, .pfx = { oldread, bytes, 8 },
                       .pred = { rd, 65536, 3 }, .tgt = { oldread, bytes, 0 } };
    struct win win[9];
    struct bin bin[9]; /* 3 target windows, window_bins() = 3 each */
    struct trec r = { .win = win, .nw = trial_windows(&p) };
    struct tw w;
    volatile uint64_t sink = 0;
    int whole = 1, groups = 1, lasts = 1, order = 1, bins_ok = 1;

    memset(&w, 0, sizeof w);
    w.t.group_fd = -1;
    w.v = 0x9E3779B97F4A7C15ULL * 7;
    w.t.a = guarded(n);
    for (size_t i = 0; i < n; i++)
        w.t.a[i] = w.v;

    trial_check(r.nw == 9 && window_bins(&p) == 3, "prev 1 + prefix 4 + pred 1 + target 3 windows", bytes);
    set_windows(&p, win, bin);
    printf("call,trial,%zu\n", bytes);
    run_trial(&w, &p, &r, &sink);
    for (int i = 0; i < r.nw; i++) {
        const struct win *x = &win[i];
        whole &= x->bytes > 0 && x->bytes % x->size == 0;
        groups &= x->bytes % CHECK_BYTES == 0; /* every size here divides 8 MiB */
        lasts &= x->t_end - x->t_start >= x->dur_ns;
        order &= x->t_end > x->t_start && (i == 0 || x->t_start >= win[i - 1].t_end);
        if (x->phase == PH_TARGET) {
            bins_ok &= x->nbin >= 1 && x->nbin <= x->bin_cap && x->bin[x->nbin - 1].bytes == x->bytes &&
                       x->bin[x->nbin - 1].t_end == x->t_end;
            for (int b = 1; b < x->nbin; b++)
                bins_ok &= x->bin[b].t_end > x->bin[b - 1].t_end && x->bin[b].bytes > x->bin[b - 1].bytes;
        } else {
            bins_ok &= x->nbin == 0;
        }
    }
    trial_check(whole, "every window holds whole passes and more than 0 bytes", bytes);
    trial_check(groups, "every window holds a multiple of 8 MiB (clock read after 8 MiB)", bytes);
    trial_check(lasts, "every window lasts at least its requested duration", bytes);
    trial_check(order, "timestamps do not go back from window to window", bytes);
    trial_check(bins_ok, "the last bin of a target window ends the window and holds its bytes", bytes);
    trial_check(r.sink_ok == 1, "sink holds the sum after a trial that ends in old read", bytes);

    p.tgt.k = rd;
    set_windows(&p, win, bin);
    run_trial(&w, &p, &r, &sink);
    trial_check(r.sink_ok == 1, "sink holds the sum of the last old read when the target is new read", bytes);

    p.pfx.k = asmread;
    set_windows(&p, win, bin);
    run_trial(&w, &p, &r, &sink);
    trial_check(r.sink_ok == -1, "sink check is NA for a trial without old read", bytes);

    /* The sink check must be able to fail: one changed word changes the sum. */
    p.tgt.k = oldread;
    w.t.a[n - 1] ^= 1;
    set_windows(&p, win, bin);
    run_trial(&w, &p, &r, &sink);
    trial_check(r.sink_ok == 0, "sink check fails after one word of the buffer is changed", bytes);

    struct counts c[3] = { { .enabled = 0, .running = 0 }, { .enabled = 100, .running = 100 }, { .enabled = 200, .running = 150 } };
    trial_check(first_multiplexed(c, 2) == 1, "running time below enabled time is found in target window 1", 0);
    c[2].running = 200;
    trial_check(first_multiplexed(c, 2) == -1, "equal running and enabled time is not called multiplexed", 0);
    unguard(w.t.a, n);
}

static int has_line(const char *text, const char *line)
{
    size_t n = strlen(line);
    for (const char *s = text; (s = strstr(s, line)) != NULL; s += n)
        if ((s == text || s[-1] == '\n') && s[n] == '\n')
            return 1;
    return 0;
}

/* The text that emit_trial() prints for the record r of the trial p. stdout
 * is a memory stream during the call (glibc lets a program assign stdout). */
static char *emitted(struct tw *w, struct trial *p, struct trec *r)
{
    char *text = NULL;
    size_t len = 0;
    FILE *out = stdout, *mem = open_memstream(&text, &len);
    if (!mem) {
        perror("open_memstream");
        exit(2);
    }
    fflush(out);
    plan.tr = p;
    rec = r;
    stdout = mem;
    emit_trial(w, 0);
    stdout = out;
    fclose(mem);
    plan.tr = NULL;
    rec = NULL;
    return text;
}

/* emit_trial() on a record with known values. Every value differs from the
 * value of the field beside it, so a row that prints the wrong field fails. */
static void test_emit(void)
{
    int oldread = kernel_named("oldread");
    struct trial p = { .nwin = 2, .count = CS_READ };
    struct win win[3] = {
        { .k = oldread, .phase = PH_PRED, .widx = 0, .size = 4096, .bytes = 8192, .t_start = t_base_ns + 1000, .t_end = t_base_ns + 2000 },
        { .k = oldread, .phase = PH_TARGET, .widx = 0, .size = 4096, .bytes = 12288, .t_start = t_base_ns + 2100, .t_end = t_base_ns + 3100 },
        { .k = oldread, .phase = PH_TARGET, .widx = 1, .size = 4096, .bytes = 16384, .t_start = t_base_ns + 3400, .t_end = t_base_ns + 4400 },
    };
    /* three readings; the second window ran its counters for 50 of 100 ns */
    struct counts c[3] = { { .cpu_ns = 500, .enabled = 1000, .running = 1000, .val = { 70 } },
                           { .cpu_ns = 800, .enabled = 1100, .running = 1100, .val = { 75 } },
                           { .cpu_ns = 1400, .enabled = 1200, .running = 1150, .val = { 82 } } };
    struct trec r = { .win = win, .nw = 3, .cnt = c, .pg = { { 8192, 4096 }, { 8192, -1 } },
                      .vm = { { 1, 2, 3, 4 }, { 5, 6, 7, 8 } }, .cpu = { 10000, 13000 },
                      .nvcsw = { 5, 7 }, .nivcsw = { 10, 13 }, .state = CS_READ, .sink_ok = 0 };
    struct tw w;
    int nev = cfg.nev;
    char *text;

    memset(&w, 0, sizeof w);
    w.t.group_fd = 0; /* emit_trial() only asks whether a group is open */
    w.t.nopen = 1;
    cfg.nev = 1;
    text = emitted(&w, &p, &r);
    trial_check(has_line(text, "C,0,0,100,100,300,5") && has_line(text, "C,0,1,100,50,600,7"),
                "C rows hold the differences of two readings", 0);
    trial_check(has_line(text, "P,0,pre,8192,4096,1,2,3,4") && has_line(text, "P,0,post,8192,NA,5,6,7,8"),
                "P rows: pre holds the first snapshot and post the second", 0);
    trial_check(has_line(text, "E,0,3400,3000,2,3,100,300,0,read"),
                "E row holds wall time and CPU time and both switch counts and both gaps each in its own field", 0);
    trial_check(strstr(text, "\nX,0,coverage_na,") != NULL, "X row coverage_na when a snapshot has no huge-page value", 0);
    trial_check(strstr(text, "\nX,0,count_multiplexed,target window 1: running_ns 50 below enabled_ns 100\n") != NULL,
                "X row count_multiplexed names the window that ran its counters for less time", 0);
    trial_check(strstr(text, "\nX,0,sink,") != NULL, "X row sink when the sink check failed", 0);
    free(text);

    /* The same record without the three defects must print no X row. */
    r.pg[1].kb_huge = 4096;
    c[2].running = 1200;
    r.sink_ok = 1;
    text = emitted(&w, &p, &r);
    trial_check(strstr(text, "\nX,") == NULL && has_line(text, "E,0,3400,3000,2,3,100,300,1,read"),
                "no X row for a record without a defect", 0);
    free(text);
    cfg.nev = nev;
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
    test_trial();
    test_emit();
    printf("# failures=%d\n", failures);
    return failures ? 1 : 0;
}
