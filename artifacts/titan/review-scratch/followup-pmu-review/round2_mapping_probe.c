#define syscall mock_syscall
#define read mock_read
#define main latency_program_main
#include "/home/jhan/workspace/titan/cache-perf/asimov/latency.c"
#undef main
#undef read
#undef syscall
#include <stdarg.h>
#include <assert.h>
static unsigned fail_mask, attempts, n_kept;
static uint64_t kept[PERF_N];
static int reading_mode;
static uint64_t enabled, running;
long mock_syscall(long number, ...)
{
    assert(number == __NR_perf_event_open);
    va_list ap; va_start(ap, number);
    struct perf_event_attr *a = va_arg(ap, struct perf_event_attr *); va_end(ap);
    (void)a;
    unsigned slot=attempts++;
    if (slot >= PERF_REQUIRED && (fail_mask & (1U << (slot-PERF_REQUIRED)))) { errno=EINVAL; return -1; }
    kept[n_kept++] = (slot+1)*100;
    return 100+slot;
}
ssize_t mock_read(int fd, void *buffer, size_t count)
{
    (void)fd;
    uint64_t *v=buffer;
    size_t size=(3+n_kept)*sizeof *v;
    assert(count==size);
    v[0]=n_kept; v[1]=enabled; v[2]=running;
    for(unsigned i=0;i<n_kept;i++) v[3+i]=kept[i];
    if(reading_mode==1)return (ssize_t)size-8;
    if(reading_mode==2)v[0]++;
    return (ssize_t)size;
}
int main(void)
{
    unsigned total=0;
    for(int set=0;set<3;set++)for(fail_mask=0;fail_mask<8;fail_mask++){
        attempts=n_kept=0;reading_mode=0;enabled=running=1000;
        if(set==0)perf_open(&pg);else if(set==1)perf_open_cme(&pg);else perf_open_tlb(&pg);
        assert(pg.ok && attempts==PERF_N && pg.n==(int)n_kept);
        uint64_t out[PERF_N];const char *why;
        assert(perf_read(&pg,out,&why)==1 && why==NULL);
        for(int i=0;i<PERF_N;i++){
            int absent=i>=PERF_REQUIRED && (fail_mask & (1U<<(i-PERF_REQUIRED)));
            assert(perf_have(&pg,i)==!absent);
            assert(out[i]==(absent?0:(unsigned)(i+1)*100));
        }
        char p[128];snprintf(p,sizeof p,"/tmp/followup-pmu-review/round2-set%d-mask%u.csv",set,fail_mask);
        FILE *capture=freopen(p,"w",stdout);assert(capture);
        printf("# latency: cme=%d\n",set==1);
        printf("mem,size_bytes,mode,rep,loads,ns_per_load");
        for(int i=0;i<PERF_N;i++)printf(",%s_per_load",pg.names[i]);
        printf(",perf_cov\n");
        printf("dram,4096,repeat,0,100,2.000");print_counters(out,100,1,NULL);
        printf("dram,4096,repeat,1,100,2.100");print_counters(out,100,0,"multiplexed");
        printf("dram,4096,best,-,-,2.000\n");
        enabled=2000;running=1500;assert(!perf_read(&pg,out,&why));assert(!strcmp(why,"multiplexed"));
        enabled=3000;running=2500;assert(perf_read(&pg,out,&why));
        reading_mode=1;assert(!perf_read(&pg,out,&why));assert(!strcmp(why,"short read"));
        reading_mode=2;assert(!perf_read(&pg,out,&why));assert(!strcmp(why,"wrong event count"));
        reading_mode=0;enabled=4000;running=3500;pg.ctl_err=EIO;assert(!perf_read(&pg,out,&why));assert(!strcmp(why,"counter ioctl failed"));
        total++;
    }
    fprintf(stderr,"PASS: %u event-set/mask cases, compact count mapping, printer output, interval recovery, short read, count mismatch and ioctl error\n",total);
}
