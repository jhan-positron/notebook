#define main latency_program_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/latency.c"
#undef main
#include <assert.h>

int main(void)
{
    int cases = 0;
    for (int segments = 1; segments <= 5; segments += 4) {
        struct buf b = { .kind = MEM_DRAM, .nseg = segments,
                         .bytes = segments * 262144ULL, .seg_bytes = 262144,
                         .backing = "test" };
        for (int s = 0; s < segments; s++) {
            b.seg[s].base = calloc(1, 262144);
            b.seg[s].bytes = 262144;
            assert(b.seg[s].base);
        }
        for (sparse = 0; sparse <= 2; sparse++) {
            for (seq = 0; seq <= 1; seq++) {
                uint64_t n = b.bytes / (sparse ? 4096 : 64);
                for (int slot = 0; slot < 8; slot++)
                    build_cycle(&b, n, slot, 0x9E3779B97F4A7C15ULL * (slot + 1) + 12345);
                for (int slot = 0; slot < 8; slot++) {
                    unsigned char *visited = calloc(n, 1);
                    void *start = chain_start(&b, slot), *p = start;
                    for (uint64_t j = 0; j < n; j++) {
                        uint64_t member = n;
                        for (int s = 0; s < segments; s++) {
                            uintptr_t off = (uintptr_t)p - (uintptr_t)b.seg[s].base;
                            if (off < b.seg[s].bytes) {
                                member = (s * b.seg_bytes + off) / (sparse ? 4096 : 64);
                                assert(off % 64 == (uint64_t)slot * 8);
                            }
                        }
                        assert(member < n && !visited[member]);
                        visited[member] = 1;
                        p = *(void **)p;
                    }
                    assert(p == start);
                    assert(chase(start, n) == start);
                    free(visited);
                    cases++;
                }
            }
        }
        for (int s = 0; s < segments; s++) free(b.seg[s].base);
    }
    printf("PASS: %d full-cycle cases, all members visited once\n", cases);
}
