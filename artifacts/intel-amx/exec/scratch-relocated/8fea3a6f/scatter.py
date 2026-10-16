# Where do the 64 scattered dwords of store_row land for an out-of-range token?
# Formula from k_vnni.hpp:264: dword index = (s*4 + c)*256 + t + row*16, c = token//16, t = token%16
PLANE_DWORDS = 16 * 256  # 16 panels x 256 dwords = 16 KiB
for token in (63, 64, 65, 100, 127, 128, 255, 256):
    inside = outside = 0
    for s in range(4):
        c, t = token // 16, token % 16
        for row in range(16):
            idx = (s * 4 + c) * 256 + t + row * 16
            if idx < PLANE_DWORDS: inside += 1
            else: outside += 1
    print(f"token={token:3d}: inside(other tokens' slots)={inside:2d} outside={outside:2d}")
# distinctness of the k_data pattern 0x3C00 + t*100 + i across (t,i)
vals = {}
coll = 0
for t in range(4):
    for i in range(8 * 128):
        v = 0x3C00 + t * 100 + i
        if v in vals: coll += 1
        vals[v] = (t, i)
print("k_data pattern collisions across (token, element):", coll)
