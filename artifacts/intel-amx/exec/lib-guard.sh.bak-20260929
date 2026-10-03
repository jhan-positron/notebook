#!/usr/bin/env bash
# Shared launch guards for AMX campaigns on delphi-3bda. Source this from
# every campaign script:   . ~/workspace/intel-AMX/exec/lib-guard.sh
#
# Authority order (2026-08-19, per Rhys's systems_test PR #180 + jhan):
#   1. CI lease  /run/lock/systems-test-ci.lease  - AUTHORITATIVE for
#      "is System CI holding the DUT right now". Busy only if the file
#      exists AND state == "busy" AND now < expires_at_epoch. Missing,
#      non-busy, or expired => CI is not holding: rinzler cleanup, hugepage
#      cleanup, and FPGA claiming are allowed.
#   2. Cross-session campaign flock /var/tmp/jhan/3bda-campaign.lock
#      (adopted from the trace-sync-points session) + no-runtron launch guard.
#   3. The clock window (nightly prep ~03:30Z) is ADVISORY only: the lease
#      says "holding now", not "starts in five minutes" - so long campaigns
#      must re-check ci_lease_busy between runs and stop when it turns busy.
#   4. Other people (added 2026-09-05: Bill shares the machine Sat 09-06 to
#      Mon 09-08). other_user_active samples the CPU time of every login
#      user except jhan over a short window and looks for tron binaries
#      (rinzler, runtron, gen*/ test binaries) or builds (ninja, cmake, cc1plus,
#      ld) owned by them. An idle login (open shell, tmux, editor) is NOT
#      activity and does not block. The nightly's own rinzler@N units run as
#      "positron" and are covered by the lease and rinzler_active, so
#      processes inside a rinzler@*.service cgroup are skipped here.

ci_lease_busy() {  # optional $1 = grace in seconds (2026-09-15): a "busy" lease that expired less than $1 s ago still counts as busy. No argument = 0 s, the old behaviour.
  CI_LEASE_GRACE=${1:-0} python3 - <<'PY'
import json, os, re, sys, time
p = os.environ.get('GUARD_LEASE_FILE', '/run/lock/systems-test-ci.lease')   # GUARD_LEASE_FILE is a test hook only
grace = float(os.environ.get('CI_LEASE_GRACE', '0') or 0)
try:
    raw = open(p).read()
except OSError:
    sys.exit(1)  # no file -> not busy
state, exp = '', 0.0
try:
    d = json.loads(raw)
    state = str(d.get('state', '')).strip().lower()
    exp = float(d.get('expires_at_epoch', 0))
except Exception:
    m = re.search(r'state["\s:=]+([A-Za-z_-]+)', raw)
    if m: state = m.group(1).lower()
    m = re.search(r'expires_at_epoch["\s:=]+(\d+(?:\.\d+)?)', raw)
    if m: exp = float(m.group(1))
sys.exit(0 if (state == 'busy' and time.time() < exp + grace) else 1)
PY
}

