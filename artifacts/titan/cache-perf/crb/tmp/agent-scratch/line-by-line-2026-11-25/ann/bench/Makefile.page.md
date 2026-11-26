## Short version: purpose

`Makefile` tells the build tool `make` how to compile the three benchmark programs of the folder `bench` with `gcc`. On an AArch64 machine such as CRB it builds `latency`, `bandwidth` and `homelat`. On every other machine it builds `latency` only.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **AArch64**: the 64-bit Arm instruction set. The command `uname -m` prints `aarch64` on such a machine.
- **`make`**: the build tool that reads this file. It runs the recipe of a rule when the target does not exist or is older than one of the files that the rule names.
- **Target**: the name before the colon of a rule. It is a file to build, or a name such as `all` or `clean`.
- **Recipe**: the command lines of a rule. Each of them starts with a tab.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **`latency`**: the program built from `latency.c`. It measures the load latency per cache level with one thread.
- **`bandwidth`**: the program built from `bandwidth.c`. It measures how fast threads read, write and copy memory.
- **`homelat`**: the program built from `homelat.c`. It measures the latency of the SLC from each core to each part of the SLC.
- **NEON intrinsics**: C functions that map to Arm vector instructions.

## Main flow

1. Choose the compiler: `gcc`, unless the caller has set the variable `CC` ({L1-5}).
2. Set the compiler options for all programs ({L6-9}).
3. Choose what the target `all` builds: three programs on AArch64, one program on every other machine ({L11-17}).
4. Give one rule per program. Each rule compiles one C file into one program ({L19-26}).
5. Give the target `clean`, which removes the three programs ({L28-29}).
6. Declare that `all` and `clean` are not files ({L31}).

## Behavior a reader must know

- Each of the three program rules names the `Makefile` as an input. So a change of the `Makefile` builds every program again.
- `-march=native` in {L9} fits the code to the processor of the build machine. The file `README.md` of this folder gives the build command for CRB: `make` in the folder `bench`.
- `make clean` removes all three program files, also on a machine where only `latency` was built. A file that does not exist causes no error.
- The file builds no test and starts no benchmark.
