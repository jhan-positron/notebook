#include <errno.h>
#include <sys/types.h>
pid_t fork(void) { errno = EAGAIN; return -1; }
