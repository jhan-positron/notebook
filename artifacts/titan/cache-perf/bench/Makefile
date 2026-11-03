# make's built-in default CC is "cc"; use gcc unless CC comes from the
# environment or the command line.
ifeq ($(origin CC),default)
CC = gcc
endif
# -mcpu is avoided on purpose: gcc 14 on CRB resolves -mcpu=native to nothing.
# -fno-tree-loop-distribute-patterns keeps gcc from turning the write/copy
# loops into memset/memcpy calls.
CFLAGS = -O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11

# homelat uses AArch64 cache-maintenance instructions, so it is built only there.
ifeq ($(shell uname -m),aarch64)
all: latency bandwidth homelat
else
all: latency bandwidth
endif

latency: latency.c Makefile
	$(CC) $(CFLAGS) -o $@ $<

bandwidth: bandwidth.c Makefile
	$(CC) $(CFLAGS) -o $@ $<

homelat: homelat.c Makefile
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f latency bandwidth homelat

.PHONY: all clean
