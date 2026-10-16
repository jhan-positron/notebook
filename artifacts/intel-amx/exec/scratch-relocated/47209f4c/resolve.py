import re, sys, pathlib
root = pathlib.Path('/home/jhan/workspace/ai-runs/tron-issue4525')
HUNK = re.compile(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> origin/main\n', re.S)

def resolve(path, chooser, extra=None):
    p = root / path
    s = p.read_text()
    n = [0]
    def repl(m):
        n[0] += 1
        return chooser(n[0], m.group(1), m.group(2))
    s = HUNK.sub(repl, s)
    if extra: s = extra(s)
    assert '<<<<<<<' not in s and '>>>>>>>' not in s, path
    p.write_text(s)
    print(path, 'hunks', n[0])

def strip_if16(s):
    # drop a bare "#if TRON_CHUNK_SIZE == 16" line when it is followed by a block whose "#else...#endif" we delete elsewhere
    return s

# ---- kv_cache.hpp
def kv(i, ours, theirs):
    if i == 1:   # ours: #else chunk-8 view accessors ... #endif ; theirs: main's old pointer set_v/get_v decls -> neither
        return ''
    if i == 2:   # ours: #if + copy comment ; theirs: main's comment -> ours' comment without the guard
        return ours.replace('#if TRON_CHUNK_SIZE == 16\n', '')
    if i == 3:   # ours: #else memcpy branch #endif -> neither
        return ''
    if i == 4:   # ours: #else AVX2 scaled_v_expr ctor #endif -> neither
        return ''
    if i == 5:   # kv_block members: ours without the guard
        o = ours.replace('#if TRON_CHUNK_SIZE == 16\n', '')
        o = re.sub(r'#else\n  // V is row-major, indexed as \[p \* head_size \+ i\].\n  alignas\(kv_block_alignment\) bf16 v\[page_size \* head_size\];\n#endif\n', '', o)
        assert '#else' not in o and '#endif' not in o
        return o
    raise SystemExit('unexpected kv hunk %d' % i)

def kv_extra(s):
    old = ('#if TRON_CHUNK_SIZE == 16\n'
           '        bf16* v = detail::v_vnni_access::plane(block.v.as_view());\n'
           '#else\n'
           '        bf16* v = block.v;\n'
           '#endif\n')
    assert s.count(old) == 1; s = s.replace(old, '        bf16* v = detail::v_vnni_access::plane(block.v.as_view());\n')
    old = '  // The actual V data for a token in this page.\n#if TRON_CHUNK_SIZE == 16\n'
    assert s.count(old) == 1; s = s.replace(old, '  // The actual V data for a token in this page.\n')
    old = ('#if TRON_CHUNK_SIZE == 16\n'
           '  return detail::scaled_v_expr<page_size, geometry.head_size>(\n'
           '      scales, kv_block<geometry>(slot, kv_head).v.as_view(), count(), scratch);\n'
           '#else\n'
           '  return detail::scaled_v_expr<page_size, geometry.head_size>(scales,\n'
           '      const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,\n'
           '          seq<page_size, geometry.head_size>>{kv_block<geometry>(slot, kv_head).v},\n'
           '      count(), scratch);\n'
           '#endif\n')
    assert s.count(old) == 1, 'scaled_v'
    s = s.replace(old, '  return detail::scaled_v_expr<page_size, geometry.head_size>(\n'
                       '      scales, kv_block<geometry>(slot, kv_head).v.as_view(), count(), scratch);\n')
    assert 'TRON_CHUNK_SIZE' not in s
    return s
resolve('h/tron/models/kv_cache.hpp', kv, kv_extra)

# ---- model.hpp
def model(i, ours, theirs):
    assert i == 1
    o = ours.split('#else\n')[0].replace('#if TRON_CHUNK_SIZE == 16\n', '')
    return o
def model_extra(s):
    old = '#if TRON_CHUNK_SIZE == 16\n      // The executor\'s V buffer holds'
    assert s.count(old) == 1; s = s.replace(old, '      // The executor\'s V buffer holds')
    old = ('      using v_buffer_t = std::remove_cvref_t<decltype(vs[token_job_id(0)])>;\n#endif\n')
    assert s.count(old) == 1; s = s.replace(old, '      using v_buffer_t = std::remove_cvref_t<decltype(vs[token_job_id(0)])>;\n')
    assert 'TRON_CHUNK_SIZE' not in s
    return s
resolve('h/tron/models/model.hpp', model, model_extra)

# ---- self_attention.hpp: drop the #error guard (main removed it)
resolve('h/tron/models/self_attention.hpp', lambda i, o, t: t)

# ---- heterogeneous_scheduler_compile.cpp: both include sets, sorted
resolve('t/heterogeneous_scheduler_compile.cpp', lambda i, o, t: t + o)

# ---- t_amx_dispatch_dtype.cpp: main's forward_scope block, our comment kept inside it
def dtype(i, ours, theirs):
    comment = ('      // batch_queries (the batch\'s query mask) only matters when a section is\n'
               '      // large enough to dismiss workless ranges; one page and one query never is.\n')
    marker = '      state.self_attn_state.template apply_page_range<geometry>('
    assert theirs.count(marker) == 1
    return theirs.replace(marker, comment + marker)
resolve('t/t_amx_dispatch_dtype.cpp', dtype)

# ---- t_llama_unit.cpp
def llama(i, ours, theirs):
    if i == 1:
        return ours.split('#else\n')[0]
    if i == 2:
        return ours.replace('#endif\n', '')
    if i == 3:
        return ours.split('#else\n')[0].replace('#if TRON_CHUNK_SIZE == 16\n', '')
    raise SystemExit('unexpected llama hunk')
def llama_extra(s):
    old = '#if TRON_CHUNK_SIZE == 16\n// The typed packed-V operations'
    assert s.count(old) == 1; s = s.replace(old, '// The typed packed-V operations')
    old = '}\n#endif  // TRON_CHUNK_SIZE == 16\n'
    assert s.count(old) == 1; s = s.replace(old, '}\n')
    assert 'TRON_CHUNK_SIZE' not in s
    return s
resolve('t/t_llama_unit.cpp', llama, llama_extra)

# ---- v_vnni.hpp (no conflict): drop the 16-lane guard, now always true on main
p = root / 'h/tron/tensor/v_vnni.hpp'; s = p.read_text()
old = '\n#if TRON_CHUNK_SIZE == 16\n\n'; assert s.count(old) == 1; s = s.replace(old, '\n')
old = '\n#endif  // TRON_CHUNK_SIZE == 16\n\n'; assert s.count(old) == 1; s = s.replace(old, '\n')
p.write_text(s); print('v_vnni.hpp guards removed')
