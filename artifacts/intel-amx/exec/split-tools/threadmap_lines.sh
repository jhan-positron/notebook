#!/usr/bin/env bash
# Print the file:line anchors that PR3879/new-PRs/PR1/thread-map.md's "New location"
# column needs, read from the given commits (first match of each symbol).
# Usage: threadmap_lines.sh <PR1 tip> <PR0 tip> <PR0b tip>   (inside ~/workspace/ai-runs/tron-split)
set -u
P1=${1:?PR1 tip}; P0=${2:?PR0 tip}; P0b=${3:?PR0b tip}
ln() { local c=$1 f=$2 pat=$3; local n; n=$(git show "$c:$f" | grep -n -E -m1 "$pat" | cut -d: -f1); printf "%s:%s" "$f" "${n:-NOTFOUND}"; }
echo "row 1  (env var doc):      doc/amx_software_attention.md (whole file, $(git show $P1:doc/amx_software_attention.md | wc -l) lines); $(ln $P1 h/tron/kernels/amx_attn_iface.hpp 'Note \[AMX attention dispatch\]$') (Note), $(ln $P1 h/tron/kernels/amx_attn_iface.hpp 'runtime disable: TRON_AMX_DISABLE') (item 4); $(ln $P1 CMakeLists.txt 'option\(TRON_AMX_DISPATCH')"
echo "row 2  (inline globals):   $(ln $P0 h/tron/kernels/page_share_counters.hpp 'inline. variables \(C\+\+17\)')"
echo "row 3  (thread_local):     $(ln $P1 h/tron/models/self_attention.hpp 'thread_local std::vector<amx_qpack_slot>')"
echo "row 4  (helper):           $(ln $P1 h/tron/models/self_attention.hpp 'const bf16\* packed_amx_query\(')"
echo "row 5  (mask_t -> bitset): $(ln $P1 h/tron/models/self_attention.hpp 'std::bitset<max_minibatch_size> amx_packed;')"
echo "row 6  (two paths):        $(ln $P1 h/tron/models/self_attention.hpp 'static bool is_dense_amx_page\(') and $(ln $P1 h/tron/models/self_attention.hpp 'bool try_apply_dense_amx_page\(')"
echo "row 7  (syscall consts):   $(ln $P1 src/tron/kernels/amx_attn.cpp 'ARCH_REQ_XCOMP_PERM') (first mention), $(ln $P1 src/tron/kernels/amx_attn.cpp 'constexpr.*xfeature_xtiledata') (named constant)"
echo "row 8  (memory order):     $(ln $P0b h/tron/models/kv_cache.hpp 'last_print_bytes\.load\(')"
echo "row 9  (tron::bf16):       $(ln $P1 h/tron/kernels/amx_attn_iface.hpp 'tron::bf16') (first mention in the interface)"
echo "row 10 (namespace):        $(ln $P1 h/tron/kernels/amx_attn_iface.hpp 'namespace (tron::)?amx_attn_h128g4|namespace amx_attn_h128g4')"
echo "row 11 (lazy pack):        $(ln $P1 h/tron/models/self_attention.hpp 'const bf16\* packed_amx_query\(') (same helper as row 4); call site $(ln $P1 h/tron/models/self_attention.hpp 'amx_qp = packed_amx_query<geometry>')"
echo "row 12 (aligned buffer):   $(ln $P1 h/tron/models/self_attention.hpp 'struct alignas\(64\) amx_qpack_slot')"
