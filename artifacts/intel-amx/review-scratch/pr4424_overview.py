from build_pr4424_diagrams import *

TENSOR='h/tron/tensor/k_vnni.hpp'
CACHE='h/tron/models/kv_cache.hpp'
MODEL='h/tron/models/model.hpp'
COMMON='h/tron/models/common.hpp'
def N(name,kind,description,file,line,end_line=None):
 d=dict(name=name,kind=kind,description=description,file=file,line=line)
 if end_line:d['end_line']=end_line
 return d
def F(nodes,edges):return dict(nodes=nodes,edges=edges)
def D(title,caption,*flows):return dict(title=title,caption=caption,flows=list(flows))

BASE_DIAGRAMS=[
 D('Storage: one owner per page, slot and head',
   'The type holds 64 × 128 bf16 values. The bytes of an unconverted 16-token block still contain contiguous token rows. The page’s block bits determine how to interpret them.',
   F([N('kv_block<page_size, head_size>','cache','Stores the K and V planes for one KV head of one slot.',CACHE,2983,3008),N('k_vnni_tensor<page_size, head_size>','k','Owns the K bytes when layout_on<head_size> is true.',CACHE,2993,3004)],['1 kv_block owns 1 K plane: page_size × head_size bf16 values']),
   F([N('k_vnni_tensor<Rows, Cols>','k','Owns the aligned plane without a separate allocation.',TENSOR,201,236),N('k_vnni_view<T, Rows, Cols>','k','Refers to the same plane and carries its element type.',TENSOR,156,198)],['1 view refers to 1 owner’s plane; 1 owner can supply 0 or more views']),
   F([N('page','cache','Tracks completion and layout for its storage slots.',CACHE,1940,1973),N('k_vnni_blocks_','cache','Records which 16-token blocks hold packed values.',CACHE,2618,2622)],['1 page has layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 state entries; each entry uses 4 block bits'])
 ),
 D('Two write routes reach the same owner',
   'These are branches inside store_k_block. The full-block path publishes layout only after all KV heads are written. A shorter run follows the block’s existing layout through set_k_row.',
   F([N('store_k_block','function','Stores a run of token rows for every KV head.',MODEL,3232,3245),N('page::set_k_block','function','Stores a complete 16-token block in packed form.',CACHE,2265,2284)],['run contains exactly 16 rows filling one block → full-block store']),
   F([N('store_k_block','function','Stores a run of token rows for every KV head.',MODEL,3232,3245),N('page::set_k_row','function','Writes one typed source row in the recorded layout.',CACHE,2238,2263)],['shorter run → one row store per token and KV head'])
 ),
 D('Saved rows and packed blocks are different states',
   'A converted-block bit implies all 16 saved-row bits. All 16 saved-row bits do not imply conversion has happened. Short writes for a hardware-scored operation skip row-bit recording and deferred conversion.',
   F([N('k_rows_saved_','cache','One bit records each saved row of a storage slot.',CACHE,2608,2617),N('k_vnni_blocks_','cache','One bit records each converted block of that slot.',CACHE,2618,2622)],['16 saved-row bits permit 1 block conversion; its 1 block bit is published afterward']),
   F([N('pending_k_block','work','Captures the page, resolved storage and block to convert.',MODEL,3155,3169),N('page::k_storage_ref','cache','Keeps a physical storage offset with its state index.',CACHE,2137,2148)],['1 queued pending_k_block carries 1 page pointer, 1 storage reference and 1 block number'])
 ),
 D('Read routes follow the recorded layout',
   'Eligibility checks select the dense AMX route only when every block is packed. The software loop handles mixed pages. The source of this dispatch is self_attention.hpp:1903–2049.',
   F([N('page::k_packed','function','Returns a read-only view of one head’s K plane.',CACHE,2108,2123),N('qk_vnni_128x4','function','Computes query-by-token scores from a fully packed page.', 'h/tron/kernels/amx_attn_iface.hpp',250,263)],['AMX eligible + dense page + all 4 block bits set → 4 × 64 scores']),
   F([N('k_vnni::qk_group','function','Scores selected tokens from packed blocks.', 'h/tron/kernels/k_vnni.hpp',34,65),N('s_pages','value','Stores each query head’s score for each page token.', 'h/tron/models/self_attention.hpp',1946,1952)],['1 score per live packed token per query head; other entries stay unchanged']),
   F([N('row_major_row','function','Returns a contiguous row from an unconverted block.',TENSOR,458,472),N('dot_q[offset](k)','function','Computes one query head’s dot product with one K row.','h/tron/models/self_attention.hpp',2027,2032)],['row-major block → one row per relevant token, one dot product per query head'])
 ),
]

