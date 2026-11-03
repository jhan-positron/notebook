#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static uint64_t rng_state;
static uint64_t xorshift64(void){rng_state^=rng_state<<13;rng_state^=rng_state>>7;rng_state^=rng_state<<17;return rng_state;}
int main(int argc,char**argv){
  uint64_t n = strtoull(argv[1],0,10);
  uint64_t *a = malloc(n*8);
  rng_state = 0x9E3779B97F4A7C15ULL;
  for(uint64_t i=0;i<n;i++) a[i]=i;
  for(uint64_t i=n-1;i>0;i--){uint64_t j=xorshift64()%i;uint64_t t=a[i];a[i]=a[j];a[j]=t;}
  /* follow from 0, count steps until back at 0 */
  uint64_t p=0,len=0,seq=0,within_page=0;
  do{ uint64_t q=a[p]; if(q==p+1) seq++; if((q>>6)==(p>>6)) within_page++; p=q; len++; }while(p!=0);
  printf("n=%lu cycle_len=%lu %s seq_steps=%lu same_4K_page_steps=%lu (expect ~%lu)\n",n,len,len==n?"OK":"SHORT CYCLE",seq,within_page,(unsigned long)(n/ (n/64 ? n/64 : 1)));
  return 0;}
