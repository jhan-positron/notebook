# `remote.sh` explained, line by line

- Source file: `cread-2026-11-12/remote.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 14 lines, 734 bytes).
- sha256 of the source when this page was built: `0118068810bc1bdd2cef541cdea6835a30fb66166644fc1614dc01ec0401385f`.

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

1. Stop when the marker file exists (line 2).
2. Print the machine state: the host name, the time, the load averages and the number of logins (line 3).
3. Go to the work folder and store the standard input as the file `cread.c` (lines 4 to 5).
4. Print the compiler version, the sha256 of `cread.c` and the compiler flags (lines 6 to 9).
5. Compile `cread.c` to the object file `cread.o` without linking, on the CPUs 0 to 119, and print `## compile ok` after a success (line 10).
6. Print the machine-code listing of the four functions (lines 11 to 14).

## Behavior a reader must know

- The file holds no `ssh` command and no first line that names a shell. A caller must give its text to a shell on CRB and send the text of `cread.c` as the standard input (line 5).
- The script prints everything to its standard output. It writes no result file. The caller decides where the record goes.
- It writes two files on CRB, both in the work folder: `cread.c` and `cread.o`. An older `cread.c` there is replaced.
- Exit status 3 when the marker file exists (line 2). In every other case the exit status is the status of the last `sed` command (line 13).
- The script has no `set -e`, so a failed step does not stop it. When the record holds no line `## compile ok`, the listings do not come from this compile.
- Only the compiler runs under `taskset -c 0-119` (line 10). The script sets no CPU limit for its other commands.
- Nothing is timed, and no benchmark runs.

## Source and explanation, line by line

- Text shown: the file `cread-2026-11-12/remote.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (14 lines, 734 bytes, sha256 `0118068810bc1bdd2cef541cdea6835a30fb66166644fc1614dc01ec0401385f`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `set -u` | `set -u`: the shell stops when the script uses a variable that was never set. The file has no first line that names a shell, and it has no `set -e`. So a failed command alone does not stop it. |
| 2 | `if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi` | Marker check. When the marker file `/tmp/positron-perf.RUNNING` exists (`-e`), the script prints `RUNNING file present: stop` to the standard output and ends with exit status 3. It has written no file at this point. |
| 3 | `echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who \| wc -l)"` | Prints the first line of the record: the host name (`hostname`), the UTC date and time (`date -u`), the load averages and the number of logins. `cut -d' ' -f1-3 /proc/loadavg` takes the first three fields of that file: the load averages of the last 1, 5 and 15 minutes. `who` prints one line per login, and `wc -l` counts the lines. |
| 4 | `D=$HOME/cache-perf/scratch-cread-20261113` | `D`: the work folder `cache-perf/scratch-cread-20261113` under the home folder of the user. |
| 5 | `mkdir -p $D && cd $D && cat > cread.c` | Three steps, joined with `&&`: a step runs only when the step before it succeeded. `mkdir -p` creates the work folder and gives no error when it exists. `cd` goes into it. `cat` then copies the standard input of the script into the file `cread.c` (`>` replaces an older file of that name). So the caller must send the text of `cread.c` as the standard input. When `mkdir` or `cd` fails, no file is written, and the script still goes on. |
| 6 | `echo "## gcc=$(gcc --version \| head -1)"` | Prints the compiler version. `head -1` keeps the first line of the output of `gcc --version`. |
| 7 | `echo "## sha256: $(sha256sum cread.c)"` | Prints the sha256 and the name of the file `cread.c` that line 5 wrote. A reader can compare this value with the sha256 of the local file. |
| 8 | `CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"` | `CFLAGS`: the compiler flags. `-O3`: a high optimization level. `-march=native`: the compiler may use every instruction of the machine that it runs on. `-fno-tree-loop-distribute-patterns`: gcc must not turn a loop into a call of `memset` or `memcpy`. `-pthread`: build with the POSIX thread library. `-Wall -Wextra`: print more warnings. `-std=gnu11`: the C standard of 2011 with the GNU extensions. The script `run_cread.sh` of the same folder sets the same flags. |
| 9 | `echo "## CFLAGS=$CFLAGS"` | Prints the compiler flags. |
| 10 | `taskset -c 0-119 gcc $CFLAGS -c -o cread.o cread.c 2>&1 && echo "## compile ok"` | Compiles `cread.c` to the object file `cread.o`. `-c` means compile only: gcc does not link, so no program is made. `taskset -c 0-119` allows the compiler to run on the CPUs 0 to 119 only. `$CFLAGS` has no quotes, so the shell splits it into the single flags. `2>&1` sends the error output of the compiler, with its warnings and errors, to the standard output. When the compile succeeds, the script prints `## compile ok`. A failed compile does not stop the script. |
| 11 | `for f in k_cread k_cread_loop k_cread_plain k_cread_volatile; do` | Loop over the names of the four functions of `cread.c`: `k_cread`, `k_cread_loop`, `k_cread_plain` and `k_cread_volatile`. |
| 12 | `  echo "=== $f ==="` | Prints a heading with the function name, for example `=== k_cread ===`. |
| 13 | `  objdump -d --no-show-raw-insn --disassemble=$f cread.o \| sed -n '/>:$/,$p'` | Prints the machine code of the function from the object file `cread.o`. `objdump -d` turns machine code into text. `--no-show-raw-insn` leaves out the instruction bytes. `--disassemble=$f` limits the output to the function `f`. The pipe gives the text to `sed -n '/>:$/,$p'`. It prints from the first line that ends with `>:`, which is the label line of the function, to the last line of the text. The lines before the label are dropped. |
| 14 | `done` | Ends the loop of line 11. The script ends here. Its exit status is the status of the last `sed` command. |
