// amxprobe: LD_PRELOAD shim that reports the one system call the AMX runtime probe makes.
// tron's amx_attn.cpp asks Linux for AMX tile permission with
//   syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM /* 0x1023 */, XFEATURE_XTILEDATA /* 18 */)
// only after CPUID and XCR0 say AMX exists. Interposing libc's syscall() lets us see that
// request without ptrace (strace breaks the setuid fusermount3 helper runtron needs).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
typedef long (*syscall_fn)(long, ...);
static void note(const char* line) {
  fprintf(stderr, "[amxprobe] %s\n", line);
  const char* f = getenv("AMXPROBE_FILE");
  if (f) { FILE* o = fopen(f, "a"); if (o) { fprintf(o, "%s\n", line); fclose(o); } }
}
__attribute__((constructor)) static void amxprobe_loaded(void) {
  char b[128]; snprintf(b, sizeof b, "loaded in pid %d", (int)getpid()); note(b);
}
long syscall(long n, ...) {
  static syscall_fn real = 0;
  if (!real) real = (syscall_fn)dlsym(RTLD_NEXT, "syscall");
  va_list ap; va_start(ap, n);
  long a1 = va_arg(ap, long), a2 = va_arg(ap, long), a3 = va_arg(ap, long);
  long a4 = va_arg(ap, long), a5 = va_arg(ap, long), a6 = va_arg(ap, long);
  va_end(ap);
  long r = real(n, a1, a2, a3, a4, a5, a6);
  if (n == SYS_arch_prctl && a1 == 0x1023) {
    char b[160];
    snprintf(b, sizeof b, "arch_prctl(ARCH_REQ_XCOMP_PERM=0x1023, feature %ld) = %ld in pid %d", a2, r, (int)getpid());
    note(b);
  }
  return r;
}