# Is another person actively using the machine? Exit 0 = yes (busy), 1 = no.
# Tunables (env): GUARD_OTHER_USERS   space-separated user names to watch;
#                                     default = every user with uid >= 1000
#                                     that owns a process, except
#                                     GUARD_EXCLUDE_USERS
#                 GUARD_EXCLUDE_USERS default "jhan nobody positron packer"
#                 GUARD_OTHER_SAMPLE_SEC  CPU sampling window, default 10
#                 GUARD_OTHER_CPU_SEC     busy if the user's processes used more
#                                         than this many CPU-seconds in the
#                                         window, default 2.0 (= 0.2 core)
# Prints one report line per watched user to stderr; the last line is the
# verdict. An idle shell/tmux/editor uses ~0 CPU and does not count.
other_user_active() {
  python3 - <<'PY'
import os, sys, time, pwd, re
watch = os.environ.get('GUARD_OTHER_USERS', '').split()
excl = set(os.environ.get('GUARD_EXCLUDE_USERS', 'jhan nobody positron packer').split())
win = float(os.environ.get('GUARD_OTHER_SAMPLE_SEC', '10'))
thr = float(os.environ.get('GUARD_OTHER_CPU_SEC', '2.0'))
hz = os.sysconf('SC_CLK_TCK')
# Accounts on delphi-3bda come from a directory service and cannot be
# enumerated (getent passwd lists only local users; directory uids are huge,
# e.g. bill = 1062305141), so "who is here" is discovered from process
# ownership: every uid >= 1000 that owns a process is a person unless
# excluded. Names resolve per uid. positron and packer are service accounts
# (the nightly CI runs as positron and is covered by the lease).
name_cache = {}
def uname(uid):
    if uid not in name_cache:
        try: name_cache[uid] = pwd.getpwuid(uid).pw_name
        except KeyError: name_cache[uid] = str(uid)
    return name_cache[uid]
watch_set = set(watch)
def watched(uid):
    if uid < 1000: return False
    n = uname(uid)
    if n in excl: return False
    return (not watch_set) or (n in watch_set)
uids = {}
heavy = re.compile(r'(^|/)(rinzler|runtron(\.[a-z0-9]+)?|ninja|cmake|make|cc1plus|cc1|ld|ld\.lld|lld|clang(\+\+)?|g\+\+|gcc|perf|amx_[a-z_]+|t_[a-z0-9_]+)$')
def scan():
    out = {}   # pid -> (uid, cpu_ticks, comm, argv0)
    for d in os.listdir('/proc'):
        if not d.isdigit(): continue
        pid = int(d)
        try:
            st = os.stat(f'/proc/{pid}')
            uid = st.st_uid
            if not watched(uid): continue
            uids[uid] = uname(uid)
            cg = open(f'/proc/{pid}/cgroup').read()
            if 'rinzler@' in cg: continue          # nightly/production units: lease + rinzler_active cover them
            with open(f'/proc/{pid}/stat') as f: s = f.read()
            comm = s[s.index('(')+1:s.rindex(')')]
            fields = s[s.rindex(')')+2:].split()
            ticks = int(fields[11]) + int(fields[12])   # utime + stime
            try:
                argv = open(f'/proc/{pid}/cmdline','rb').read().split(b'\0')
                argv0 = argv[0].decode(errors='replace') if argv and argv[0] else comm
            except OSError:
                argv0 = comm
            out[pid] = (uid, ticks, comm, argv0)
        except (OSError, ValueError, IndexError):
            continue
    return out
a = scan(); time.sleep(win); b = scan()
busy = False
if not uids:
    print(f'GUARD other-user: no other login user owns a process (window {win:.0f} s)', file=sys.stderr)
for uid, user in sorted(uids.items(), key=lambda kv: kv[1]):
    cpu = 0.0; procs = 0; heavy_names = set(); top = []
    for pid, (u, t1, comm, argv0) in b.items():
        if u != uid: continue
        procs += 1
        t0 = a.get(pid, (u, t1, comm, argv0))[1]
        d = (t1 - t0) / hz
        cpu += max(d, 0.0)
        if d > 0.05: top.append((d, comm))
        if heavy.search(argv0) or heavy.search(comm): heavy_names.add(os.path.basename(argv0) if heavy.search(argv0) else comm)
    if procs == 0: continue
    top.sort(reverse=True)
    reason = []
    if cpu > thr: reason.append(f'{cpu:.1f} CPU-s in {win:.0f} s')
    if heavy_names: reason.append('tron/build processes: ' + ', '.join(sorted(heavy_names)))
    state = 'ACTIVE' if reason else 'idle'
    if reason: busy = True
    detail = '; '.join(reason) if reason else f'{procs} processes, {cpu:.2f} CPU-s in {win:.0f} s'
    hot = ', '.join(f'{c}:{d:.1f}s' for d, c in top[:4])
    print(f'GUARD other-user {user}: {state} ({detail}{"; hot: " + hot if hot else ""})', file=sys.stderr)
sys.exit(0 if busy else 1)
PY
}

