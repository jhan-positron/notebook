CC      ?= gcc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra -g
CFLAGS_BW ?= -O3 -mavx512f -std=c11 -Wall -Wextra -g
LDFLAGS ?=
LIBS    ?= -lnuma

BINS = inspect_pages ptr_chase bw_avx512 bw_multi c2c_lat

all: $(BINS)

inspect_pages: inspect_pages.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBS)

ptr_chase: ptr_chase.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBS) -lm

bw_avx512: bw_avx512.c
	$(CC) $(CFLAGS_BW) $(LDFLAGS) -o $@ $< $(LIBS) -lm

bw_multi: bw_multi.c
	$(CC) $(CFLAGS_BW) $(LDFLAGS) -pthread -o $@ $< $(LIBS) -lm

c2c_lat: c2c_lat.c
	$(CC) $(CFLAGS) $(LDFLAGS) -pthread -o $@ $< $(LIBS) -lm

clean:
	rm -f $(BINS)

.PHONY: all clean
