import sys
d = "/home/jhan/workspace/intel-AMX/exec/glimext-20261018"
p = d + "/build.sh"; s = open(p).read()
old = 'rm -f "$RES/build-$TAG.done"\n'
new = '''# one build per tag at a time (the chain may be relaunched while a build still runs); a second copy exits without touching the marker
exec {BUILD_LOCK_FD}>"/var/tmp/jhan/$NAME.build-$TAG.lock"
flock -n "$BUILD_LOCK_FD" || { echo "$(ts) another build.sh $TAG holds /var/tmp/jhan/$NAME.build-$TAG.lock; this copy exits"; exit 1; }
rm -f "$RES/build-$TAG.done"
'''
assert s.count(old) == 1; s = s.replace(old, new); open(p, "w").write(s)
p = d + "/chain.sh"; s = open(p).read()
old = '''      if pgrep -f "glimext-20261018/build[.]sh" >/dev/null; then echo "$(ts) step B: a build.sh already runs on this host; waiting for the markers"
      else
        [ "$(cat "$RES/build-g16b.done" 2>/dev/null)" = ok ] || { env TAG=g16b SHA="$BASE_SHA" KSYM_RE="$KSYM_BASE" KSYM_N=$KSYM_BASE_N bash "$C/build.sh" & }
        [ "$(cat "$RES/build-g16h.done" 2>/dev/null)" = ok ] || { env TAG=g16h SHA="$HEAD_SHA" KSYM_RE="$KSYM_HEAD" KSYM_N=$KSYM_HEAD_N bash "$C/build.sh" & }
      fi
'''
new = '''      # build.sh holds a per-tag lock: a copy launched while another runs exits at once and leaves the marker alone
      [ "$(cat "$RES/build-g16b.done" 2>/dev/null)" = ok ] || { env TAG=g16b SHA="$BASE_SHA" KSYM_RE="$KSYM_BASE" KSYM_N=$KSYM_BASE_N bash "$C/build.sh" & }
      [ "$(cat "$RES/build-g16h.done" 2>/dev/null)" = ok ] || { env TAG=g16h SHA="$HEAD_SHA" KSYM_RE="$KSYM_HEAD" KSYM_N=$KSYM_HEAD_N bash "$C/build.sh" & }
'''
assert s.count(old) == 1; s = s.replace(old, new); open(p, "w").write(s)
print("patched")
