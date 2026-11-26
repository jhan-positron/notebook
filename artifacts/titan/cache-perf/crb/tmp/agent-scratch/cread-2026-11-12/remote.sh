set -u
if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi
echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who | wc -l)"
D=$HOME/cache-perf/scratch-cread-20261113
mkdir -p $D && cd $D && cat > cread.c
echo "## gcc=$(gcc --version | head -1)"
echo "## sha256: $(sha256sum cread.c)"
CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"
echo "## CFLAGS=$CFLAGS"
taskset -c 0-119 gcc $CFLAGS -c -o cread.o cread.c 2>&1 && echo "## compile ok"
for f in k_cread k_cread_loop k_cread_plain k_cread_volatile; do
  echo "=== $f ==="
  objdump -d --no-show-raw-insn --disassemble=$f cread.o | sed -n '/>:$/,$p'
done
