import os
R = '/home/jhan/workspace/ai-runs/tron-issue4525'
A, D = 'VIEW_ALIGNED_TRUE', 'VIEW_DMA_FALSE'
# (line at tip 1c87d66926, exact old substring, new substring)
EDITS = {
 'h/tron/tensor/kv_cache_fwd.hpp': [
   (43, '    true,', f'    {A},'), (44, '    false,', f'    {D},'),
   (49, '    true,', f'    {A},'), (50, '    false,', f'    {D},')],
 'h/tron/models/kv_cache.hpp': [
   (1429, '/*reclaimable=*/false);', 'RECLAIMABLE_FALSE);'),
   (1441, '/*reclaimable=*/true);', 'RECLAIMABLE_TRUE);'),
   (1944, 'const_view<Source, true, Dma,', f'const_view<Source, {A}, Dma,'),
   (1952, 'view<Destination, true, Dma,', f'view<Destination, {A}, Dma,'),
   (1960, 'const_view<Source, true, Dma,', f'const_view<Source, {A}, Dma,'),
   (1969, 'view<Destination, true, Dma,', f'view<Destination, {A}, Dma,'),
   (2424, 'const_view<bf16, true, false,', f'const_view<bf16, {A}, {D},'),
   (2547, 'const_view<bf16, true, false,', f'const_view<bf16, {A}, {D},'),
   (2582, 'const_view<Source, true, Dma,', f'const_view<Source, {A}, Dma,'),
   (2600, 'view<Destination, true, Dma,', f'view<Destination, {A}, Dma,'),
   (2618, 'const_view<Source, true, Dma,', f'const_view<Source, {A}, Dma,'),
   (2635, 'view<Destination, true, Dma,', f'view<Destination, {A}, Dma,')],
 'h/tron/models/model.hpp': [
   (2830, 'v_buffer_t::scalar, true,', f'v_buffer_t::scalar, {A},')],
 'h/tron/scheduler/full.hpp': [
   (2762, 'view<bf16, true, false,', f'view<bf16, {A}, {D},')],
 'h/tron/tensor/v_vnni.hpp': [
   (311, 'const_view<Source, true, Dma,', f'const_view<Source, {A}, Dma,'),
   (378, 'view<Destination, true, Dma,', f'view<Destination, {A}, Dma,')],
 't/t_llama_unit.cpp': [
   (98, 'const_view<T, true, false,', f'const_view<T, {A}, {D},'),
   (99, 'const_view<T, true, false,', f'const_view<T, {A}, {D},'),
   (103, 'view<T, true, false,', f'view<T, {A}, {D},'),
   (104, 'view<T, true, false,', f'view<T, {A}, {D},'),
   (156, 'view<bf16, true, false,', f'view<bf16, {A}, {D},')],
 't/t_amx_numerics.cpp': [
   (234, 'tron::const_view<tron::bf16, true, false,', f'tron::const_view<tron::bf16, tron::{A}, tron::{D},')],
 't/t_amx_dispatch_dtype.cpp': [
   (103, 'const_view<bf16, true, false,', f'const_view<bf16, {A}, {D},')],
 't/heterogeneous_scheduler_compile.cpp': [
   (452, 'const_view<float, true, false,', f'const_view<float, {A}, {D},')],
}
# Insertions (after line N at tip), applied after the replacements, bottom-up.
INSERTS = {
 'h/tron/tensor/kv_cache_fwd.hpp': [(25, [
   '',
   '// Values for the aligned and dma template flags of view and const_view',
   '// (view.hpp, and views.hpp for the dma flag).',
   f'inline constexpr bool {A} = true;',
   f'inline constexpr bool {D} = false;'])],
 'h/tron/models/kv_cache.hpp': [(1420, [
   "  // Values of construct_kv_blocks' reclaimable argument: the retained arena",
   '  // (false) or one reclaimable chunk (true).',
   '  static constexpr bool RECLAIMABLE_FALSE = false;',
   '  static constexpr bool RECLAIMABLE_TRUE = true;',
   ''])],
}
n_lit = 0
for f, edits in EDITS.items():
    p = os.path.join(R, f)
    lines = open(p).read().split('\n')
    for ln, old, new in edits:
        line = lines[ln - 1]
        assert line.count(old) == 1, (f, ln, line)
        n_lit += old.count('true') + old.count('false')
        lines[ln - 1] = line.replace(old, new)
    for after, block in sorted(INSERTS.get(f, []), reverse=True):
        lines[after:after] = block
    open(p, 'w').write('\n'.join(lines))
print('lines edited:', sum(len(v) for v in EDITS.values()), 'literals replaced:', n_lit)
