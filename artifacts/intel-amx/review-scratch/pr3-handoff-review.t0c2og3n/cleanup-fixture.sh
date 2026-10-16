set -u
EXEC=/fixture
MARKER_TAKEN=1
bash() { printf 'STUB invoked: %s\n' "$*"; }
ts() { printf fixture-time; }
machine() { printf 'lease=free serving=down marker=released'; }
finish() { [ "$MARKER_TAKEN" = 1 ] && { bash "$EXEC/bill-share.sh" release 2>&1 | tail -1; echo "$(ts) Bill marker released"; }; echo "$(ts) machine at exit: $(machine)"; }
trap finish EXIT
exit 17
