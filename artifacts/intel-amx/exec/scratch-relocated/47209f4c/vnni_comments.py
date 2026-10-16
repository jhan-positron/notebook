import pathlib
p = pathlib.Path('/home/jhan/workspace/ai-runs/tron-issue4525/h/tron/tensor/v_vnni.hpp')
s = p.read_text()
reps = [
("// Words used here: A plane is V for one KV head of one 64-token page.\n"
 "// AVX-512 and AVX2 are the 512-bit and the 256-bit x86 vector instruction families;\n"
 "// they give the 16-lane and the 8-lane build. A lane is one 32-bit slot of a vector\n"
 "// register, here holding one bf16 pair. A chunk is one register of chunk_size fp32\n"
 "// values (16 or 8). A pair is two adjacent tokens (2p, 2p + 1). A pair chunk is the\n"
 "// 64-byte load that holds one chunk of both tokens of a pair (32 bf16).\n",
 "// Words used here: A plane is V for one KV head of one 64-token page.\n"
 "// AVX-512 is the 512-bit x86 vector instruction family; the build is 16-lane. A\n"
 "// lane is one 32-bit slot of a vector register, here holding one bf16 pair. A\n"
 "// chunk is one register of chunk_size (16) fp32 values. A pair is two adjacent\n"
 "// tokens (2p, 2p + 1). A pair chunk is the 64-byte load that holds one chunk of\n"
 "// both tokens of a pair (32 bf16).\n"),
("// In the 16-lane (AVX-512) build the V plane of a kv_block stores token pairs\n"
 "// interleaved: for each dimension d,",
 "// The V plane of a kv_block stores token pairs interleaved: for each dimension d,"),
("// The 8-lane (AVX2) build keeps V row-major and does not use these types for\n"
 "// storage. The classes are still defined there, so that declarations naming\n"
 "// them (the AMX kernel signatures and their CPU fakes) compile. The vector\n"
 "// operations exist only at 16 lanes.\n"
 "//\n", ""),
("// Byte alignment of one packed V plane. In the 16-lane build every pair chunk is\n"
 "// one 64-byte vector load, and the AMX PV kernel reads the plane in 64-byte tile\n"
 "// rows. Fixed for both lane counts (chunk_alignment is 32 bytes at 8 lanes).\n",
 "// Byte alignment of one packed V plane: every pair chunk is one 64-byte vector\n"
 "// load, and the AMX PV kernel reads the plane in 64-byte tile rows.\n"),
]
for old, new in reps:
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new)
p.write_text(s)
