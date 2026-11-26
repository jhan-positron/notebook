// Verifier: cross-check of the core-clock calibration with four dependent chains.
#define _GNU_SOURCE
#include <immintrin.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static inline uint64_t now_ns(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC_RAW,&ts);return (uint64_t)ts.tv_sec*1000000000ull+ts.tv_nsec;}
int main(int argc,char**argv){
  int cpu=argc>1?atoi(argv[1]):-1; if(cpu>=0){cpu_set_t s;CPU_ZERO(&s);CPU_SET(cpu,&s);sched_setaffinity(0,sizeof s,&s);}
  const long N=20000000;
  for(int rep=0;rep<3;rep++){
    double g_mul=0,g_add4=0,g_fma=0,g_ld=0;
    for(int r=0;r<5;r++){
      uint64_t x=3; uint64_t t0=now_ns();
      for(long i=0;i<N;i++){ __asm__ volatile("imul %1,%0" : "+r"(x) : "r"(0x9E3779B97F4A7C15ull)); }
      uint64_t t1=now_ns(); double g=3.0*N/(double)(t1-t0); if(g>g_mul) g_mul=g;
    }
    for(int r=0;r<5;r++){
      uint64_t x=3,y=5; uint64_t t0=now_ns();
      for(long i=0;i<N;i++){ __asm__ volatile("add %1,%0\n add %1,%0\n add %1,%0\n add %1,%0\n add %1,%0\n add %1,%0\n add %1,%0\n add %1,%0" : "+r"(x) : "r"(y)); }
      uint64_t t1=now_ns(); double g=8.0*N/(double)(t1-t0); if(g>g_add4) g_add4=g;
    }
    for(int r=0;r<5;r++){
      __m128d a=_mm_set_sd(1.0),b=_mm_set_sd(1.0000001),c=_mm_set_sd(1e-9); uint64_t t0=now_ns();
      for(long i=0;i<N;i++){ __asm__ volatile("vfmadd213sd %2,%1,%0" : "+x"(a) : "x"(b),"x"(c)); }
      uint64_t t1=now_ns(); double g=4.0*N/(double)(t1-t0); if(g>g_fma) g_fma=g;
    }
    for(int r=0;r<5;r++){
      void *p=&p; void *q=p; uint64_t t0=now_ns();
      for(long i=0;i<N;i++){ __asm__ volatile("mov (%0),%0" : "+r"(q)); }
      uint64_t t1=now_ns(); double g=4.0*N/(double)(t1-t0); if(g>g_ld) g_ld=g;
    }
    printf("rep %d: imul chain (3 cyc) %.3f GHz | 8 adds chain (8 cyc) %.3f GHz | scalar FMA chain (4 cyc) %.3f GHz | load chain (4 cyc) %.3f GHz\n",rep,g_mul,g_add4,g_fma,g_ld);
  }
  return 0;
}
