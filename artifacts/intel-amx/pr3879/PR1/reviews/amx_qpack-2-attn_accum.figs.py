# Figure generator for amx_qpack-2-attn_accum.html (run: python3 this_file.py; needs cairosvg for the PNG check).
# Generates the three SVG figures for reviews/amx_qpack-2-attn_accum.html and renders PNGs for inspection.
import html, cairosvg, sys, os
OUT = os.path.dirname(os.path.abspath(__file__))
SIZES = {"v":"16 B handle + 8192 B heap block","s":"128 B (32 floats)","m":"128 B (32 floats)","valid":"8 B (8 bools)"}
STYLE = """<style>
text{font-family:system-ui,sans-serif;fill:#0b0b0b;font-size:12.5px}
.hd{font-size:13px;font-weight:600}.cap{font-size:12px;fill:#52514e}.tt{font-size:11.5px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.box{fill:#ffffff;stroke:#0b0b0b;stroke-width:1.2}.soft{fill:#f4f3ef;stroke:#8a8883;stroke-width:1}
.a{fill:#e8e6f3;stroke:#7570b3;stroke-width:1.2}.b{fill:#cfe8d6;stroke:#1b9e77;stroke-width:1.2}.g{fill:#fff4d6;stroke:#d95f02;stroke-width:1.2}
.red{fill:#fde2e1;stroke:#c8322f;stroke-width:1.4}
.flow{stroke:#0b0b0b;stroke-width:1.3;fill:none}.dep{stroke:#7570b3;stroke-width:1.3;fill:none}.depb{stroke:#1b9e77;stroke-width:1.3;fill:none}.depg{stroke:#d95f02;stroke-width:1.4;fill:none}
.dash{stroke-dasharray:6 4}
</style>"""
def svg(w,h,body,mid):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" role="img">
{STYLE}
<defs><marker id="ar{mid}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#0b0b0b"/></marker>
<marker id="arg{mid}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#d95f02"/></marker>
<marker id="arb{mid}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#1b9e77"/></marker></defs>
{body}
</svg>'''
def rect(x,y,w,h,cls,rx=4,extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}" {extra}/>'
def text(x,y,s,cls="",anchor="start",extra=""):
    a = f' text-anchor="{anchor}"' if anchor!="start" else ""
    c = f' class="{cls}"' if cls else ""
    return f'<text x="{x}" y="{y}"{c}{a} {extra}>{html.escape(s)}</text>'
def lines(x,y,rows,cls="",dy=16,anchor="start"):
    return "\n".join(text(x,y+i*dy,r,cls,anchor) for i,r in enumerate(rows))

# ---------------- Figure 1: where each piece of state lives ----------------
b=[]
b.append(rect(20,20,560,500,"soft",6))
b.append(text(32,42,"run_sections(worker w, one layer): for each kv_section (one kv_head, one page range) in worker w's plan","hd"))
b.append(rect(40,60,520,440,"box",6))
b.append(text(52,82,"apply_page_range(items, kv_head, scratchpad = w, page_range)","hd"))
b.append(rect(60,98,480,34,"g"))
b.append(lines(70,113,["if amx_on: amx_qpack.resize(items.size()); begin_region()","(the vector grows only when this minibatch is the largest seen so far)"],"tt",13))
b.append(rect(60,148,480,296,"box"))
b.append(text(72,168,"for each page in page_range  (a page = 64 tokens of K and V)","hd"))
b.append(rect(80,184,440,244,"box"))
b.append(text(92,204,"for each token batch_job_ix in items (the minibatch)","hd"))
b.append(rect(100,218,400,28,"soft")); b.append(text(110,237,"skip if the page is invisible to the token or outside its sliding window","tt"))
b.append(rect(100,254,400,28,"a")); b.append(text(110,273,"sp = attn[scratchpad] row batch_job_ix  (v*, s*, m*, valid of this token)","tt"))
b.append(rect(100,290,400,28,"red")); b.append(text(110,309,"amx_qp = packed_amx_query(amx_qpack[batch_job_ix], ...)","tt"))
b.append(rect(100,326,400,42,"box")); b.append(lines(110,343,["apply_page_tok: QK scores (AMX kernel or AVX dotter), scale, max, exp,","PV, then fold this page into v*, s*, m* of sp"],"tt",14))
b.append(rect(100,376,400,28,"a")); b.append(text(110,395,"sp.mark_valid_for(kv_head) once a real score has landed","tt"))
b.append(rect(60,456,480,28,"g")); b.append(text(70,475,"if amx_on: end_region()","tt"))
# right column: storage classes
b.append(rect(640,60,440,96,"soft",6))
b.append(text(652,80,"Stack of this call (gone when apply_page_range returns)","hd"))
b.append(lines(652,100,["amx_packed: std::bitset, which tokens are packed in THIS call","s_pages, amx_o, corr_arr: one page's scores, PV output, corrections"],"tt",15))
b.append(rect(640,190,440,150,"a",6))
b.append(text(652,210,"attn[scratchpad]: worker w's attn_accum","hd"))
b.append(lines(652,228,["allocated once in the state constructor, attn.resize(num_workers);","lives as long as the model state; arrays indexed by token in minibatch:","v_stars[tok], s_stars[tok], m_stars[tok], valid[tok][kv_head]"],"tt",15))
b.append(rect(652,282,416,44,"red dash",4))
b.append(lines(662,300,["amx_qpack[tok]  <- Ben's proposal: a 5th per-token array (or vector),","written and read only by worker w, inside apply_page_range"],"tt",15))
b.append(rect(640,380,440,110,"g",6))
b.append(text(652,400,"thread_local inside apply_page_range  (today)","hd"))
b.append(lines(652,418,["one std::vector<amx_qpack_slot> per OS thread per instantiation,","lives as long as the thread; heap storage only on threads that ran","the AMX path; items.size() slots of 4096 B, capacity kept after the call"],"tt",15))
# arrows (corridor x 500..640)
b.append(f'<path d="M500,268 L640,268" class="dep" marker-end="url(#ar1)"/>')
b.append(f'<path d="M500,308 L590,308 L590,435 L640,435" class="depg" marker-end="url(#arg1)"/>')
b.append(text(596,380,"today","cap"))
b.append(f'<path d="M500,300 L652,300" class="depg dash" marker-end="url(#arg1)"/>')
b.append(text(562,293,"proposed","cap"))
b.append(text(20,545,"Figure 1. One attention worker's loop for one layer (left) and the three places its state can live (right). Solid orange arrow: where the pack buffer lives today.","cap"))
b.append(text(20,561,"Dashed orange arrow: Ben's proposal. Purple: the existing per-worker scratchpad rows.","cap"))
fig1 = svg(1100,576,"\n".join(b),1)

# ---------------- Figure 2: attn_accum anatomy ----------------
b=[]
b.append(text(20,30,"attn_accum: one per pool worker (attn[0..num_workers-1]) plus two inside every hw_attn_results (data, unpack_tmp)","hd"))
x0=400; x1=930; cw=(x1-x0)
def strip(y,h,cls,name,typ,meaning,right,cells=16,dashed=False):
    out=[]
    out.append(text(20,y+h/2-2,name,"tt"))
    out.append(text(20,y+h/2+13,typ,"cap"))
    out.append(rect(x0,y,cw,h,cls+(" dash" if dashed else ""),3))
    step=cw/cells
    for i in range(1,cells):
        out.append(f'<line x1="{x0+i*step:.1f}" y1="{y}" x2="{x0+i*step:.1f}" y2="{y+h}" stroke="#8a8883" stroke-width="0.8" stroke-dasharray="2 3"/>')
    out.append(text(x0+cw/2,y+h/2+4,meaning,"cap","middle"))
    out.append(text(x1+10,y+h/2+4,right,"cap"))
    return "\n".join(out)
b.append(text(x0,58,"index = the token's position in the minibatch (batch_job_ix), 0 .. max_minibatch_size-1","cap"))
b.append(text(x0,72,"0","cap")); b.append(text(x1,72,"max-1","cap","end")); b.append(text(x1+10,58,"bytes per token (32 heads x 128)","cap"))
y=80
b.append(strip(y,40,"a","v_stars[tok]","btensor handle -> heap block of 4096 bf16","running weighted sum of V, all query heads","%(v)s"))
y+=54; b.append(strip(y,28,"a","s_stars[tok]","float x scratch_query_heads","running softmax denominator, per query head","%(s)s"))
y+=42; b.append(strip(y,28,"a","m_stars[tok]","float x scratch_query_heads","running maximum score, per query head","%(m)s"))
y+=42; b.append(strip(y,22,"a","valid[tok][kv_head]","bool x scratch_kv_heads","is there a state for that kv_head yet","%(valid)s"))
y+=44; b.append(strip(y,40,"red","amx_qpack[tok]  (proposed)","amx_qpack_slot: 2048 bf16, 64-B aligned","the token's 4 query heads in the tile-operand layout","4096 B",dashed=True))
y+=62
b.append(text(20,y,"Every row is one entry per token of the minibatch. The four existing rows are the reduction state: join_page_ranges reads them after all sections are done.","cap"))
b.append(text(20,y+16,"The proposed row is scratch: written once per (token, call), read by the QK kernel during the call, never joined. The index space is the same.","cap"))
fig2 = svg(1210,y+30,"\n".join(b) % SIZES,2)

# ---------------- Figure 3: lifetime lanes ----------------
b=[]
gx=250; W=1080-gx
b.append(text(20,26,"One worker, one layer, one token t. Time runs left to right (schematic, not to scale).","hd"))
# header: sections
secs=[("section S0: kv_head 0",0.0,0.42,["p0","p1","p2","p3"]),("section S1: kv_head 1",0.44,0.86,["p0","p1","p2","p3"]),("join",0.88,1.0,[])]
for name,a,z,pages in secs:
    xa=gx+a*W; xz=gx+z*W
    b.append(rect(xa,44,xz-xa,26,"soft",3)); b.append(text((xa+xz)/2,62,name,"cap","middle"))
    n=len(pages)
    for i,p in enumerate(pages):
        px=xa+(xz-xa)*i/n; pw=(xz-xa)/n
        b.append(rect(px+2,74,pw-4,18,"box",2)); b.append(text(px+pw/2,87,p,"cap","middle"))
lane_y=[110,170,230]
labels=[["amx_packed bitset","(stack of the call)"],["amx_qpack[t]","(thread_local today,","attn[w] if moved)"],["v*, s*, m* of token t","(attn[w] row t)"]]
for (y,lab) in zip(lane_y,labels):
    b.append(text(20,y+14,lab[0],"tt"))
    for i,l in enumerate(lab[1:]): b.append(text(20,y+29+i*14,l,"cap"))
# lane 1: per call
for name,a,z,pages in secs[:2]:
    xa=gx+a*W; xz=gx+z*W
    b.append(rect(xa,lane_y[0]+4,xz-xa,30,"soft",3)); b.append(text((xa+xz)/2,lane_y[0]+23,"cleared at call start, set when t is packed, dies at return","cap","middle"))
# lane 2: pack per call, written at p0
for name,a,z,pages in secs[:2]:
    xa=gx+a*W; xz=gx+z*W; pw=(xz-xa)/4
    b.append(rect(xa+2,lane_y[1]+4,pw-4,30,"red",3)); b.append(text(xa+pw/2,lane_y[1]+23,"pack","cap","middle"))
    b.append(rect(xa+pw,lane_y[1]+4,xz-xa-pw,30,"g",3)); b.append(text(xa+pw+(xz-xa-pw)/2,lane_y[1]+23,"read by the QK kernel at each page","cap","middle"))
# lane 3: v* from S0 p0 to join
xa=gx; xz=gx+W
b.append(rect(xa+2,lane_y[2]+4,gx+0.86*W-xa-2,30,"a",3)); b.append(text(xa+(0.86*W)/2,lane_y[2]+23,"created at S0.p0, folded at every page of S0 and S1 (kv_head 0 heads, then kv_head 1 heads)","cap","middle"))
b.append(rect(gx+0.88*W,lane_y[2]+4,0.12*W,30,"a",3)); b.append(text(gx+0.94*W,lane_y[2]+23,"read by join","cap","middle"))
b.append(text(20,300,"Figure 3. The pack of token t lives exactly one apply_page_range call: a 4 KiB copy made at the first page that needs it, read at each later page, not looked at after the call","cap"))
b.append(text(20,316,"returns (the next section packs again). The reduction state v*, s*, m* lives across all sections of the layer and is consumed by the join. Both are one entry per token per worker.","cap"))
fig3 = svg(1100,330,"\n".join(b),3)

for name,s in [("fig1",fig1),("fig2",fig2),("fig3",fig3)]:
    open(f"{OUT}/{name}.svg","w").write(s)
    cairosvg.svg2png(bytestring=s.encode(), write_to=f"{OUT}/{name}.png", output_width=1400)
    print("wrote",name)

# ---------------- Figure 4: bytes added per attn_accum instance, option A vs option B ----------------
def fmt_bytes(n):
    if n >= 1<<20: return f"{n/(1<<20):g} MiB"
    if n >= 1<<10: return f"{n/(1<<10):g} KiB"
    return f"{n} B"
ROWS = [
  ("attention-worker slot after a full minibatch", "M x 4096", lambda M: M*4096, lambda M: M*4096),
  ("attention-worker slot after 8-token minibatches only (e.g. 8-user decode)", "", lambda M: M*4096, lambda M: 8*4096),
  ("main-helper slot (never runs attention)", "", lambda M: M*4096, lambda M: 24),
  ("copy inside hw_attn_results (hardware-attention models)", "", lambda M: M*4096, lambda M: 24),
  ("any slot of a model that is not AMX-eligible", "", lambda M: M*4096, lambda M: 24),
]
PANELS = [("llama plugin: max_minibatch_size 128 (llama-3.1-8b eligible; llama-70b not: kv_mul 8)", 128),
          ("ingested plugins: max_minibatch_size 1024 (Qwen3-4B eligible; gpt-oss-120b not: head 64)", 1024)]
A_COL="#eb6834"; B_COL="#2a78d6"
b=[]
W=1100; gutter=20; label_w=470; plot_x=gutter+label_w; plot_w=W-plot_x-110
b.append(text(20,24,"Bytes ADDED to one attn_accum instance by the two placements (today's thread_local adds 0 here; its memory lives per OS thread instead)","hd"))
# legend
b.append(f'<rect x="20" y="36" width="14" height="14" rx="3" fill="{A_COL}"/>'); b.append(text(40,48,"option A: std::array<amx_qpack_slot, max_minibatch_size> member (Ben's proposal)","cap"))
b.append(f'<rect x="560" y="36" width="14" height="14" rx="3" fill="{B_COL}"/>'); b.append(text(580,48,"option B: std::vector<amx_qpack_slot> member, sized on first use","cap"))
y=70
for title,M in PANELS:
    b.append(text(20,y+4,title,"hd")); y+=14
    vmax=M*4096
    for name,_,fa,fb in ROWS:
        va=fa(M); vb=fb(M)
        b.append(text(20,y+22,name,"cap"))
        for i,(v,col) in enumerate([(va,A_COL),(vb,B_COL)]):
            by=y+6+i*16
            bw=max(1.5, plot_w*v/vmax)
            # square at baseline, 4px rounded data end: draw as path
            r=4 if bw>8 else 0
            b.append(f'<path d="M{plot_x},{by} h{bw-r} a{r},{r} 0 0 1 {r},{r} v{14-2*r} a{r},{r} 0 0 1 -{r},{r} h-{bw-r} z" fill="{col}"/>')
            b.append(text(plot_x+bw+6,by+11,fmt_bytes(v),"cap"))
        y+=44
    # axis line + tick labels
    b.append(f'<line x1="{plot_x}" y1="{y-4}" x2="{plot_x+plot_w}" y2="{y-4}" stroke="#8a8883" stroke-width="1"/>')
    b.append(text(plot_x,y+10,"0","cap")); b.append(text(plot_x+plot_w,y+10,fmt_bytes(vmax),"cap","end"))
    y+=34
b.append(text(20,y,"Figure 4. Option A spends max_minibatch_size x 4096 bytes in every instance, used or not. Option B spends 24 bytes (an empty vector) until a worker runs the AMX","cap"))
b.append(text(20,y+16,"path, then (largest minibatch seen) x 4096 bytes, which is what the thread_local costs today. Our runs: 55 pool workers per model state (--instance 1,2), no hardware copies.","cap"))
fig4 = svg(W,y+30,"\n".join(b),4)
open(f"{OUT}/fig4.svg","w").write(fig4)
cairosvg.svg2png(bytestring=fig4.encode(), write_to=f"{OUT}/fig4.png", output_width=1400)
print("wrote fig4")