def explorer():
 cells=''.join(f'<div class="panel-cell" data-s="{s}" data-c="{c}">s={s}, c={c}</div>' for s in range(4) for c in range(4))
 lanes=''.join(f'<div class="pair-cell" data-t="{t}">{t}</div>' for t in range(16))
 return '''<section class="section" id="layout-explorer"><h2>Base layout: follow one K value</h2><p>This diagram represents a converted block. Change a logical token or dimension to see its physical location. It uses the exact <code>k_vnni::index</code> formula.</p>'''+cite(TENSOR,24,32)+' · '+cite(TENSOR,132,141)+'''<div class="explorer"><div class="controls"><label>token (0–63) <input type="number" min="0" max="63" step="1" id="token" value="17"></label><label>dim (0–127) <input type="number" min="0" max="127" step="1" id="dim" value="35"></label></div><div class="explorer-grid"><div><h3>plane: 16 panels, 1 KiB each</h3><p class="small">Rows: dimension step <code>s</code>. Columns: token block <code>c</code>. The selected panel is outlined in blue.</p><div class="panel-grid">'''+cells+'''</div></div><div><h3>One pair row: 16 token lanes</h3><p class="small" id="pair-label">Each lane contains 2 bf16 values.</p><div class="pair-grid">'''+lanes+'''</div><p class="small" id="element-note"></p><div class="formula" id="coordinates"></div></div></div><div class="formula">(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j</div><p class="takeaway" id="index-result" aria-live="polite"></p><p class="small">The panel cells represent byte capacity. The lane cells represent the 16 token positions within one 64-byte pair row. They are different magnifications of the same plane.</p></div><div class="table-scroll"><table><thead><tr><th>Code name</th><th>Definition</th><th>Cardinality</th></tr></thead><tbody><tr><td><code>plane</code></td><td>One head’s K values for one page</td><td>64 tokens × 128 dimensions × 2 bytes = 16 KiB</td></tr><tr><td><code>s, c</code></td><td>Dimension step and token block</td><td>4 steps × 4 blocks = 16 panels</td></tr><tr><td><code>dp</code></td><td>Pair row within one panel</td><td>16 pair rows × 64 bytes = 1 KiB per panel</td></tr><tr><td><code>t, j</code></td><td>Token lane and value within its dimension pair</td><td>16 lanes × 2 bf16 values = 64 bytes per pair row</td></tr></tbody></table></div></section>'''

def sequence():
 return D('Forward-end conversion follows both waits',
  'This is source dependency order, not elapsed time. The plugin must finish its spawned pool work before run returns. Cooperative GOF staging must also finish before conversion changes row addresses. model.hpp:1836–1847 gives this call order. No timing measurements are available for this report.',
  F([N('plugin_state.run(q_batches)','function','Runs the plugin, which must join its spawned pool work.',MODEL,1822,1836),N('wait_for_coop_gof','function','Drains queued GOF staging and waits for in-flight staging submissions.',MODEL,3578,3592),N('convert_pending_k_blocks','function','Converts queued complete blocks and clears the queue.',MODEL,3171,3179)],['run returns after its spawned pool work finishes','staging has drained → no earlier staging reader still uses these rows'])
 )

