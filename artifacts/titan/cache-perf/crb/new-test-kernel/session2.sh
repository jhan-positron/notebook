#!/usr/bin/env bash
# session2.sh - session 2 of Parts B and C: the visits of session 1 in the same order with the same settings.
# It stops at the first visit that does not end with status 0. Watch #phoenix-crb every 10 min while it runs.
N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel
EV='BWX_PMU_TYPE=11 BWX_EVENTS=cycles=0x11,instructions=0x08,l1d_refill=0x03,l2d_refill=0x17,ll_miss_rd=0x37'
ST='BWX_STOP=common BWX_START=common BWX_MIN_MS=6000'
v() { local log=$1; shift; "$N/visit.sh" "$log" "$@"; grep -q "ssh status 0" "$N/$log.log" || { echo "visit $log did not end with status 0: stop"; exit 1; }; echo "visit $log done $(date -u +%T)"; }
v visit-s2-B7 B7
v visit-s2-B10a B10a
v visit-s2-B10b B10b
ENVV="$ST B8_COUNTS=\"64+32 64+36 64+40 64+44 64+48 64+52 64+56\"" v visit-s2-B8B5B9 B8 B5 B9
v visit-s2-B1B4B6 B1 B4 B6
ENVV="$EV" v visit-s2-B2B3C1C2 B2 B3 C1 C2
ENVV="$EV $ST C3_B7_SETTINGS=\"pass:500:common pass:500:offset pass:6000:common pass:6000:offset common:500:common common:500:offset common:6000:common common:6000:offset\"" v visit-s2-C3 C3
