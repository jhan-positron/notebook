| Term | Meaning |
|---|---|
| the cache | h/tron/models/kv_cache.hpp: `struct page` (one 64-token KV page) and `struct book` (the pages of one model instance) |
| the option | the CMake option TRON_K_VNNI. When it is on, the K cache of 128-dimension heads is stored in the AMX VNNI layout |
| a VNNI slot | a K storage slot that uses that layout. A row-major slot stores one token's row after another |
| AMX | Intel tile-matrix instructions. TRON_AMX_DISABLE=1 (the kill switch) turns the AMX attention path off at run time |
| the kernel | qk_vnni_128x4, the AMX QK kernel over a VNNI page (kernels in src/tron/kernels/amx_attn.cpp) |
| the reader | k_vnni::qk_group, the AVX-512 scoring loop over the VNNI plane (h/tron/kernels/k_vnni.hpp) |
| the syntax matrix | 22 compiler runs (two generated trees x the option off/on x five test files, plus the AMX kernel file) that parse and instantiate the code without linking or running it |
| 3bda | delphi-3bda, the Intel server where the builds and unit tests run |
