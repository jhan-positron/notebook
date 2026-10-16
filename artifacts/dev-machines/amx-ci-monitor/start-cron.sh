#!/bin/sh
set -eu
cd /home/jhan/workspace/random/amx-ci-monitor
umask 077
mkdir -p logs
# The lock prevents duplicate scheduler processes after repeated starts.
/usr/bin/setsid -f /usr/bin/flock -n -F logs/scheduler.lock \
    /usr/bin/env -i HOME=/home/jhan PATH=/usr/bin:/bin \
    /home/jhan/workspace/random/amx-ci-monitor/bin/supercronic -debug \
    /home/jhan/workspace/random/amx-ci-monitor/schedule.cron \
    </dev/null >>logs/scheduler.log 2>&1
