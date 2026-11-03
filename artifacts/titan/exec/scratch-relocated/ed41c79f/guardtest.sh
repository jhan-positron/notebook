MARKER=/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/fake.RUNNING
rm -f $MARKER
guard() {
    "$@" & local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        if [[ -e $MARKER ]]; then
            echo "marker appeared: killing pid $pid ($1)" >&2
            kill "$pid" 2>/dev/null; sleep 1; kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
            exit 3
        fi
        sleep 5 & wait $!
    done
    wait "$pid"
}
( sleep 7; touch $MARKER ) &
start=$(date +%s)
guard sleep 60
echo "not reached"
