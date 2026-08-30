// Compile-time coverage for the AMX software-attention paths (see
// Note [AMX attention dispatch] in tron/kernels/amx_attn_iface.hpp): this
// object library is built with TRON_AMX_DISPATCH and TRON_AMX_K_MIRROR defined
// whatever the build's options are, so the #ifdef'd dispatch, the save_k
// write-through and the mirror arena cannot rot in the default (OFF) build.
// Instantiates the full scheduler for one attention shape the kernels serve
// (llama-3.1-8b: 32 query heads / 8 KV heads / 128 dims). No CTest entry: it
// runs no model.
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/plugins/llama.hpp"
#include "tron/scheduler/full.hpp"

namespace tron {

static_assert(amx_attn::shape_ok(named_llama_configs::llama_3p1_8b.head_size,
    named_llama_configs::llama_3p1_8b.n_heads / named_llama_configs::llama_3p1_8b.n_kv_heads));
static_assert(amx_mirror_eligible(llama_3p1_8b<tp1>::plugin_model::attention_kernels));

template struct full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>;

}  // namespace tron
