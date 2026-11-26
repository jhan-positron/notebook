## Short version: purpose

`robsize.c` is the window test program: it measures how many filler instructions of one kind fit in the out-of-order window of one AArch64 core. It writes a loop at run time with two independent loads that miss the caches and N fillers after each load, times the loop for a list of N, and reports the N at which the time per pass steps from about one miss time to about two. The kinds whose name starts with `k_` use one loop body of a read kernel of `bwx12.c` as the unit, so they tell how many loop bodies, and so how many cache lines, one window covers.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **AArch64**: the 64-bit instruction set of Arm.
- **Out-of-order window**: the instructions that a core holds between fetch and retirement. By the README of this folder its size is limited by the reorder buffer, by the free physical registers and by the load queue.
- **Retire**: a core retires an instruction when the instruction and all instructions before it are finished. Only then does the instruction leave the window.
- **Filler**: an instruction placed between the two loads that miss the caches. It does not depend on those loads.
- **Kind**: one sort of filler. The table `kinds` holds 36 of them. The option `--kind` chooses.
- **N, unit**: N is the number of filler units after each of the two loads. For most kinds one unit is one instruction. For `iter256` it is 8 instructions, and for a kernel-body kind it is one whole loop body.
- **Kernel-body kind**: a kind whose name starts with `k_`. One unit of N is one loop body of a benchmark kernel of `bwx12.c`.
- **Chain**: a buffer of pointers that form one random cycle. Each load of a pointer gives the address of the next load, and each such load misses the caches.
- **Template**: an instruction that the assembler encodes at build time. The program copies its 4-byte word into the generated loop.
- **Pass**: one run through the generated loop: load A, N units, load B, N units, the counter step and the branch.
- **Miss time**: the time that one load takes when its data is not in a cache.
- **Scratch buffer**: 512 bytes that stay in the level 1 cache. The filler loads read its first 256 B. Two more cells of it point to themselves and serve the run without misses.
- **Filler cost (`hot_ns`)**: the time per pass of the same generated code when both loads hit the level 1 cache.
- **Plateau**: a flat part of the series of times over N. The low plateau is the mean of the first 3 points, the high plateau the mean of the last 3 points that are used.
- **Step position**: the N at which the series first crosses the midpoint between the two plateaus. The program prints it as `N_at_midpoint`.
- **`cbnz`**: the Arm instruction "compare and branch if not zero". It ends each pass of the generated loop.

## Main flow

1. `main` reads the options and checks them: `--cpu` is required and at most 119, `--reps` is 5 to 64, `--iters` is at least 200000, and every name of `--kind` must be in the table ({L651-699}).
2. Check the one change that the program makes to an instruction word: `patch_cbnz` puts the distance -300 into the `cbnz` template, and the result must be equal to the word that the assembler made for the same distance ({L701-707}).
3. Pin the program to the CPU of `--cpu` and test that it runs there ({L709-715}).
4. Build two pointer chains of `--mb` MiB each. `build_chain` writes every node, shuffles the nodes into one random cycle and turns the node numbers into addresses. Then read how much memory lies on huge pages ({L717-722}).
5. Prepare the scratch buffer and the code buffer, and print the head lines of the output ({L724-748}).
6. For each selected kind, in the order of the table, and for each N of its list: `emit_loop` writes the loop into the code buffer, and the buffer is made executable ({L750-778}).
7. Time the loop two times with `measure`: first without misses, 3 repetitions with the two cells that point to themselves, then with misses, `--reps` repetitions on the two chains. Print one data row for this N ({L780-793}).
8. After the last N of a kind, `report_step` finds the step in the series of the medians and in the series of the medians minus the filler cost, and prints one `# step` line for each ({L795-799}).

## Behavior a reader must know

- What is timed: one repetition is one call of the generated function with `--iters` passes. The clock `CLOCK_MONOTONIC` is read directly before and directly after the call ({L540-542}). The time per pass is the difference divided by the number of passes. The call holds the 7 instructions of the start code and the 5 of the end code once.
- What is not timed: the building of the chains, the writing of the loop, and the two warm-up calls of 20000 passes each ({L781}, {L784}).
- One pass does two loads of 8 bytes, one from each chain, and each loaded value is used: it is the address of the next load of the same chain. The program computes no byte count and no rate. Its result is ns per pass.
- Placement: the program pins itself to one CPU, and the chains are first written after that. By default the two chains take 2 times 1024 MiB. The program asks for transparent huge pages and prints a warning in its second head line when less than half of the chain memory is on them.
- The data row of an N holds the median and the minimum over the repetitions with misses, and the filler cost as the minimum of 3 repetitions without misses.
- The step search first cuts the series at the first N where the filler cost is above half of the low plateau of the run with misses. With fewer than 8 points left it prints `too few points` and no step position. A warning is added when the high plateau is below 1.4 times the low plateau.
- By the README of this folder, the window between load B and the next load A also holds the counter step and the branch. So the capacity is about the step position plus 2 to 3 instructions.
- The place in the two chains is never set back. Each N and each kind goes on where the one before it ended.
- For a kernel-body kind the unit differs from the real kernel in three points that the comment of {L203-214} lists: the loads hit the level 1 cache, the loop branch is never taken, and the accumulators have no start value.
- Exit statuses: 0 after all kinds. 2 after the help text: an unknown option, an option without a value, a value that is not a whole number, or a CPU number that is missing or below 0. 1 for every other stop: a CPU above 119, a value outside its allowed range, an unknown kind, a failed patch check, a failed system call.
- The output goes to the standard output. Lines that start with `#` are comments. Each data row is written out at once.
