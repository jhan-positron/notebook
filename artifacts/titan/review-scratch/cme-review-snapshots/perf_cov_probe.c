#include "/home/jhan/workspace/titan/cache-perf/asimov/common.h"
static uint64_t sample[3 + PERF_N];
ssize_t read(int fd, void *buf, size_t len)
{
    (void)fd;
    if (len != sizeof sample) return -1;
    memcpy(buf, sample, len);
    return (ssize_t)len;
}
int main(void)
{
    struct perfgrp g = { .ok = 1 };
    uint64_t counts[PERF_N];
    const char *why;
    const uint64_t enabled[] = {100, 200, 300, 400};
    const uint64_t running[] = {50, 150, 250, 350};
    const int expected[] = {0, 1, 0, 1};
    for (int i = 0; i < 4; ++i) {
        sample[0] = PERF_N;
        sample[1] = enabled[i];
        sample[2] = running[i];
        sample[3] = 123;
        g.ctl_err = i == 2 ? EIO : 0;
        int valid = perf_read(&g, counts, &why);
        printf("case=%d valid=%d enabled_delta=%llu running_delta=%llu reason=%s\n", i, valid,
               (unsigned long long)g.t_enabled, (unsigned long long)g.t_running, why ? why : "none");
        if (valid != expected[i] || g.t_enabled != 100 || g.t_running != (i == 0 ? 50 : 100)) return 1;
    }
    puts("PASS: partial -> full -> ioctl failure -> full");
    return 0;
}
