# Simulate the 16x16 transpose of qk_rowmajor_128x4 at HEAD element by element.
# Tile T[token][col]: row = token (0..15 within one 16-token block), col = query head (0..15).
# Each __m512 is a list of 16 floats; 128-bit lane L = elements 4L..4L+3.
def unpacklo_ps(a,b): return [x for L in range(4) for x in (a[4*L],b[4*L],a[4*L+1],b[4*L+1])]
def unpackhi_ps(a,b): return [x for L in range(4) for x in (a[4*L+2],b[4*L+2],a[4*L+3],b[4*L+3])]
def unpacklo_pd(a,b): return [x for L in range(4) for x in (a[4*L],a[4*L+1],b[4*L],b[4*L+1])]
def unpackhi_pd(a,b): return [x for L in range(4) for x in (a[4*L+2],a[4*L+3],b[4*L+2],b[4*L+3])]
def shuffle_f32x4(a,b,imm):
    sel=[(imm>>(2*i))&3 for i in range(4)]
    lanes=[a[4*sel[0]:4*sel[0]+4],a[4*sel[1]:4*sel[1]+4],b[4*sel[2]:4*sel[2]+4],b[4*sel[3]:4*sel[3]+4]]
    return [x for l in lanes for x in l]
T=[[(tok,col) for col in range(16)] for tok in range(16)]  # s_transposed block r: row=token, col=head
u=[[None]*4 for _ in range(4)]
for rg in range(4):
    r0,r1,r2,r3=T[4*rg],T[4*rg+1],T[4*rg+2],T[4*rg+3]
    t0=unpacklo_ps(r0,r1); t1=unpackhi_ps(r0,r1); t2=unpacklo_ps(r2,r3); t3=unpackhi_ps(r2,r3)
    u[rg][0]=unpacklo_pd(t0,t2); u[rg][1]=unpackhi_pd(t0,t2); u[rg][2]=unpacklo_pd(t1,t3); u[rg][3]=unpackhi_pd(t1,t3)
# claim: lane `lane` of u[rg][k] holds tile column 4*lane+k for tokens 4rg..4rg+3
for rg in range(4):
    for k in range(4):
        for lane in range(4):
            seg=u[rg][k][4*lane:4*lane+4]
            assert seg==[(4*rg+t,4*lane+k) for t in range(4)], (rg,k,lane,seg)
print("stage1-2 claim holds")
E,O=0x88,0xdd
ok=True
for lane in range(4):
    pair_sel=O if lane&1 else E
    quad_sel=O if lane&2 else E
    for k in range(4):
        p=shuffle_f32x4(u[0][k],u[1][k],pair_sel)
        q2=shuffle_f32x4(u[2][k],u[3][k],pair_sel)
        out=shuffle_f32x4(p,q2,quad_sel)
        row=4*lane+k
        want=[(tok,row) for tok in range(16)]
        if out!=want:
            ok=False; print("MISMATCH lane",lane,"k",k,"row",row,out)
print("stages 3-4 all rows correct:",ok)
