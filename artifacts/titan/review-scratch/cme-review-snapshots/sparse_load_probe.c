#define main latency_cli_main
#include "latency.c"
#undef main
int main(void) {
    void *nodes[8];
    for (int i=0; i<8; ++i) nodes[i]=&nodes[(i+1)%8];
    use_cme=0;
    for (uint64_t n=2; n<=8; n+=2) {
        void *got=chase(&nodes[0],n);
        printf("requested=%llu actual_end_node=%td expected_end_node=%llu\n",(unsigned long long)n,(void **)got-nodes,(unsigned long long)(n%8));
    }
    return 0;
}
