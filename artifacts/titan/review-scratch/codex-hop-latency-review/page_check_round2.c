#define main meshmap_original_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/meshmap.c"
#undef main
int main(int argc, char **argv)
{
    (void)argv;
    out = stdout;
    memcfg.no_hugetlb = 1;
    memcfg.no_thp = argc > 1;
    alloc_dram(&dram, HUGE_BYTES);
    fill_buf(&dram, 42);
    if (argc > 2) dram.backing = "thp"; /* accepted hint with no allocated huge page */
    check_one_page();
    read_pagemap();
    return 0;
}