def render_index(data,stats):
 toc=[('short-version','Short version and source revisions'),('files','The three selected files'),('terms','Words used here and color key'),('base-models','Base data and function diagrams'),('layout-explorer','Interactive K layout diagram'),('sequence','Forward-end sequencing'),('coverage','Coverage and other PR files')]
 s=top('PR4424 · diagrams beside the code',toc,'diagramming-code-changes.html')
 s+='<header class="hero" id="short-version"><div class="eyebrow">PR4424 · code change atlas</div><h1>From K rows to typed storage<br>and shared writes</h1><h2>Short version</h2><div class="short-version"><p>PR4424 gives eligible K planes a typed owner that can hold row-major and packed blocks.</p><p>Cache state records which layout each block uses.</p><p>The model shares writes with helpers, then completes token bookkeeping and any deferred conversion.</p></div>'+revision_note()+'<p class="scope-note">This report follows the source at the current PR head, including the short-write behavior merged into this head. It explains code, not benchmark results. The three detailed pages cover all changes in their selected files.</p></header>'
 s+='<section id="files" class="section"><h2>The three selected files</h2><p>These files define the storage representation, its cache lifecycle, and the model’s writing protocol. That gives the diagrams a continuous path from bytes to callers.</p><div class="file-cards">'
 reasons={
  'tensor':('k','Defines the bytes and typed operations','The new owner, views, address formula, row transfers, block stores and in-place conversions.'),
  'cache':('cache','Connects layout to page state','Storage selection, saved-row and converted-block masks, accessors, suffix reuse and page copies.'),
  'model':('work','Coordinates the writers','Work-unit boundaries, helper publication and joining, completion marks and deferred conversion.')}
 for key,d in data.items():
  cl,title,why=reasons[key];r=next(x for x in stats if x['file']==d['file'])
  s+='<article class="file-card '+cl+'"><div class="eyebrow">'+title+'</div><h3><a href="'+FILES[key][1]+'">'+Path(d['file']).name+'</a></h3><p>'+why+'</p><p><strong>'+str(r['units'])+' logical changes · '+str(r['diagrams'])+' diagrams</strong></p><p class="small"><code>'+d['file']+'</code></p></article>'
 s+='</div></section><section id="terms" class="section"><h2>Words used here</h2>'+terms(COMMON_TERMS+[{'name':'layout_on<head_size>','meaning':'The compile-time storage gate. TRON_K_VNNI enables it only for 128-dimension heads.'},{'name':'slot','meaning':'A key/value storage position associated with an attention operation and a head geometry.'},{'name':'pending_k_block','meaning':'A saved page pointer, physical storage reference and block number awaiting conversion.'},{'name':'EAGLE_STORAGE_SLOTS_1','meaning':'One extra layout-state entry beyond the logical slots, reserved for EAGLE storage.'}])+legend()+'</section>'
 s+='<section id="base-models" class="section"><h2>Base data and function diagrams</h2><div class="base-grid">'+''.join(map(diagram,BASE_DIAGRAMS))+'</div><p class="small">Dispatch definitions: '+cite('h/tron/models/self_attention.hpp',1903,2049)+'. The detailed file pages reuse these concepts and expand each changed operation.</p></section>'
 s+=explorer()
 s+='<section class="section" id="sequence"><h2>Forward-end sequencing</h2>'+diagram(sequence())+'</section>'
 s+='<section class="section" id="coverage"><h2>Coverage and scope</h2><p>The range audit counts every nonblank changed line in the three selected files. Each substantive unit has a diagram. Each page also includes its complete diff.</p>'+coverage_table(stats)
 s+='<div class="coverage-bars">'
 for r in stats:
  a=r['covered_added_nonblank']+r['covered_removed_nonblank'];b=r['added_nonblank']+r['removed_nonblank']
  s+='<div class="coverage-row"><code>'+Path(r['file']).name+'</code><div class="bar"><div class="bar-fill" style="width:'+str(100*a/b)+'%"></div></div><strong>'+str(a)+' / '+str(b)+' changed lines mapped</strong></div>'
 s+='</div><p class="small">The bars show coverage, not performance. Exact counts come from the pinned source diff. Blank-only changes remain in the complete diff.</p>'
 s+='<h3>Other files in this PR</h3><p>The PR changes 28 files. The remaining 25 files are listed here for scope visibility. They do not receive separate per-change diagrams because the requested selection is three files.</p><div class="table-scroll"><table><thead><tr><th>File</th><th>Added lines</th><th>Removed lines</th><th>Source</th></tr></thead><tbody>'
 selected={v[0] for v in FILES.values()}
 for line in git('diff','--numstat',BASE,HEAD).splitlines():
  add,delete,file=line.split('\t')
  if file in selected:continue
  s+='<tr><td><code>'+file+'</code></td><td>'+add+'</td><td>'+delete+'</td><td>'+cite(file,1,label='Pinned file')+'</td></tr>'
 s+='</tbody></table></div><p class="small">Line totals include comments and blank lines. No source files were changed to produce this report.</p></section>'+end()
 (OUT/'diagramming-code-changes.html').write_text(s)
