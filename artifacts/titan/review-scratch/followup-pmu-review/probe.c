#define syscall mock_syscall
#define main latency_program_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/latency.c"
#undef main
#undef syscall
#include <stdarg.h>
#include <assert.h>
static uint64_t rejected;
static unsigned seen_second;
static unsigned attempts;
long mock_syscall(long number, ...)
{
    assert(number == __NR_perf_event_open);
    va_list ap;
    va_start(ap, number);
    struct perf_event_attr *a = va_arg(ap, struct perf_event_attr *);
    va_end(ap);
    attempts++;
    if (a->config == 0x81BD || a->config == 0x32B2) seen_second++;
    if (a->config == rejected) { errno = EINVAL; return -1; }
    return (long)(100 + attempts);
}
int main(int argc, char **argv)
{
    int cme = argc > 1 && !strcmp(argv[1], "cme");
    rejected = cme ? 0x3280 : 0x81BC;
    if (cme) perf_open_cme(&pg); else perf_open(&pg);
    fprintf(stderr, "first optional fails: ok=%d n=%d attempts=%u second_attempted=%u\n", pg.ok, pg.n, attempts, seen_second);
    printf("# latency: cme=%d\n", cme);
    printf("mem,size_bytes,mode,rep,loads,ns_per_load");
    for (int i = 0; i < PERF_N; i++) printf(",%s_per_load", pg.names[i]);
    printf(",perf_cov\n");
    pg.t_enabled = pg.t_running = 100;
    const uint64_t counters[PERF_N] = { 400, 100, 200, 300, 400, 500 };
    printf("dram,4096,repeat,0,100,2.000");
    print_counters(counters, 100, 1, NULL);
}
