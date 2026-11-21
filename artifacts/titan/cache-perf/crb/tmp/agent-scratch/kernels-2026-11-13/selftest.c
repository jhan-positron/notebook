/*
 * selftest.c - checks what the six kernels of bandwidth.c do to memory.
 * It includes bandwidth.c itself, so it tests the code that the benchmark runs.
 * Every buffer ends at a page that cannot be read or written (PROT_NONE) and
 * starts after one. A kernel that touches a byte within one page before the
 * buffer or within one page after it dies with SIGSEGV. The line "call,..."
 * printed before each kernel call names the kernel that died.
 * Exit status 0 means every check passed.
 *
 * Limits. The test sees only memory contents and faults. It cannot see
 * whether a read kernel loads every byte, or in which order a copy kernel
 * loads and stores: the objdump listing is the evidence for those. It does
 * not check that a kernel preserves the callee-saved registers d8-d15.
 */
#define main bandwidth_main
#include "bandwidth.c"
#undef main

static long page;
static int failures;

/* n words whose first byte follows a PROT_NONE page and whose last byte
 * precedes one. n * 8 must be a multiple of the page size. */
static uint64_t *guarded(size_t n)
{
    size_t len = n * 8;
    uint8_t *raw = mmap(NULL, len + 2 * (size_t)page, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED || mprotect(raw + page, len, PROT_READ | PROT_WRITE) != 0) {
        perror("guarded");
        exit(2);
    }
    return (uint64_t *)(raw + page);
}

static uint64_t pattern(size_t i, uint64_t salt)
{
    return (i + 1) * 0x9E3779B97F4A7C15ULL ^ salt;
}

static void calling(const char *kernel, size_t n)
{
    printf("call,%s,%zu\n", kernel, n * 8);
}

static void check(int ok, const char *kernel, const char *what, size_t n)
{
    printf("%s,%s,%zu,%s\n", kernel, what, n * 8, ok ? "pass" : "FAIL");
    if (!ok)
        failures++;
}

typedef void (*read_fn)(const uint64_t *, size_t);
typedef void (*write_fn)(uint64_t *, size_t, uint64_t);
typedef void (*copy_fn)(uint64_t *restrict, const uint64_t *restrict, size_t);

static void test_size(size_t n, const char *rn, read_fn rd, const char *wn, write_fn wr, const char *cn, copy_fn cp)
{
    uint64_t *a = guarded(n), *b = guarded(n);
    int ok;

    /* read: must leave every word as it was (and must not fault) */
    for (size_t i = 0; i < n; i++)
        a[i] = pattern(i, 1);
    calling(rn, n);
    rd(a, n);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= a[i] == pattern(i, 1);
    check(ok, rn, "buffer unchanged", n);

    /* write: every word must hold v afterwards; no word may keep the old pattern */
    uint64_t v = 0xA5A5F00D12345678ULL + n;
    calling(wn, n);
    wr(a, n, v);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= a[i] == v;
    check(ok, wn, "every word equals v", n);

    /* copy: destination must equal source word for word; source unchanged.
     * Every word of the source is different, so a store of the wrong vector
     * or to the wrong offset is seen. */
    for (size_t i = 0; i < n; i++) {
        a[i] = pattern(i, 2);
        b[i] = 0;
    }
    calling(cn, n);
    cp(b, a, n);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= b[i] == pattern(i, 2);
    check(ok, cn, "destination equals source", n);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= a[i] == pattern(i, 2);
    check(ok, cn, "source unchanged", n);

    munmap((uint8_t *)a - page, n * 8 + 2 * (size_t)page);
    munmap((uint8_t *)b - page, n * 8 + 2 * (size_t)page);
}

/* One iteration (256 B = 32 words) at word offset off inside one guarded
 * page. Words of the page outside the 256 B must keep their old value. */
static void test_block(size_t off, const char *rn, read_fn rd, const char *wn, write_fn wr, const char *cn, copy_fn cp)
{
    size_t n = (size_t)page / 8, m = 32;
    uint64_t *a = guarded(n), *b = guarded(n);
    int ok;

    for (size_t i = 0; i < n; i++)
        a[i] = pattern(i, 3);
    calling(rn, m);
    rd(a + off, m);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= a[i] == pattern(i, 3);
    check(ok, rn, off ? "256 B at page end: page unchanged" : "256 B at page start: page unchanged", m);

    for (size_t i = 0; i < n; i++)
        b[i] = pattern(i, 4);
    calling(cn, m);
    cp(b + off, a + off, m);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= b[i] == (i >= off && i < off + m ? pattern(i, 3) : pattern(i, 4));
    check(ok, cn, off ? "256 B at page end: only those 256 B copied" : "256 B at page start: only those 256 B copied", m);

    uint64_t v = 0x0123456789ABCDEFULL;
    calling(wn, m);
    wr(a + off, m, v);
    ok = 1;
    for (size_t i = 0; i < n; i++)
        ok &= a[i] == (i >= off && i < off + m ? v : pattern(i, 3));
    check(ok, wn, off ? "256 B at page end: only those 256 B written" : "256 B at page start: only those 256 B written", m);

    munmap((uint8_t *)a - page, n * 8 + 2 * (size_t)page);
    munmap((uint8_t *)b - page, n * 8 + 2 * (size_t)page);
}

int main(void)
{
    setvbuf(stdout, NULL, _IOLBF, 0); /* a kernel that faults must not take the earlier lines with it */
    page = sysconf(_SC_PAGESIZE);
    printf("# selftest: page_bytes=%ld; columns: kernel,check,bytes,result\n", page);
    if (page % 256 != 0) {
        fprintf(stderr, "page size is not a multiple of 256\n");
        return 2;
    }
    /* whole buffers of 1 page, 3 pages and 1 MiB */
    size_t words[] = { (size_t)page / 8, 3 * (size_t)page / 8, (1UL << 20) / 8 };
    for (size_t i = 0; i < sizeof words / sizeof words[0]; i++) {
        test_size(words[i], "read", k_read, "write", k_write, "copy", k_copy);
        test_size(words[i], "asmread", k_asmread, "asmwrite", k_asmwrite, "asmcopy", k_asmcopy);
    }
    /* one iteration: at the start of a page (guard before it) and at the end (guard after it) */
    size_t offs[] = { 0, (size_t)page / 8 - 32 };
    for (size_t i = 0; i < 2; i++) {
        test_block(offs[i], "read", k_read, "write", k_write, "copy", k_copy);
        test_block(offs[i], "asmread", k_asmread, "asmwrite", k_asmwrite, "asmcopy", k_asmcopy);
    }
    printf("# failures=%d\n", failures);
    return failures ? 1 : 0;
}
