The forward-path test for the open item "Forward-path coverage" is pushed as commit `175b1837b9`, the new head. It changes `t/heterogeneous_scheduler_compile.cpp` only (+203, −7 lines). The description's sections "Builds and focused tests" and "Mutation checks" hold the results, and the open item is narrowed to "Conversion-call ordering".

**What the case does.** The fixture plugin of `t_heterogeneous_scheduler` (the test binary that runs the forward on a fake device) now stores the K rows of its 128-dimension operation through `save_k` when asked, and a variant of the plugin does not force hardware attention. Two forwards store rows 0 to 14 and then row 15 of one block. Under the software-scored variant the second forward returns with the block converted and every row readable with its stored value. Under the hardware-scored default the block stays row-major.

**Results on the Granite Rapids machine, 2026-10-13:**

| Configuration | `t_heterogeneous_scheduler` | The new case alone |
|---|---|---|
| option on (`TRON_K_VNNI=ON`) | 2855 assertions / 4 cases | 72 / 1 |
| option on, `convert_pending_k_blocks()` removed from the forward (mutation) | | 71 / 72, the block check fails: 0 converted blocks against 1 |
| option on, source restored | | 72 / 1 |
| option off | 2855 / 4 | 72 / 1 |

A first version of the case set `USE_HW_ATTN=0` and failed: tron reads that variable once per process, so the setting had no effect after earlier cases. The plugin variant replaced it. The step-4 checks of the stack (the 22-cell and 38-cell syntax matrices, clang-format 19.1.7, `git diff --check`) pass at the new head. No mutation checks the conversion call's ordering after the staging join. That remains the open item.
