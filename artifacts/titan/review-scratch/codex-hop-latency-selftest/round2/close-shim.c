#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int fclose(FILE *stream)
{
    int (*real_close)(FILE *) = dlsym(RTLD_NEXT, "fclose");
    char fdpath[64], target[4096];
    const char *wanted = getenv("MESHMAP_FAIL_CLOSE_PATH");
    snprintf(fdpath, sizeof fdpath, "/proc/self/fd/%d", fileno(stream));
    ssize_t len = readlink(fdpath, target, sizeof target - 1);
    if (len >= 0) target[len] = '\0';
    int inject = wanted && len >= 0 && !strcmp(wanted, target);
    int result = real_close(stream);
    if (inject) {
        errno = EIO;
        return EOF;
    }
    return result;
}
