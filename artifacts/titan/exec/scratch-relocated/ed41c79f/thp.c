#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
int main(void){
    size_t len = 64UL<<20, huge = 2UL<<20;
    uint8_t *raw = mmap(NULL, len+huge, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    uint8_t *p = (uint8_t*)(((uintptr_t)raw + huge-1) & ~(uintptr_t)(huge-1));
    int r = madvise(p, len, MADV_HUGEPAGE); printf("madvise=%d\n", r);
    memset(p, 1, len);
    FILE *f = fopen("/proc/self/smaps", "r"); char line[256]; int in=0;
    while (fgets(line, sizeof line, f)) {
        unsigned long lo, hi;
        if (sscanf(line, "%lx-%lx", &lo, &hi) == 2) in = (lo <= (unsigned long)p && (unsigned long)p < hi);
        else if (in && (strstr(line,"AnonHuge")||strstr(line,"THPeligible")||strstr(line,"VmFlags")||strstr(line,"Size:"))) fputs(line, stdout);
    }
    return 0;
}
