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

ci_lease_busy() {
  python3 - <<'PY'
import json, re, sys, time
p = '/run/lock/systems-test-ci.lease'
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
sys.exit(0 if (state == 'busy' and time.time() < exp) else 1)
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
  if pgrep -x 'runtron(\.[a-z0-9]+)?' >/dev/null; then
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
