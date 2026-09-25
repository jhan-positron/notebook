# Closed-form attention work per (layer, KV head), unit = K tokens scored by one query token
# (multiply by kv_mul = 4 for dot products). Single user, chunk 128, KV page 64, no prefix cache,
# HBM shard 1024, engagement point 127, GOF 4. est. = derived from the causal rule, not measured.
PAGE=64; CHUNK=128; ENGAGE=127
def prefill_cpu(N):
    amx=avx=0; visits_amx=visits_avx=0
    for q in range(N):
        c=q//CHUNK
        for p in range(q//PAGE+1):
            ready = p*PAGE+PAGE-1 < c*CHUNK      # written in an earlier forward -> one range -> dense
            if ready: amx+=PAGE; visits_amx+=1
            else:
                avx+=min(PAGE, q-p*PAGE+1); visits_avx+=1   # own-chunk page: one range per token -> dotter
    return amx,avx,visits_amx,visits_avx
def prefill_aof(N, lag_gofs=0):
    # FPGA scores the HBM-resident prefix = tokens of earlier chunks, if their DMA finished (lag_gofs GOFs behind)
    fpga=amx=avx=0
    for q in range(N):
        c=q//CHUNK
        resident_end = c*CHUNK - 4*lag_gofs          # exclusive
        if q < ENGAGE or resident_end < 128: resident_end = 0   # young query or first shard not engaged
        fpga += max(0,resident_end)
        # CPU part: tokens resident_end..q ; full ready pages (written earlier chunks, inside one range) -> AMX
        for p in range(resident_end//PAGE, q//PAGE+1):
            lo=max(p*PAGE,resident_end); hi=min(p*PAGE+PAGE-1,q)
            n=hi-lo+1
            if n<=0: continue
            ready = p*PAGE+PAGE-1 < c*CHUNK
            if ready and n==PAGE: amx+=PAGE
            else: avx+=n
    return fpga,amx,avx
def decode_cpu(N0, steps, full_pending_is_amx=True):
    amx=avx=0; va=vv=0
    for t in range(1,steps+1):
        N=N0+t
        full=N//PAGE; rem=N%PAGE
        if rem==0 and not full_pending_is_amx: full-=1; rem=PAGE
        amx+=PAGE*full; va+=full
        if rem: avx+=rem; vv+=1
    return amx,avx,va,vv
def decode_aof(N0, steps, lag=4):
    # FPGA covers 0..B, B = N-1-lag (lag tokens = pending token + incomplete GOF, est.), CPU tail all AVX
    fpga=avx=amx=0
    for t in range(1,steps+1):
        N=N0+t; B=N-1-lag
        fpga+=B+1
        tail=N-1-B   # tokens B+1..N-1
        # tail spans <=2 partial pages -> AVX; a full CPU page would need tail>=64
        avx+=tail
    return fpga,amx,avx
for N in (1024,2048,4096,8192):
    a,v,va,vv=prefill_cpu(N); tot=a+v
    f,fa,fv=prefill_aof(N)
    da,dv,dva,dvv=decode_cpu(N,256); dtot=da+dv
    df,dfa,dfv=decode_aof(N,256)
    print(f"N={N}: PREFILL total {tot:,} K-tok = {N*(N+1)//2:,} check; CPU-attn AMX {a:,} ({100*a/tot:.1f}%) AVX {v:,} ({100*v/tot:.1f}%), visits AMX {va:,} AVX {vv:,}")
    print(f"        PREFILL AoF(est., DMA keeps up): FPGA {f:,} ({100*f/tot:.1f}%) AMX {fa:,} AVX {fv:,} ({100*fv/tot:.1f}%)")
    print(f"        DECODE 256 steps total {dtot:,}; CPU-attn AMX {da:,} ({100*da/dtot:.1f}%) AVX {dv:,} ({100*dv/dtot:.1f}%) visits {dva:,}/{dvv:,}; AoF(est. lag 4) FPGA {df:,} ({100*df/dtot:.1f}%) AVX {dfv:,} ({100*dfv/dtot:.2f}%)")
    print(f"        prefill/decode work ratio {tot/dtot:.2f}x; one decode query at N+1: {(N+1)//64} AMX pages, {(N+1)%64} AVX tokens")
# variant: full pending page counted AVX
da,dv,_,_=decode_cpu(1024,256,False); print("decode 1024 variant (full pending page -> AVX): AMX",f"{da:,}","AVX",f"{dv:,}")
# steps where the tail page is full
print("steps with N mod 64 == 0 in 256 steps from 1024:", sum(1 for t in range(1,257) if (1024+t)%64==0))
