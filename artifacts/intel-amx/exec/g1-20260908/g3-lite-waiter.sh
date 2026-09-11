#!/usr/bin/env bash
# Waits until the G1 campaign is in a serving phase (socket 1 idle: rinzler runs on socket 0),
# then runs the standalone G3 probe once on socket-1 core 141 (one core, nice 19). Half-machine
# work; needs no guard. Launched detached (setsid nohup) by launch.sh or by hand.
until grep -q "phase [2-6]" /home/jhan/workspace/intel-AMX/exec/logs/g1-20260908.status 2>/dev/null; do sleep 120; done
sleep 60   # let the first rinzler settle
G3_CORE=141 bash /home/jhan/workspace/intel-AMX/exec/g1-20260908/g3-lite.sh
