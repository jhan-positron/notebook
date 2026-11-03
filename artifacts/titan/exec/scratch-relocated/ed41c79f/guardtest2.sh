set -euo pipefail
MARKER=/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/fake.RUNNING
rm -f $MARKER
guard() {
    setsid "$@" & local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        if [[ -e $MARKER ]]; then
            echo "marker appeared: killing process group $pid ($1)" >&2
            kill -- -"$pid" 2>/dev/null || true; sleep 1; kill -9 -- -"$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            exit 3
        fi
        sleep 5 & wait $! || true
    done
    wait "$pid"
}
( sleep 6; touch $MARKER ) &
guard bash -c 'sleep 120 & wait'   # a wrapper with a descendant, like perf stat -- bandwidth
echo "not reached"
