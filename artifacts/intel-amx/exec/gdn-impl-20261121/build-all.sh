#!/usr/bin/env bash
# gdn-impl-20261121: build the three trees of the campaign one after another on delphi-3b35 (see build.sh).
#   ctr = the counters only (the base build of the plan), pa = + GDN chain kernel and AMX block kernel,
#   pab = + AMX attention kernels for 256-wide heads.
# Usage: CTR=<sha> PA=<sha> PAB=<sha> bash build-all.sh     Marker: exec/results/gdn-impl-20261121/build-all.done
set -u
E=/home/jhan/workspace/intel-AMX/exec
R=$E/results/gdn-impl-20261121
rm -f "$R/build-all.done"
ALL='runtron t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype t_llama_unit t_tronstats_convention'
TAG=ctr SHA=${CTR:?} TARGETS="$ALL" CPUS=${CPUS:-96-143} JOBS=${JOBS:-44} bash $E/gdn-impl-20261121/build.sh
TAG=pa SHA=${PA:?} TARGETS="$ALL" CPUS=${CPUS:-96-143} JOBS=${JOBS:-44} bash $E/gdn-impl-20261121/build.sh
TAG=pab SHA=${PAB:?} TARGETS="$ALL" CPUS=${CPUS:-96-143} JOBS=${JOBS:-44} bash $E/gdn-impl-20261121/build.sh
echo "ctr=$(cat $R/build-ctr.done) pa=$(cat $R/build-pa.done) pab=$(cat $R/build-pab.done)" >"$R/build-all.done"
