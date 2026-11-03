export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0
date -u
col() { awk -v c="CPU$1" -v n="$2" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1==n{print $(k+1)}' /proc/interrupts; }
echo "timedated running before: $(pgrep -a systemd-timedated | tr '\n' ' ')"
echo "=== control: 4 s pinned spin on cpu125, nothing else started ==="
a=$(col 125 IPI1:); t=$(col 125 12:); r=$(col 125 IPI0:)
taskset -c 125 timeout 4 bash -c 'while :; do :; done'
b=$(col 125 IPI1:); u=$(col 125 12:); s=$(col 125 IPI0:)
echo "control 4 s: IPI1=$((b-a)) arch_timer=$((u-t)) IPI0=$((s-r))"
sleep 1
echo "=== 4 s pinned spin on cpu125 with 3x timedatectl from cpu0 ==="
a=$(col 125 IPI1:); t=$(col 125 12:); r=$(col 125 IPI0:)
( taskset -c 125 timeout 4 bash -c 'while :; do :; done' & )
sleep 0.3; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 2.9
b=$(col 125 IPI1:); u=$(col 125 12:); s=$(col 125 IPI0:)
echo "with 3x timedatectl: IPI1=$((b-a)) arch_timer=$((u-t)) IPI0=$((s-r))"
echo "timedated running after: $(pgrep -a systemd-timedated | tr '\n' ' ')"
echo "=== idle cpu125 4 s with 3x timedatectl ==="
a=$(col 125 IPI1:); t=$(col 125 12:)
sleep 0.3; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 2.7
b=$(col 125 IPI1:); u=$(col 125 12:)
echo "idle with 3x timedatectl: IPI1=$((b-a)) arch_timer=$((u-t))"
echo "systemd-timedated.service: $(systemctl show systemd-timedated.service -p ActiveState -p PrivateTmp -p ProtectSystem -p ProtectHome -p ExecMainStartTimestamp 2>&1 | tr '\n' ' ')"
date -u
