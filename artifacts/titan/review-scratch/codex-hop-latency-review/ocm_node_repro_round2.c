#define main meshmap_original_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/meshmap.c"
#undef main

int main(void)
{
    const long physical_nodes[5] = {88, 160, 216, 288, 344};
    const long requested_nodes[5] = {344, 288, 216, 160, 88};
    char path[] = "/tmp/codex-hop-ocm-map-XXXXXX";
    int fd = mkstemp(path);
    if (fd < 0 || ftruncate(fd, 5 * 4096) != 0)
        return 2;
    for (int i = 0; i < 5; i++) {
        uint64_t marker = (uint64_t)physical_nodes[i];
        if (pwrite(fd, &marker, sizeof marker, i * 4096 + 56) != sizeof marker)
            return 2;
    }
    close(fd);
    out = stdout;
    cfg.nnodes = 5;
    cfg.lines = 64;
    memcpy(cfg.nodes, requested_nodes, sizeof requested_nodes);
    memcfg.ocm_dev = path;
    memcfg.ocm_base = 0;
    memcfg.ocm_stride = 4096;
    memcfg.ocm_size = 4096;
    int rc = map_ocm();
    if (rc)
        for (int i = 0; i < 5; i++)
            printf("row_node=%ld physical_region_node=%llu\n", cfg.nodes[i],
                   (unsigned long long)*(uint64_t *)(ocm_base[i] + 56));
    unlink(path);
    return rc ? 0 : 1;
}
