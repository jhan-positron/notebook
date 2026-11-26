# pr5606-check-20261123: settings shared by the scripts of this folder. Sourced, not run.
# Runs ON delphi-3b35 (shared machine: other users run servers on the first half). Our CPUs are 96-143.
# Words: tron = the inference program; AMX = Intel's tile-matrix instructions;
# TRON_AMX_DISPATCH = the CMake option (default OFF) that compiles the AMX kernels and their call sites.
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5606-check-20261123
HERE=$EXEC/$NAME
RES=$EXEC/results/$NAME
LOGDIR=$EXEC/logs
REPO=/home/jhan/workspace/tron
# The three source states. S0 = head of PR 5022. S1 = first commit of PR 5606. S2 = both commits of PR 5606.
S0=ddf843ad97f8602fc1171458e42036ef03b6e4c4
S1=c6cba6b0f8b9be57672a3cbf36021df4069a2b0b
S2=90a9110be5d2c6552267322c472902984dca8e0f
S2_TREE=d6c77bd315c556ebf78556450562f2427ee660c7
OUR_CPUS=96-143
PIN="nice -n10 taskset -c $OUR_CPUS"
JOBS=40
# The build runs each new test binary once to list its cases, so the build needs this value too.
export SYSTEM_CONFIG="--instance 1,2"
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
ts() { date -u +%FT%TZ; }
wt_of() { case $1 in off) echo /var/tmp/jhan/b35-pr5606-off ;; on) echo /var/tmp/jhan/b35-pr5606-on ;; *) return 1 ;; esac; }
sha_of() { case $1 in S0) echo $S0 ;; S1) echo $S1 ;; S2) echo $S2 ;; *) return 1 ;; esac; }
only_3b35() { [ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only (here: $(hostname))"; exit 1; }; }
# Prints the busy share of our CPUs 96-143 over 2 s, from /proc/stat.
busy_pct() {
  local prog='/^cpu[0-9]+ /{c=substr($1,4)+0; if(c>=96&&c<=143){t=0; for(i=2;i<=9;i++)t+=$i; T+=t; I+=$5+$6}} END{print T, I}'
  local a b
  a=$(awk "$prog" /proc/stat); sleep 2; b=$(awk "$prog" /proc/stat)
  awk -v a="$a" -v b="$b" 'BEGIN{split(a,x," "); split(b,y," "); dt=y[1]-x[1]; di=y[2]-x[2]; printf "%.1f%%", (dt > 0 ? 100 * (dt - di) / dt : 0)}'
}
# Prints the tracked or untracked changes of a tree. The build folder gen is ignored by .gitignore.
dirty_of() { git -C "$1" status --porcelain; }
