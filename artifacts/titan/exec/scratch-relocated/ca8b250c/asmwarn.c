int main(void){ long q; long n = 3; __asm__ volatile("mov %[p], %[q]\n\t" : [q] "=&r"(q), [n] "+&r"(n) : [p] "r"(n)); return 0; }
