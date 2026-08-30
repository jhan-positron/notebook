### The picture

AMX works on **tiles**: fixed-size registers configured here as **16 rows x 64 bytes**. Three kernels produce result tiles; the question is where each one *stores* them and therefore how big the caller's output buffer has to be.

```
kernel                  where TILESTORED writes                caller must provide
----------------------  -------------------------------------  ---------------------------
weights_times_v_128x4   straight into the caller's `o`          16 rows x 128 fp32  (8 KB)
qk_mirror_128x4         straight into the caller's `s`          16 rows x  64 fp32  (4 KB)
qk_canonical_128x4      into its OWN local buffer, then         `s` with only 4 rows
                        transposes and copies rows 0..3 to `s`  (row stride: caller's choice)
```

What one stored tile looks like at width 4 (4 query heads = 4 useful rows):

```
16-row buffer (correct)            4-row buffer (the bug the Note warns about)
row  0 #### result                 row 0 #### result
row  1 #### result                 row 1 #### result
row  2 #### result                 row 2 #### result
row  3 #### result                 row 3 #### result
row  4 ---- zeros                  rows 4..15 are written PAST THE END of the
 ...   ---- zeros                  buffer: memory after it is overwritten,
row 15 ---- zeros                  and nothing reports an error ("silent overrun")
```

### Sentence by sentence

| the comment says | in plain words |
|---|---|
| "TILESTORED always writes ALL 16 configured tile rows, no matter how many carry real data: a width-4 result still stores 16 rows." | The tile-store instruction has no "store only 4 rows" mode. If the tile is configured as 16 rows, 16 rows land in memory, even when only 4 of them mean anything. |
| "The two kernels that store a tile straight into the caller's buffer - `weights_times_v_128x4` (`o`) and `qk_mirror_128x4` (`s`) - therefore need 16-row buffers" | Two of the three kernels point the store instruction directly at the memory the caller passed in. For those two, the caller's buffer must have room for 16 rows. |
| "a "4 x N" buffer is a silent overrun (rows 4..15 land past its end)." | If a caller sizes the buffer for the 4 real rows only, rows 4..15 are written beyond it. No crash, no error - just corrupted memory somewhere else. |
| "Rows 4..15 of those buffers receive zeros (the A-operand rows 4..15 are zero padding)" | Why those extra rows are zeros and not garbage: the tile multiply computes C = A.B row by row, so output row i comes from row i of the left-hand input (the "A operand"). Rows 4..15 of A are padding that is kept at zero (the P rows in `weights_times_v_128x4`, the packed Q rows in the mirror kernel), so rows 4..15 of the output are zero. This is also why 35b3f3cae made "padding must already be zero" a precondition of the pack functions. |
| "only rows 0..3 are the result." | The caller reads rows 0..3 and ignores the rest. |
| "`qk_canonical_128x4` stores its tiles into a kernel-local buffer, transposes, and writes exactly 4 rows x 64 columns into `s`" | The third kernel is different: it computes the *transposed* scores (64 token rows x 16 columns) into a scratch buffer that lives inside the kernel (`s_transposed`), then flips them and copies only the 4 real rows into the caller's `s`. The 16-row store happens on the kernel's own memory, not the caller's. |
| "so `s` needs only 4 rows (s[4][s_stride_floats])." | For this kernel a 4-row `s` is correct - which is exactly what `t_amx_numerics` passes it (`s_amx[NQ][PAGE]`, NQ = 4). `s_stride_floats` is the distance between consecutive rows of `s`, chosen by the caller (both current callers use 64). |

### Why the sentence was changed

The old Note said "**every** output buffer handed to a kernel below must be sized for 16 rows." That was false for `qk_canonical_128x4`, and it made the test's correct 4-row buffer look like a bug (R1-10). The new text names the two kernels the rule applies to and states the exception.

### Glossary

- **TILESTORED** - the AMX instruction that copies a tile register to memory (`_tile_stored` in the code).
- **tile** - one of 8 AMX registers; configured here as 16 rows x 64 bytes (16 fp32 or 32 bf16 per row).
- **A operand / B operand** - the two inputs of the tile multiply `C += A.B`; output rows follow A's rows, output columns follow B's columns.
- **width-4** - one KV head shared by 4 query heads (GQA), so a decode step has 4 useful query rows.
- **padding** - rows or columns present only to fill the tile; must be zero so they do not disturb the result.
- **row stride** - the number of elements between the start of one row and the next in a buffer.
