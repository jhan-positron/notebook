#!/bin/sh
HERE=/tmp/round17-review/bin
set -- --quick --out /tmp/round17-review/out
. /home/jhan/workspace/titan/cache-perf/asimov/lib_run.sh
run absent-test.csv cmnq absent-test /bin/true
finish_suite probe
