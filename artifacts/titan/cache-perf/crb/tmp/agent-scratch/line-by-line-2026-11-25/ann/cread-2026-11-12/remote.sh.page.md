## Short version: purpose

`remote.sh` is the script of the compile check of `cread.c` on CRB. It stores the text that it gets on its standard input as `cread.c`, compiles that file without linking, and prints the machine code of the four candidate functions. It runs no benchmark and times nothing.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **`cread.c`**: the file of the same folder with four candidates for a read loop in C that only loads memory.
- **Compile check**: one compile of `cread.c` whose only purpose is the machine code that the compiler produces.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Object file**: the output of the compiler for one source file, before linking. It cannot be run by itself.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Record**: the text that this script prints to its standard output.
- **Work folder**: the folder `cache-perf/scratch-cread-20261113` under the home folder of the user on CRB.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists ({L2}).
2. Print the machine state: the host name, the time, the load averages and the number of logins ({L3}).
3. Go to the work folder and store the standard input as the file `cread.c` ({L4-5}).
4. Print the compiler version, the sha256 of `cread.c` and the compiler flags ({L6-9}).
5. Compile `cread.c` to the object file `cread.o` without linking, on the CPUs 0 to 119, and print `## compile ok` after a success ({L10}).
6. Print the machine-code listing of the four functions ({L11-14}).

## Behavior a reader must know

- The file holds no `ssh` command and no first line that names a shell. A caller must give its text to a shell on CRB and send the text of `cread.c` as the standard input ({L5}).
- The script prints everything to its standard output. It writes no result file. The caller decides where the record goes.
- It writes two files on CRB, both in the work folder: `cread.c` and `cread.o`. An older `cread.c` there is replaced.
- Exit status 3 when the marker file exists ({L2}). In every other case the exit status is the status of the last `sed` command ({L13}).
- The script has no `set -e`, so a failed step does not stop it. When the record holds no line `## compile ok`, the listings do not come from this compile.
- Only the compiler runs under `taskset -c 0-119` ({L10}). The script sets no CPU limit for its other commands.
- Nothing is timed, and no benchmark runs.
