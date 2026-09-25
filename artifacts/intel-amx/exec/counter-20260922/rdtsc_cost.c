#include <stdio.h>
#include <stdint.h>
#include <x86intrin.h>
#include <time.h>
static inline uint64_t ns(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
int main(){ const long N=100000000; volatile uint64_t sink=0;
 uint64_t t0=ns(); for(long i=0;i<N;i++) sink+=__rdtsc(); uint64_t t1=ns();
 printf("rdtsc: %.2f ns per read (%ld reads)\n",(double)(t1-t0)/N,N);
 unsigned aux; t0=ns(); for(long i=0;i<N;i++) sink+=__rdtscp(&aux); t1=ns();
 printf("rdtscp: %.2f ns per read\n",(double)(t1-t0)/N);
 t0=ns(); for(long i=0;i<N;i++){ _mm_lfence(); sink+=__rdtsc(); } t1=ns();
 printf("lfence+rdtsc: %.2f ns per read\n",(double)(t1-t0)/N);
 return 0;}
