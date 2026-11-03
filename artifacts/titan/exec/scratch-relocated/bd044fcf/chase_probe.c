/* host probe for R12: the core chase loop must execute exactly the requested hop count */
#define main latency_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/latency.c"
#undef main
int main(void)
{
    void *ring[8];
    uint64_t cell[8];
    for (int i = 0; i < 8; i++) ring[i] = &cell[i];
    for (int i = 0; i < 8; i++) cell[i] = (uint64_t)(uintptr_t)ring[(i + 1) % 8];
    int fails = 0;
    for (uint64_t k = 0; k <= 8; k++) {
        void *end = chase(ring[0], k);
        if (end != ring[k % 8]) { fails++; printf("FAIL: %llu hops ended at node %ld\n", (unsigned long long)k, (long)((uint64_t *)end - cell)); }
    }
    for (uint64_t k = 9; k <= 100; k += 7) {
        void *end = chase(ring[0], k);
        if (end != ring[k % 8]) { fails++; printf("FAIL: %llu hops ended at node %ld\n", (unsigned long long)k, (long)((uint64_t *)end - cell)); }
    }
    printf("%s\n", fails ? "FAIL" : "PASS: hop counts 0..8 and 9..100 step 7 end at the expected node");
    return fails ? 1 : 0;
}
