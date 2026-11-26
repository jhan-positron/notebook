#!/usr/bin/env bash
# Cut chunk_evenly out of a TRON checkout, build the harness around it, run it.
# Usage: run.sh [path to a TRON checkout]
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
tron=${1:-/home/jhan/workspace/ai-runs/tron-env-vars/tron-main}
header="${tron}/h/tron/models/model.hpp"

# Lines 212-346 hold chunk_evenly and adjust_grains_for_partners at commit
# 7eddde7895. Stop with an error if the header moved.
sed -n '212,346p' "${header}" > "${here}/chunk_evenly_extract.inc"
head -n 1 "${here}/chunk_evenly_extract.inc" | grep -q '^TRON(nodiscard, inline)$' || {
  echo "model.hpp:212 is not the start of chunk_evenly; fix the line range" >&2
  exit 1
}
tail -n 1 "${here}/chunk_evenly_extract.inc" | grep -q '^}$' || {
  echo "model.hpp:346 is not the end of adjust_grains_for_partners" >&2
  exit 1
}

echo "TRON commit: $(git -C "${tron}" rev-parse --short=10 HEAD)"
g++ -std=c++20 -O1 -Wall -Wextra -o "${here}/harness" "${here}/harness.cpp"
"${here}/harness"
