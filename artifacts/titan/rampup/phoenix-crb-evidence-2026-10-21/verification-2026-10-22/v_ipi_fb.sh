export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0
date -u
col() { awk -v c="CPU$1" -v n="$2" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1==n{print $(k+1)}' /proc/interrupts; }
echo "=== feedback_ctrs IPI test (cpu125 target) ==="
a=$(col 125 IPI1:); taskset -c 0 bash -c 'for i in $(seq 100); do cat /sys/devices/system/cpu/cpu125/acpi_cppc/feedback_ctrs >/dev/null; done'; b=$(col 125 IPI1:)
echo "100 remote reads from cpu0: IPI1 delta on cpu125 = $((b-a))"
a=$(col 125 IPI1:); taskset -c 125 bash -c 'for i in $(seq 100); do cat /sys/devices/system/cpu/cpu125/acpi_cppc/feedback_ctrs >/dev/null; done'; b=$(col 125 IPI1:)
echo "100 local reads on cpu125: IPI1 delta on cpu125 = $((b-a))"
a=$(col 125 IPI1:); taskset -c 0 bash -c 'for i in $(seq 100); do cat /sys/devices/system/cpu/cpufreq/policy125/scaling_cur_freq >/dev/null; done'; b=$(col 125 IPI1:)
echo "100 remote scaling_cur_freq reads from cpu0: IPI1 delta on cpu125 = $((b-a))"
echo "=== nvme hctx -> cpu mapping ==="
for h in 118 119 120 121 122 123 124 125; do printf 'hctx%s:%s ' $h "$(cat /sys/block/nvme0n1/mq/$h/cpu_list)"; done; echo
echo "nvme0 queue_count=$(cat /sys/class/nvme/nvme0/queue_count 2>&1) nvme1 queue_count=$(cat /sys/class/nvme/nvme1/queue_count 2>&1)"
for i in 176 183 304 311; do echo "irq $i: $(cat /sys/kernel/irq/$i/actions) smp_affinity_list=$(cat /proc/irq/$i/smp_affinity_list) effective=$(cat /proc/irq/$i/effective_affinity_list) perms=$(stat -c %a /proc/irq/$i/smp_affinity_list)"; done
echo "=== RCU kthreads allowed ==="
for p in 15 16 17 586 680 681; do echo "pid $p $(cat /proc/$p/comm): allowed=$(grep Cpus_allowed_list /proc/$p/status | awk '{print $2}')"; done
echo "=== unbound kworkers / foreign threads on 120-127 now ==="
ps -eLo tid,psr,user,comm --no-headers | awk '$2>=120&&$2<=127' | grep -vE 'cpuhp|ksoftirqd|migration|kworker/12[0-7]:' | sort -k2n | tr '\n' ';'; echo
echo "=== loginctl / arm ==="
loginctl show-session 4 -p TTY -p IdleHint -p IdleSinceHint -p Remote 2>&1 | tr '\n' ' '; echo
ps -u arm -o pid,etime,stat,pcpu,comm --no-headers | tr '\n' ';'; echo
echo "=== sysfs isolation files ==="
echo "isolated='$(cat /sys/devices/system/cpu/isolated)' wq cpumask=$(cat /sys/devices/virtual/workqueue/cpumask) isolated=$(cat /sys/devices/virtual/workqueue/cpumask_isolated) requested=$(cat /sys/devices/virtual/workqueue/cpumask_requested 2>&1)"
echo "subtree_control: $(cat /sys/fs/cgroup/cgroup.subtree_control) ; user.slice cpuset files: $(ls /sys/fs/cgroup/user.slice | grep -c cpuset)"
date -u
