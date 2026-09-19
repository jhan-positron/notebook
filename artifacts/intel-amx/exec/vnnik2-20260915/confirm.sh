#!/usr/bin/env bash
# Confirmation round for the review-fixed commit: build it into /var/tmp/jhan/tron-vnnik3
# (runtron.vnnik3) with build.sh, then run campaign.sh under NAME=vnnik2-confirm-20260915
# with the arms base / vnni0 / ab at prompt 1024 (tp2 and tp4, 2 repetitions each), the
# greedy smoke and the traces of the new arms. Must start only after the vnnik2-20260915
# campaign has finished (its marker exists): a 96-job build next to running cells would
# perturb them. Usage (on delphi-3bda): confirm.sh <commit>
set -u
COMMIT=$1
EXEC=/home/jhan/workspace/intel-AMX/exec
until [ -s "$EXEC/logs/vnnik2-20260915.done" ]; do sleep 60; done
export RES=$EXEC/results/vnnik2-confirm-20260915 LOG=$EXEC/logs/vnnik2-confirm-build.log WT=/var/tmp/jhan/tron-vnnik3 SUFFIX=vnnik3
mkdir -p "$RES"
bash "$EXEC/vnnik2-20260915/build.sh" "$COMMIT"
unset RES LOG
NAME=vnnik2-confirm-20260915 WT=/var/tmp/jhan/tron-vnnik3 SUFFIX=vnnik3 ARMS="base vnni0 ab" PROMPTS=1024 RT_REPS=2 TP4_REPS=2 LONG_REPS=0 RUN_TRACES=1 \
  bash "$EXEC/vnnik2-20260915/campaign.sh"
