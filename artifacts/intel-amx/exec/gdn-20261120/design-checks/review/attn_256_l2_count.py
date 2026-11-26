#!/usr/bin/env python3
"""Low case of the Part B prefill factor: the speedup of one page unit when a 256-wide page comes from L2.

A page of a 256-wide head holds 64 KiB of K and V (64 tokens x 256 values x 2 bytes, for K and for V).
It does not fit the 48 KiB L1 cache, so every visit of the page loads its 1,024 cache lines from L2.
Both kernels pay that cost. Only the instruction cycles differ.

Inputs (all est. counts with measured instruction costs):
- instruction cycles per page unit: design-checks/verify-cost/recount_tiles.out, lines "width 256"
  (AMX: 64 TDPBF16PS + 80 tile loads + 20 tile stores = 2,027.3 cycles with the instruction costs of design_numbers.py; AVX-512: 4,096 VDPBF16PS x 2.0 = 8,192 cycles);
- cycles per cache line from L2: 1.8 to 2.96 (design_numbers.py LINE_LO, LINE_HI);
- core clock under AMX on delphi-3b35: 2.396 GHz or 1.895 GHz, against 2.70 GHz for AVX-512 (bench/clock-probe*.txt).
"""
AMX = 64 * 16.17 + 80 * 8.38 + 20 * 16.1    # cycles of tile work per page unit (costs of design_numbers.py)
AVX = 4096 * 2.0                            # cycles of AVX-512 dot products per page unit
LINES = 64 * 256 * 2 * 2 // 64              # cache lines of K and V in one page
print(f"AMX {AMX:.1f} cycles, AVX-512 {AVX:.0f} cycles, {LINES} cache lines per page")
print(f"all data in L1: {AVX / AMX:.2f} times at an equal clock")
for line in (2.96, 1.8):
    mem = LINES * line
    equal = (AVX + mem) / (AMX + mem)
    print(f"{line} cycles per line: lines {mem:.0f} cycles; ({AVX:.0f} + {mem:.0f}) / ({AMX:.0f} + {mem:.0f}) = {equal:.2f} times at an equal clock; "
          f"{equal * 2.396 / 2.70:.2f} times at 2.396 GHz; {equal * 1.895 / 2.70:.2f} times at 1.895 GHz")
