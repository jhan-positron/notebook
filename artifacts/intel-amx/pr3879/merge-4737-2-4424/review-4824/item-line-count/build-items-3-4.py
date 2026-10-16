from pathlib import Path
import difflib
import json
import subprocess

REPO = Path('/home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424/tron')
OUT = REPO.parent / 'review-4824/item-line-count'
HEAD = '9d5c7a389b23078398028bce0d1fe1a6c5c64e31'
BASE = 'be0d5565b355a90b6018529d3310565c3f5909cb'
TENSOR = 'h/tron/tensor/k_vnni.hpp'
CACHE = 'h/tron/models/kv_cache.hpp'
TEST = 't/t_k_vnni_layout.cpp'
LLAMA = 't/t_llama_unit.cpp'

def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=REPO, text=True, capture_output=True, check=check)

def source(rev, path):
    result = git('show', f'{rev}:{path}', check=False)
    if result.returncode:
        assert rev == BASE and path in {TENSOR, TEST}, result.stderr
        return ''
    return result.stdout

def replace_once(text, old, new):
    assert text.count(old) == 1, (old[:120], text.count(old))
    return text.replace(old, new, 1)

def diff_counts(old, new):
    result = git('diff', '--no-index', '--numstat', str(old), str(new), check=False)
    assert result.returncode in (0, 1), result.stderr
    if not result.stdout.strip():
        return {'added': 0, 'deleted': 0}
    fields = result.stdout.split('\t')
    return {'added': int(fields[0]), 'deleted': int(fields[1])}

def code_lines(text):
    return sum(bool(line.strip()) and not line.lstrip().startswith('//') for line in text.splitlines())

original_pr = {'added': 0, 'deleted': 0}
for line in git('diff', '--numstat', BASE, HEAD).stdout.splitlines():
    added, deleted, _ = line.split('\t', 2)
    original_pr['added'] += int(added)
    original_pr['deleted'] += int(deleted)

def write_item(name, drafts, assumptions):
    root = OUT / name
    stats = []
    patch = ''
    for path, draft in drafts.items():
        head = source(HEAD, path)
        base = source(BASE, path)
        for directory, contents in [('original', head), ('base', base), ('draft', draft)]:
            target = root / directory / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents)
        before = diff_counts(root / 'base' / path, root / 'original' / path)
        after = diff_counts(root / 'base' / path, root / 'draft' / path)
        edit = diff_counts(root / 'original' / path, root / 'draft' / path)
        stats.append({
            'file': path,
            'edit': edit,
            'pr_before': before,
            'pr_after': after,
            'net_source_reduction': len(head.splitlines()) - len(draft.splitlines()),
            'net_nonblank_noncomment_reduction': code_lines(head) - code_lines(draft),
            'pr_changed_lines_reduction': sum(before.values()) - sum(after.values()),
        })
        patch += ''.join(difflib.unified_diff(head.splitlines(keepends=True), draft.splitlines(keepends=True), fromfile='a/' + path, tofile='b/' + path))
    patch_path = root / 'draft.patch'
    patch_path.write_text(patch)
    check = git('apply', '--check', str(patch_path), check=False)
    assert check.returncode == 0, check.stderr
    totals = {key: sum(row[key] for row in stats) for key in ['net_source_reduction', 'net_nonblank_noncomment_reduction', 'pr_changed_lines_reduction']}
    totals['edit'] = {key: sum(row['edit'][key] for row in stats) for key in ['added', 'deleted']}
    totals['draft_pr'] = {key: original_pr[key] + sum(row['pr_after'][key] - row['pr_before'][key] for row in stats) for key in ['added', 'deleted']}
    result = {
        'head': HEAD,
        'base': BASE,
        'method': 'Exact physical line counts from one concrete, uncompiled draft. Counts are computed with git diff --no-index --numstat. PR diff size is additions + deletions against the merge base. Physical counts include comments and blank lines. Code count excludes blank and full-line // comments.',
        'assumptions': assumptions,
        'original_pr': original_pr,
        'files': stats,
        'totals': totals,
        'validation': {'git_apply_check': check.returncode == 0, 'builds_run': False, 'runtime_tests_run': False, 'performance_verified': False},
    }
    (root / 'counts.json').write_text(json.dumps(result, indent=2) + '\n')
    print(name, json.dumps(totals))

