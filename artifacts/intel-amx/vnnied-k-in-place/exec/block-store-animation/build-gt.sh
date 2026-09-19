#!/bin/bash
# Build and run the ground-truth program against the real k_vnni.hpp of the
# worktree (g++ 11 lacks __bf16, so a bf16 shim with the same API is used).
set -euo pipefail
cd "$(dirname "$0")"
TRON=${TRON:-/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K}
g++ -std=c++20 -O2 -mavx512f -mavx512bw -mavx512vl -mavx512bf16 -I shim -I "$TRON/h" gt.cpp -o gt 2>/dev/null
./gt
