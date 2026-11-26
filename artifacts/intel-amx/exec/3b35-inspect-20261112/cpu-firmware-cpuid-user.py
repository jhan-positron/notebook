# Executes the unprivileged CPUID instruction in user space (no /dev/cpu, no root). Read-only.
import ctypes, mmap, struct
code = bytes([0x53,                 # push rbx
              0x89,0xf8,            # mov eax,edi
              0x89,0xf1,            # mov ecx,esi
              0x49,0x89,0xd0,       # mov r8,rdx
              0x0f,0xa2,            # cpuid
              0x41,0x89,0x00,       # mov [r8],eax
              0x41,0x89,0x58,0x04,  # mov [r8+4],ebx
              0x41,0x89,0x48,0x08,  # mov [r8+8],ecx
              0x41,0x89,0x50,0x0c,  # mov [r8+12],edx
              0x5b,0xc3])           # pop rbx; ret
m = mmap.mmap(-1, 4096, prot=mmap.PROT_READ|mmap.PROT_WRITE|mmap.PROT_EXEC)
m.write(code)
addr = ctypes.addressof(ctypes.c_char.from_buffer(m))
fn = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p)(addr)
def cpuid(l, s):
    b = ctypes.create_string_buffer(16); fn(l, s, ctypes.addressof(b)); return struct.unpack('<4I', b.raw)
for l, s in [(0,0),(1,0),(7,0),(7,1),(7,2),(0xd,0),(0xd,1),(0xd,17),(0xd,18),(0x16,0),(0x1d,0),(0x1d,1),(0x1e,0),(0x1e,1),(0x24,0)]:
    a,b,c,d = cpuid(l,s); print('leaf 0x%02x sub %2d: eax=%08x ebx=%08x ecx=%08x edx=%08x' % (l,s,a,b,c,d))
a,b,c,d = cpuid(7,0)
print('CPUID(7,0).EDX[22] AMX-BF16 = %d' % ((d>>22)&1)); print('CPUID(7,0).EDX[24] AMX-TILE = %d' % ((d>>24)&1)); print('CPUID(7,0).EDX[25] AMX-INT8 = %d' % ((d>>25)&1))
print('CPUID(7,0).EBX[4] HLE = %d' % ((b>>4)&1)); print('CPUID(7,0).EBX[11] RTM = %d' % ((b>>11)&1)); print('CPUID(7,0).EDX[11] RTM_ALWAYS_ABORT = %d' % ((d>>11)&1))
a,b,c,d = cpuid(7,1)
print('CPUID(7,1).EAX[21] AMX-FP16 = %d' % ((a>>21)&1)); print('CPUID(7,1).EAX[4] AVX-VNNI = %d' % ((a>>4)&1)); print('CPUID(7,1).EAX[5] AVX512-BF16 = %d' % ((a>>5)&1)); print('CPUID(7,1).EDX[8] AMX-COMPLEX = %d' % ((d>>8)&1))
a,b,c,d = cpuid(0x1d,1)
print('CPUID(0x1D,1) palette 1: total_tile_bytes=%d bytes_per_tile=%d bytes_per_row=%d max_names=%d max_rows=%d' % (a&0xffff, a>>16, b&0xffff, b>>16, c&0xffff))
a,b,c,d = cpuid(0x1e,0)
print('CPUID(0x1E,0) TMUL: maxK=%d maxN=%d' % (b&0xff, (b>>8)&0xffff))
a,b,c,d = cpuid(0x16,0)
print('CPUID(0x16) base=%d MHz max=%d MHz bus=%d MHz' % (a&0xffff, b&0xffff, c&0xffff))
