#!/usr/bin/env python3
"""pr5606-check-20261123: compare the loaded sections of two ELF binaries byte by byte.

A section is "loaded" when the program loader maps it into memory (flag SHF_ALLOC): code, constants, data.
Debug sections are not loaded and are left out. For each loaded section the script prints the size in both
files and whether the bytes are the same. For a section of equal size with different bytes it prints the
count of differing bytes and the first place.
Usage: secthash.py <binary A> <binary B>
"""
import struct
import sys

SHF_ALLOC = 0x2
SHT_NOBITS = 8


def sections(path):
    data = open(path, "rb").read()
    assert data[:4] == b"\x7fELF" and data[4] == 2, "not a 64-bit ELF file"
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    raw = []
    for i in range(shnum):
        name, typ, flags, addr, off, size = struct.unpack_from("<IIQQQQ", data, shoff + i * shentsize)
        raw.append((name, typ, flags, addr, off, size))
    stroff = raw[shstrndx][4]
    out = {}
    for name, typ, flags, addr, off, size in raw:
        if not flags & SHF_ALLOC:
            continue
        end = data.index(b"\0", stroff + name)
        label = data[stroff + name:end].decode()
        out[label] = (addr, size, b"" if typ == SHT_NOBITS else data[off:off + size])
    return out


a, b = sections(sys.argv[1]), sections(sys.argv[2])
same = 0
print(f"loaded sections: A {len(a)}, B {len(b)}")
for name in a:
    if name not in b:
        print(f"  {name}: only in A")
        continue
    (aa, asz, ab), (ba, bsz, bb) = a[name], b[name]
    if ab == bb and asz == bsz and aa == ba:
        same += 1
        continue
    if asz != bsz:
        print(f"  {name}: size A {asz} B, size B {bsz} B")
    elif aa != ba:
        print(f"  {name}: same {asz} bytes, but address A {aa:#x}, address B {ba:#x}")
    else:
        idx = [i for i in range(asz) if ab[i] != bb[i]]
        print(f"  {name}: size {asz} B in both, {len(idx)} bytes differ, first at offset {idx[0]}: "
              f"A {ab[max(0, idx[0] - 24):idx[0] + 24]!r}")
for name in b:
    if name not in a:
        print(f"  {name}: only in B")
print(f"loaded sections with the same address, size and bytes in both files: {same} of {len(a)}")
text = a.get(".text")
if text:
    print(f".text (the code): {text[1]} bytes; identical in both files: {'yes' if text == b.get('.text') else 'no'}")