# Take the cross-session lock and verify no runtron is running. Uses a
# DYNAMICALLY allocated file descriptor (bash 4.1+), stored in
# $CAMPAIGN_LOCK_FD, so sourcing this never collides with a script's own
# fds (a hardcoded fd 9 bit the trace-sync-points harness on 2026-08-19).
# Returns nonzero (with a message) if the machine is not launchable.
campaign_guard_acquire() {
  if ci_lease_busy; then echo "GUARD: System CI holds the DUT (lease busy)"; return 1; fi
  if other_user_active; then echo "GUARD: another person is actively using the DUT (see the other-user lines above)"; return 1; fi
  if blackout_active; then echo "GUARD: blackout window (see the line above)"; return 1; fi
  exec {CAMPAIGN_LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
  if ! flock -n "$CAMPAIGN_LOCK_FD"; then
    echo "GUARD: campaign flock held by another session"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  # -x matches the whole comm as an ERE: also catch the renamed campaign
  # binaries (runtron.canon, runtron.mirror, runtron.inc1b, ...).
  # GUARD_RUNTRON_USER (optional, 2026-09-14): when set, only that user's
  # runtron blocks the guard (our-half campaigns that must not wait for
  # another user's runtron export it); unset keeps the old any-user check.
  if pgrep ${GUARD_RUNTRON_USER:+-u "$GUARD_RUNTRON_USER"} -x 'runtron(\.[a-z0-9]+)?' >/dev/null; then
    echo "GUARD: runtron already running"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  # Production serving check (added 2026-08-19 after the peakbw handback
  # restored live rinzler serving): campaigns must not launch next to active
  # serving unless the script deliberately implements a stop-and-restore flow
  # and says so by passing --allow-serving.
  if [ "${1:-}" != "--allow-serving" ] && rinzler_active; then
    echo "GUARD: rinzler serving is active (pass --allow-serving only if your script stops and restores it)"
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
    return 1
  fi
  return 0
}

rinzler_active() {
  systemctl is-active --quiet rinzler@0 || systemctl is-active --quiet rinzler@1 ||   systemctl is-active --quiet rinzler@2 || systemctl is-active --quiet rinzler@3
}

# rinzler_takeover_if_idle: stop idle production serving once the nightly is over
# (added 2026-09-15, revised the same day after review).
#
# Words used here: rinzler@N = the four systemd units rinzler@0..3 that serve the
# production model. The nightly System CI starts them and never stops them (Rhys,
# 2026-09-15). lease = /run/lock/systems-test-ci.lease, the file that says whether CI
# holds the machine. blackout window = a line in /var/tmp/jhan/3bda-blackout for a day
# promised to another person (see blackout_active). SYSTEM_STATS = the status line each
# unit logs with its open, closed and busy session counts. Under load it comes every
# 5 min. An idle unit logs it at growing intervals (300 s, 450 s, 675 s, 1013 s, ...),
# so a 10 min window of an idle unit is often empty. serving ports = TCP 3000-3020, the
# range platformd advertises, and 13000-13020, the engine ports. slice files =
# /dev/hugepages/slice-*-of-8, the hugepage arenas the units map.
#
# History: the same steps ran inline in exec/vnnik-20260914/campaign.sh phase 0, the
# recipe first used by the round-1 campaigns. The our-half chains only waited for the
# units to stop. On 2026-09-15 that left rinzler@0 and rinzler@1 running for 2 h 25 min,
# until jhan stopped them by hand. Every campaign can now call this one copy.
#
# Use: call it from a wait loop that polls every 1 to 2 min. One attempt per call.
# Return 0 when no rinzler@N unit is active on return (none was up, or the stop worked).
# Return 1 otherwise. The units are stopped only when all of these hold:
#   - the lease is free, and it did not expire less than 600 s ago. CI renews the lease
#     by heartbeat, and gaps of 261 s to 322 s were seen on 2026-08-21.
#   - no blackout window is open.
#   - the UTC time is outside the takeover hold, 01:40 to 04:30. A timer starts the
#     production units at 02:45 UTC, and the nightly took the lease between 03:37:53 and
#     03:41:56 UTC on the eight nights 2026-09-08 to 2026-09-15. The hold keeps the
#     idle units alive for the nightly.
#   - this process has not stopped the units in the last 6 h. Units that come back
#     within 6 h of our stop were started on purpose by someone, so the loop waits.
#   - every active unit has been active for at least 10 min (600 s). A unit that is just
#     starting has no traffic yet and must not be judged idle.
#   - the journal of the units is readable. Its last 10 min hold no request line and no
#     SYSTEM_STATS line with a non-zero count. When the last 10 min hold no line at all,
#     the last journal line must be a SYSTEM_STATS line with all counts zero.
#   - no established TCP connection from another host exists on the serving ports at this
#     moment. An ss failure counts as a connection.
# After a successful stop, and only while no unit is active again, the slice files are
# removed when they belong to positron, or when they are ours and unmapped. Files of other
# users are kept.
# Each decision writes one line to stdout, so the campaign log shows why serving was or
# was not stopped. Test hooks: GUARD_HUGEPAGES_DIR (default /dev/hugepages),
# GUARD_TAKEOVER_HOLD_START and GUARD_TAKEOVER_HOLD_END (HHMM as a number, default 140
# and 430), GUARD_TAKEOVER_LAST (epoch seconds of the last stop by this process), and
# guard_utc_hhmm, which the unit tests replace.
GUARD_TAKEOVER_LAST=${GUARD_TAKEOVER_LAST:-0}
guard_utc_hhmm() { echo $((10#$(date -u +%H%M))); }
rinzler_takeover_hold() {  # 0 = inside the takeover hold window
  local hm; hm=$(guard_utc_hhmm)
  [ "$hm" -ge "${GUARD_TAKEOVER_HOLD_START:-140}" ] && [ "$hm" -lt "${GUARD_TAKEOVER_HOLD_END:-430}" ]
}
rinzler_min_active_age() {  # 0 = every active rinzler@N unit has been active >= $1 s. Otherwise prints the first younger unit and returns 1.
  local min=$1 i t s now; now=$(date +%s)
  for i in 0 1 2 3; do
    systemctl is-active --quiet "rinzler@$i" || continue
    t=$(systemctl show -p ActiveEnterTimestamp --value "rinzler@$i" 2>/dev/null) || t=""
    s=""; [ -n "$t" ] && { s=$(date -d "$t" +%s 2>/dev/null) || s=""; }   # empty stays empty: `date -d ""` would return today's midnight
    if [ -z "$s" ] || [ $((now - s)) -lt "$min" ]; then echo "rinzler@$i"; return 1; fi   # an unreadable start time counts as young
  done
  return 0
}
rinzler_stop_serving() {
  # Stop the production engines. platformd 0.11 (delphi-3bda since 2026-09-21) supervises the engines: a unit stopped with
  # systemctl is started again within about a minute, which made the q4b-rt8u campaign's first run stop itself at
  # 2026-09-22 16:36 UTC (WATCH-STOP rinzler@N unit active). So when platformd answers on GUARD_PLATFORMD (default
  # http://localhost:8080) the engines are taken down through its API (POST /api/inference/down, the same call dut.sh
  # serving-down makes) and we wait up to 180 s for every rinzler@N unit to leave the active state. Without platformd the
  # old systemctl stop is used. Production comes back through POST /api/inference/up (dut.sh serving-up) or the nightly.
  local pd=${GUARD_PLATFORMD:-http://localhost:8080} r i now; now=$(date -u +%FT%TZ)
  if r=$(curl -s -m 5 "$pd/api/inference/status" 2>/dev/null) && [ -n "$r" ]; then
    GUARD_STOP_VIA=platformd
    echo "$now GUARD takeover: platformd answers, taking serving down through POST $pd/api/inference/down: $(curl -s -m 60 -X POST "$pd/api/inference/down" 2>/dev/null | head -c 160)"
    for i in $(seq 1 36); do rinzler_active || return 0; sleep 5; done
    echo "$(date -u +%FT%TZ) GUARD takeover: rinzler@N units still active 180 s after the platformd down request"; return 1
  fi
  sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3
}
rinzler_takeover_if_idle() {
  local now epoch j rc traffic busy probe note sso conns f young hp=${GUARD_HUGEPAGES_DIR:-/dev/hugepages}
  now=$(date -u +%FT%TZ); epoch=$(date +%s)
  rinzler_active || return 0
  if ci_lease_busy 600; then echo "$now GUARD takeover: CI lease busy or expired less than 600 s ago, serving left running"; return 1; fi
  if blackout_active; then echo "$now GUARD takeover: blackout window, serving left running"; return 1; fi
  if rinzler_takeover_hold; then echo "$now GUARD takeover: inside the 01:40-04:30 UTC hold, serving left running"; return 1; fi
  if [ $((epoch - GUARD_TAKEOVER_LAST)) -lt 21600 ]; then echo "$now GUARD takeover: this process stopped serving $(( (epoch - GUARD_TAKEOVER_LAST) / 60 )) min ago and units are active again, so someone started them: serving left running"; return 1; fi
  if ! young=$(rinzler_min_active_age 600); then echo "$now GUARD takeover: ${young:-a unit} active for less than 10 min, serving left running"; return 1; fi
  j=$(sudo -n journalctl -q -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null); rc=$?
  [ "$rc" -eq 0 ] || { echo "$now GUARD takeover: journalctl failed (rc=$rc), serving left running"; return 1; }
  probe=$(sudo -n journalctl -u 'rinzler@*' -n 1 -o cat --no-pager 2>/dev/null) || true
  [ -n "$probe" ] || { echo "$now GUARD takeover: journal not readable (no last line), serving left running"; return 1; }
  if [ -n "$j" ]; then
    traffic=$(printf '%s\n' "$j" | grep -v '#EVT#' | grep -icE 'session|request|prompt|generat|token') || true
    busy=$(printf '%s\n' "$j" | grep 'SYSTEM_STATS' | grep -vc 'Open=0, Closed=0, Busy=0') || true
    note="window=10min"
  elif printf '%s\n' "$probe" | grep -q 'SYSTEM_STATS.*Open=0, Closed=0, Busy=0'; then
    traffic=0; busy=0; note="window=empty,last-line=idle-stats"   # idle units log stats at growing intervals; the last line says idle
  else
    echo "$now GUARD takeover: journal empty for the last 10 min and the last line is not an idle SYSTEM_STATS line, serving left running"; return 1
  fi
  sso=$(sudo -n ss -Htn state established '( sport >= :3000 and sport <= :3020 ) or ( sport >= :13000 and sport <= :13020 )' 2>/dev/null) || sso='ss-failed - - unknown:0'   # an ss failure counts as a connection
  conns=$(printf '%s\n' "$sso" | awk 'NF && $4 !~ /^127\.0\.0\.1:/' | wc -l)
  echo "$now GUARD takeover: rinzler units active; journal-request-lines=${traffic:-?} non-idle-stats-lines=${busy:-?} $note remote-conns=${conns:-?}"
  { [ "${traffic:-1}" -eq 0 ] && [ "${busy:-1}" -eq 0 ] && [ "${conns:-1}" -eq 0 ]; } || return 1
  echo "$now GUARD takeover: all checks passed, stopping rinzler@0..3 (lease free, units idle for 10 min)"
  GUARD_STOP_VIA=systemctl
  if ! rinzler_stop_serving; then
    echo "$now GUARD takeover: $GUARD_STOP_VIA stop returned nonzero, slice files kept"; return 1
  fi
  GUARD_TAKEOVER_LAST=$epoch
  sleep 5
  rinzler_active && { echo "$now GUARD takeover: a rinzler@N unit is active again after the stop, slice files kept"; return 1; }
  for f in "$hp"/slice-*-of-8; do
    [ -e "$f" ] || continue
    if [ "$(stat -c %U "$f" 2>/dev/null)" = positron ]; then rm -f "$f" && echo "$now GUARD takeover: removed $f (rinzler@N stopped)"
    elif [ -O "$f" ]; then ! fuser -s "$f" 2>/dev/null && rm -f "$f" && echo "$now GUARD takeover: removed $f (unmapped, ours)"
    else echo "$now GUARD takeover: $f belongs to $(stat -c %U "$f" 2>/dev/null || echo '?'), kept"
    fi
  done
  ! rinzler_active
}

campaign_guard_release() {
  if [ -n "${CAMPAIGN_LOCK_FD:-}" ]; then
    flock -u "$CAMPAIGN_LOCK_FD" 2>/dev/null || true
    exec {CAMPAIGN_LOCK_FD}>&-
    unset CAMPAIGN_LOCK_FD
  fi
}

# Between-runs check: stop the campaign if CI has taken the DUT or another
# person has started using it (2026-09-05). The name is kept so the ~30
# existing callers keep working; dut_contended is the same thing by a
# truthful name. ci_lease_busy alone is still available for CI-only logic.
# Blackout windows (2026-09-05): /var/tmp/jhan/3bda-blackout holds lines
# "start_epoch end_epoch note". While now is inside a window the DUT counts as
# contended: campaign_guard_acquire refuses and the wait loops keep waiting.
# Used for days promised to another person (e.g. Sunday 2026-09-06 for Bill).
blackout_active() {
  local f=/var/tmp/jhan/3bda-blackout now s e note
  [ -r "$f" ] || return 1
  now=$(date +%s)
  while read -r s e note; do
    [ -n "$s" ] && [ -n "$e" ] && [ "$now" -ge "$s" ] && [ "$now" -lt "$e" ] && {
      echo "GUARD blackout: ${note:-no note} (until $(date -u -d "@$e" +%FT%TZ))" >&2; return 0; }
  done < "$f"
  return 1
}
ci_took_dut() { ci_lease_busy || other_user_active || blackout_active; }
dut_contended() { ci_took_dut; }

# Wait until both CI and other people have left the DUT (poll every 5 min,
# up to $1 seconds, default 6 h). Returns nonzero on timeout.
wait_for_dut_free() {
  local deadline=$(( $(date +%s) + ${1:-21600} ))
  while dut_contended; do
    [ "$(date +%s)" -ge "$deadline" ] && return 1
    sleep 300
  done
  return 0
}

# Wait until CI releases the DUT (poll every 5 min, up to $1 seconds,
# default 6 h). Returns nonzero on timeout.
wait_for_ci_release() {
  local deadline=$(( $(date +%s) + ${1:-21600} ))
  while ci_lease_busy; do
    [ "$(date +%s)" -ge "$deadline" ] && return 1
    sleep 300
  done
  return 0
}
