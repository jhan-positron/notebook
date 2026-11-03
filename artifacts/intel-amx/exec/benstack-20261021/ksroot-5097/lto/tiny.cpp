extern int ext(int);
static inline int sq(int x){return x*x;}
int f(int a){ for(int i=0;i<64;i++) a+=sq(i)+ext(i); return a; }
