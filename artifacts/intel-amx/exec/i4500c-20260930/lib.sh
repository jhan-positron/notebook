# i4500c-20260930 shared shell functions (source after exec/lib-guard.sh; the caller sets RES and, optionally, STATUS).
# Machine handling on delphi-3bda, our half: wait for the CI lease (600 s grace), the pre-CI hold (01:40-03:45 UTC),
# another person's activity (other_user_active of lib-guard.sh; bill is excluded by GUARD_EXCLUDE_USERS, so Rhys or
# anyone else blocks us), and the production engines (taken down through platformd only when idle for 10 min:
# rinzler_takeover_if_idle, fail closed). NOT_BEFORE (an ISO time) holds every step until then.
STATUS=${STATUS:-$RES/status.txt}
ts() { date -u +%FT%TZ; }
status() { mkdir -p "$(dirname "$STATUS")"; echo "$(ts) $*" >"$STATUS"; echo "$(ts) STATUS $*"; }
hp_free() { awk '/^HugePages_Free/{print $2}' /proc/meminfo; }
machine_line() { echo "load=$(cut -d' ' -f1-3 /proc/loadavg) hugepages_free=$(hp_free) units_active=$(systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3 2>/dev/null | grep -c '^active$') others=$(ps -eo user= | sort -u | grep -v -E '^(root|jhan|nobody|positron|packer|bill|_apt|syslog|systemd.*|messagebus|daemon|www-data|_chrony|polkitd|dnsmasq|uuidd|tss|fwupd-refresh|lxd|snapd|sshd|tcpdump|landscape|pollinate|usbmux|_rpc|statd|kernoops|avahi|cups-pk-helper|rtkit|whoopsie|gdm|colord|geoclue|saned|nm-openvpn|gnome-initial-setup|hplip|dhcpcd|systemd-timesync)$' | tr '\n' ',')"; }
preci_hold() { local hm; hm=$((10#$(date -u +%H%M))); [ "$hm" -ge 140 ] && [ "$hm" -lt 345 ]; }
not_before_wait() {  # NOT_BEFORE=2026-09-29T13:00:00Z
  local nb=${NOT_BEFORE:-}; [ -n "$nb" ] || return 0
  local t; t=$(date -u -d "$nb" +%s) || { echo "$(ts) bad NOT_BEFORE '$nb'"; return 1; }
  if [ "$(date -u +%s)" -lt "$t" ]; then status "waiting: NOT_BEFORE $nb"; fi
  while [ "$(date -u +%s)" -lt "$t" ]; do sleep 60; done
  return 0
}
# Why we cannot run now, on stdout; rc 0 = blocked. Reports only; the takeover of idle production engines happens in
# wait_clear, in the main shell (rinzler_takeover_if_idle keeps its latch in shell variables, which a command
# substitution would lose).
blocked() {
  preci_hold && { echo "pre-CI hold (01:40-03:45 UTC)"; return 0; }
  ci_lease_busy 600 && { echo "CI lease busy"; return 0; }
  other_user_active 2>/dev/null && { echo "another person is active on the machine"; return 0; }
  rinzler_active && { echo "rinzler@N unit active"; return 0; }
  [ "$(hp_free)" -ge "${NEED_HUGEPAGES:-256}" ] || { echo "only $(hp_free) free hugepages (need ${NEED_HUGEPAGES:-256})"; return 0; }
  return 1
}
wait_clear() {  # rc 0 = clear; rc 1 = the pre-CI hold started (the caller stops)
  local why waited=0
  not_before_wait || return 1
  while why=$(blocked); do
    [ $waited = 0 ] && { status "waiting: $why"; waited=1; }
    preci_hold && { PRECI_STOP=1; return 1; }
    if [ "$why" = "rinzler@N unit active" ] && rinzler_takeover_if_idle; then
      # Remember that WE stopped production: the chain brings it back at its end (serving_restore).
      echo "$(ts) taken down by $0 pid $$" >>"$RES/serving-taken-down.marker"; continue
    fi
    sleep 60
  done
  return 0
}
PRECI_STOP=0
take_guard() { local waited=0; until campaign_guard_acquire; do [ $waited = 0 ] && { status "waiting: guard refused"; waited=1; }; sleep 60; wait_clear || return 1; done; return 0; }
# Background watcher: kills our processes (regex $2) within ~10 s when CI takes the lease or serving comes up; when the
# main script died without its EXIT trap it also removes our hugepage files (prefix $3).
watch_run() { local sf=$1 re=$2 hp=${3:-} why main=$$; [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; while :; do kill -0 "$main" 2>/dev/null || { pkill -TERM -u jhan -f "$re" 2>/dev/null; sleep 10; pkill -KILL -u jhan -f "$re" 2>/dev/null; sleep 2; [ -n "$hp" ] && remove_our_hugepage_files "$hp"; exit 0; }; why=""; if ci_lease_busy; then why="CI lease busy"; elif rinzler_active; then why="rinzler@N unit active"; fi; [ -n "$why" ] && { [ -e "$sf" ] || echo "$(ts) WATCH-STOP $why" >"$sf"; pkill -TERM -u jhan -f "$re" 2>/dev/null; }; sleep 10; done; }
WPID=""; stop_watcher() { [ -n "$WPID" ] && { kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null; }; WPID=""; }
remove_our_hugepage_files() { local f; for f in "$1"* /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f"; done; return 0; }

# Bring production serving back when a script of this campaign took it down (the marker), the lease is free and no
# unit is active. Through platformd (exec/q4b-fpga-20260921/dut.sh serving-up). Removes the marker on success.
serving_restore() {
  [ -e "$RES/serving-taken-down.marker" ] || { echo "$(ts) serving: no takeover of ours recorded, nothing to bring up"; return 0; }
  if ci_lease_busy 600; then echo "$(ts) serving: CI lease busy, leaving serving alone (marker kept)"; return 0; fi
  if rinzler_active; then echo "$(ts) serving: rinzler units already active"; rm -f "$RES/serving-taken-down.marker"; return 0; fi
  echo "$(ts) serving: bringing production up through platformd (dut.sh serving-up)"
  if timeout 900 bash /home/jhan/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh serving-up; then rm -f "$RES/serving-taken-down.marker"; else echo "$(ts) serving: serving-up rc=$? (jhan: check platformd; marker kept)"; fi
}
