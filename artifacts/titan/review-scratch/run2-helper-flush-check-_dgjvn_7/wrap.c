#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
static int counter_fd = -1;
int __real_open(const char *, int, ...);
ssize_t __real_read(int, void *, size_t);
int __wrap_open(const char *path, int flags, ...) {
    const char *prefix = "/sys/bus/event_source/devices/reviewpmu";
    char mapped[1024];
    if (!strncmp(path, prefix, strlen(prefix))) {
        snprintf(mapped, sizeof mapped, "%s%s", getenv("REVIEW_SYSFS"), path + strlen(prefix));
        return __real_open(mapped, flags);
    }
    return __real_open(path, flags);
}
long __wrap_syscall(long n, ...) {
    if (n != __NR_perf_event_open) { errno = ENOSYS; return -1; }
    if (!strcmp(getenv("REVIEW_MODE"), "delay")) usleep(200000);
    counter_fd = __real_open("/dev/null", O_RDONLY | O_CLOEXEC);
    return counter_fd;
}
int __wrap_ioctl(int fd, unsigned long req, ...) {
    if (fd == counter_fd && req == PERF_EVENT_IOC_ENABLE && !strcmp(getenv("REVIEW_MODE"), "enablefail")) {
        errno = EIO; return -1;
    }
    return 0;
}
ssize_t __wrap_read(int fd, void *buf, size_t len) {
    if (fd == counter_fd && len == 3 * sizeof(uint64_t)) {
        if (!strcmp(getenv("REVIEW_MODE"), "delay")) usleep(200000);
        uint64_t v[3] = {42, 100, !strcmp(getenv("REVIEW_MODE"), "zero") ? 0 : 100};
        memcpy(buf, v, sizeof v); return sizeof v;
    }
    return __real_read(fd, buf, len);
}

pid_t __real_fork(void);
pid_t __wrap_fork(void) {
    if (!strcmp(getenv("REVIEW_MODE"), "forkfail")) { errno = EAGAIN; return -1; }
    return __real_fork();
}

int __real_fflush(FILE *f);
int __wrap_fflush(FILE *f) { usleep(200000); return __real_fflush(f); }
