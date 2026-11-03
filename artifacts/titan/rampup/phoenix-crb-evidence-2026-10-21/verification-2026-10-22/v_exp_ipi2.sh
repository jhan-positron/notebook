export LC_ALL=C SYSTEMD_PAGER= SYSTEMD_COLORS=0
date -u
col() { awk -v c="CPU$1" -v n="$2" 'NR==1{for(i=1;i<=NF;i++) if($i==c) k=i; next} $1==n{print $(k+1)}' /proc/interrupts; }
echo "timedated before: $(pgrep -af systemd-timedated | grep -v pgrep | tr '\n' ' ') $(systemctl show systemd-timedated.service -p ActiveState --value)"
taskset -c 0 timedatectl >/dev/null 2>&1   # unmeasured: make sure the daemon is running
sleep 1
echo "timedated now: $(systemctl show systemd-timedated.service -p ActiveState -p ExecMainStartTimestamp --value | tr '\n' ' ')"
echo "=== A: 4 s spin on cpu125 + 3x timedatectl while the daemon is already running ==="
a=$(col 125 IPI1:); t=$(col 125 12:)
( taskset -c 125 timeout 4 bash -c 'while :; do :; done' & )
sleep 0.3; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 0.5; taskset -c 0 timedatectl >/dev/null 2>&1; sleep 2.9
b=$(col 125 IPI1:); u=$(col 125 12:)
echo "A: IPI1=$((b-a)) arch_timer=$((u-t))"
sleep 1
echo "=== B: 4 s spin on cpu125 + 3x 'systemctl is-active apt-daily.timer' + 1x 'ps -eLo' + 1x 'cat /proc/interrupts' ==="
a=$(col 125 IPI1:); t=$(col 125 12:)
( taskset -c 125 timeout 4 bash -c 'while :; do :; done' & )
sleep 0.3; for i in 1 2 3; do taskset -c 0 systemctl is-active apt-daily.timer >/dev/null 2>&1; sleep 0.3; done; taskset -c 0 ps -eLo tid,psr,comm >/dev/null; taskset -c 0 cat /proc/interrupts >/dev/null; sleep 2.2
b=$(col 125 IPI1:); u=$(col 125 12:)
echo "B: IPI1=$((b-a)) arch_timer=$((u-t))"
echo "timedated after: $(systemctl show systemd-timedated.service -p ActiveState --value)"
date -u