# Item 3: retain the full-block operation and its meaningful tests.
tensor3 = source(HEAD, TENSOR)
tensor3 = replace_once(tensor3, '''// Store the K rows of up to 16 tokens of one token block c (tokens c * 16 + t
// for the bits t set in `present`) into a packed plane with full-line stores.
// For each of the 4 dimension steps, the 16 rows' 16 dimension pairs (one
// 64-byte load per row) are transposed in registers into the panel's 16 pair
// rows. Each pair row is then written as one 64-byte store (masked to the
// present tokens' lanes when the block is partial). The absent tokens' slots
// are not written. rows[t] points at the 128 bf16 of token t, one native row
// in dimension order (not packed storage). It may be null for an absent
// token. Compared with store_row per token, a full block issues 64 stores of
// whole lines instead of 64 scatters, each writing 4 bytes into 16 lines
// (every one of the block's 64 lines receives 16 partial writes). The same
// 4 KiB is written. The write pattern differs.
''', '''// Store all 16 K rows of token block c (tokens c * 16 + t) into a packed
// plane with full-line stores. For each of the 4 dimension steps, the 16
// rows' 16 dimension pairs (one 64-byte load per row) are transposed in
// registers into the panel's 16 pair rows. Each pair row is then written as
// one 64-byte store. rows[t] points at the 128 bf16 of token t, one native
// row in dimension order (not packed storage). Every row must be present.
// Compared with store_row per token, a full block issues 64 stores of whole
// lines instead of 64 scatters, each writing 4 bytes into 16 lines (every
// one of the block's 64 lines receives 16 partial writes). The same 4 KiB
// is written. The write pattern differs.
''')
tensor3 = replace_once(tensor3, '    size_t c,\n    __mmask16 present,\n', '    size_t c,\n')
tensor3 = replace_once(tensor3, '''      r[t] = ((present >> t) & 1u)
                 ? _mm512_loadu_si512(rows[t] + s * k_vnni::STEP_DIMS_32)
                 : _mm512_setzero_si512();
''', '''      r[t] = _mm512_loadu_si512(rows[t] + s * k_vnni::STEP_DIMS_32);
''')
tensor3 = replace_once(tensor3, '''    if (present == k_vnni::FULL_BLOCK_0XFFFF) {
      for (size_t dp = 0; dp < k_vnni::STEP_PAIRS_16; ++dp) {
        _mm512_storeu_si512(panel + dp * k_vnni::ROW_ELEMS_32, r[dp]);
      }
    } else {
      for (size_t dp = 0; dp < k_vnni::STEP_PAIRS_16; ++dp) {
        _mm512_mask_storeu_epi32(panel + dp * k_vnni::ROW_ELEMS_32, present, r[dp]);
      }
    }
''', '''    for (size_t dp = 0; dp < k_vnni::STEP_PAIRS_16; ++dp) {
      _mm512_storeu_si512(panel + dp * k_vnni::ROW_ELEMS_32, r[dp]);
    }
''')
tensor3 = replace_once(tensor3, '  store_block(plane, c, k_vnni::FULL_BLOCK_0XFFFF, row_ptrs);', '  store_block(plane, c, row_ptrs);')
cache3 = replace_once(source(HEAD, CACHE), '''    store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c,
        k_vnni::FULL_BLOCK_0XFFFF, rows);''', '''    store_block(kv_block<geometry>(slot, kv_head).k.as_view(), c, rows);''')
