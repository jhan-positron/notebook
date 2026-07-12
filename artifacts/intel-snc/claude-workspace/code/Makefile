# Self-contained build for enable-SNC3 project.
# Outputs binaries to ../bin/.
#
#   make         # build all into ../bin/
#   make clean   # remove binaries
#
# Deps: gcc, libnuma-dev. bw_* require AVX-512 (-mavx512f); any Xeon 6 has it.

CC        ?= gcc
CFLAGS    ?= -O2 -std=c11 -Wall -Wextra -g
CFLAGS_BW ?= -O3 -mavx512f -std=c11 -Wall -Wextra -g
LIBS      ?= -lnuma
BIN       := ../bin

BINS = $(BIN)/inspect_pages $(BIN)/ptr_chase $(BIN)/bw_avx512 $(BIN)/bw_multi $(BIN)/c2c_lat

all: $(BIN) $(BINS)
$(BIN):
	mkdir -p $(BIN)
$(BIN)/inspect_pages: inspect_pages.c | $(BIN)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)
$(BIN)/ptr_chase: ptr_chase.c | $(BIN)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS) -lm
$(BIN)/bw_avx512: bw_avx512.c | $(BIN)
	$(CC) $(CFLAGS_BW) -o $@ $< $(LIBS) -lm
$(BIN)/bw_multi: bw_multi.c | $(BIN)
	$(CC) $(CFLAGS_BW) -pthread -o $@ $< $(LIBS) -lm
$(BIN)/c2c_lat: c2c_lat.c | $(BIN)
	$(CC) $(CFLAGS) -pthread -o $@ $< $(LIBS) -lm
clean:
	rm -f $(BINS)
.PHONY: all clean