test3 = replace_once(source(HEAD, TEST), 'using tron::k_vnni::FULL_BLOCK_0XFFFF;\n', '')
test3 = replace_once(test3, '''  // must leave the plane exactly as store_row per present token does. It
  // must not touch the slots of absent tokens (poison stays poison). The
  // masks cover: full block, single tokens, halves, alternating lanes, the
  // empty block, and random subsets.
''', '''  // must leave the plane exactly as store_row for all 16 tokens does.
  // Every other block must remain unchanged (poison stays poison).
''')
start = test3.index('  constexpr unsigned TOKEN_0_0X0001 = 0x0001;\n')
end = test3.index('  auto ref = std::make_unique<plane_and_rows>();\n', start)
test3 = test3[:start] + test3[end:]
start = test3.index('  std::vector<unsigned> masks = {FULL_BLOCK_0XFFFF,')
end = test3.index('  SECTION("a block save on top of other blocks changes only its own block")', start)
test3 = test3[:start] + '''  size_t checked = 0;
  for (size_t c = 0; c < TOKEN_BLOCKS_4; ++c) {
    poison_plane(ref->plane, POISON_0XA5A5);
    blk->plane = ref->plane;  // the owner copy: same bytes
    const tron::bf16* rows[BLOCK_TOKENS_16];
    for (size_t t = 0; t < BLOCK_TOKENS_16; ++t) {
      const size_t tok = c * BLOCK_TOKENS_16 + t;
      rows[t] = ref->rows + tok * HEAD_SIZE_128;
      tron::store_row(ref->plane.as_view(), tok, row_of(*ref, tok));
    }
    tron::store_block(blk->plane.as_view(), c, rows);
    REQUIRE(std::memcmp(&blk->plane, &ref->plane, sizeof(ref->plane)) == 0);
    ++checked;
  }
  REQUIRE(checked == TOKEN_BLOCKS_4);
''' + test3[end:]
test3 = replace_once(test3, '    tron::store_block(blk->plane.as_view(), NEW_BLOCK_2, FULL_BLOCK_0XFFFF, rows);', '    tron::store_block(blk->plane.as_view(), NEW_BLOCK_2, rows);')
assert 'FULL_BLOCK_0XFFFF' not in test3
write_item('item3', {TENSOR: tensor3, CACHE: cache3, TEST: test3}, [
    'Make store_block accept exactly one complete 16-token block, matching both production call sites.',
    'Retain the full-block mask constant: page completion-bit calculations still use it.',
    'Update both production callers and both block-store test callers.',
    'Remove partial-mask-only fixtures and cases; retain full-block equality for all four blocks, poisoned-neighbor preservation, and overwriting one populated block without changing the others.',
    'Keep row-major tail, conversion, cache-copy, fallback-score, and all other tests unchanged.'
])

# Item 4: remove only the unused packed-K helper and its direct test.
tensor4 = source(HEAD, TENSOR)
start = tensor4.index('// Copy one token between packed K planes (or within one plane):')
end = tensor4.index('// Note [Row-major tail block]', start)
tensor4 = tensor4[:start] + tensor4[end:]
tensor4 = tensor4.replace('store_row, load_row, store_block, copy_token', 'store_row, load_row, store_block')
tensor4 = replace_once(tensor4, '  // rows enter through store_row, store_block and copy_token.', '  // rows enter through store_row and store_block.')
assert 'copy_token' not in tensor4
test4 = source(HEAD, TEST)
start = test4.index('  SECTION("copy_token moves one token between planes, other tokens untouched") {\n')
end = test4.index('\n}\n\nTEST_CASE("VNNI K block save', start)
assert test4[:end].endswith('  }')
test4 = test4[:start] + test4[end + 1:]
assert 'copy_token' not in test4
cache4 = replace_once(source(HEAD, CACHE), '''// operations of h/tron/tensor/k_vnni.hpp (store_row, load_row, store_block,
// copy_token). No raw plane pointer leaves the cache. detail::k_vnni_access is
''', '''// operations of h/tron/tensor/k_vnni.hpp (store_row, load_row, store_block).
// No raw plane pointer leaves the cache. detail::k_vnni_access is
''')
llama4 = replace_once(source(HEAD, LLAMA), '''  // No view writes an element. Rows enter through store_row, store_block and
  // copy_token.
''', '''  // No view writes an element. Rows enter through store_row and store_block.
''')
write_item('item4', {TENSOR: tensor4, CACHE: cache4, TEST: test4, LLAMA: llama4}, [
    'Remove the unused packed-K copy_token helper and its only direct test section.',
    'Update all comments that refer to the removed K helper.',
    'Keep packed-V copy_token and its callers/tests unchanged.',
    'Keep production page-copy logic and actual cache-append/copy coverage unchanged.'
])
