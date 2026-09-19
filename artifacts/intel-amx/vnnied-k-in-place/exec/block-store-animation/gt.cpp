// Ground truth for the block-store animation page: run the real
// k_vnni::store_block on mock rows and dump where every value lands.
#include <cstdio>
#include <cstring>
#include <cstdint>
#include "tron/kernels/k_vnni.hpp"
using namespace tron::k_vnni;
using tron::bf16;
static float mock(int T, int d) { return float(T - 21) + 0.11f + 0.01f * float(d); }
int main() {
  alignas(64) static bf16 rows_mem[64][128];
  alignas(64) static bf16 plane[64 * 128];
  for (int T = 0; T < 64; ++T) for (int d = 0; d < 128; ++d) rows_mem[T][d] = bf16(mock(T, d));
  for (auto& x : plane) x = bf16::from_bits(0xA5A5);
  // block c = 1 (tokens 16..31), all present
  const bf16* rows[16];
  for (int t = 0; t < 16; ++t) rows[t] = rows_mem[16 + t];
  store_block(plane, 1, FULL_BLOCK_0XFFFF, rows);
  // verify against index()
  int bad = 0, poison = 0;
  for (int T = 0; T < 64; ++T) for (int d = 0; d < 128; ++d) {
    size_t i = index(T, d);
    uint16_t have = plane[i].to_bits();
    if (T >= 16 && T < 32) { if (have != rows_mem[T][d].to_bits()) ++bad; }
    else { if (have != 0xA5A5) ++poison; }
  }
  printf("mismatch=%d poison_touched=%d\n", bad, poison);
  // verify the same against scatter_row per token into a second plane
  alignas(64) static bf16 ref[64 * 128];
  for (auto& x : ref) x = bf16::from_bits(0xA5A5);
  for (int T = 16; T < 32; ++T) scatter_row(ref, T, rows_mem[T]);
  printf("block_vs_scatter_memcmp=%d\n", memcmp(ref, plane, sizeof(plane)));
  // dump: for token 21, each dim -> (s, c, dp, t, j), byte offset in plane, line index
  FILE* f = fopen("token21.json", "w");
  fprintf(f, "[\n");
  for (int d = 0; d < 128; ++d) {
    size_t i = index(21, d); size_t byte = i * 2;
    int s = d / 32, dp = (d % 32) / 2, j = d % 2, c = 21 / 16, t = 21 % 16;
    fprintf(f, " {\"d\":%d,\"s\":%d,\"c\":%d,\"dp\":%d,\"t\":%d,\"j\":%d,\"byte\":%zu,\"line\":%zu,\"panel\":%d,\"val\":%.6g,\"hex\":\"0x%04X\"}%s\n",
      d, s, c, dp, t, j, byte, byte / 64, s * 4 + c, float(rows_mem[21][d]), rows_mem[21][d].to_bits(), d == 127 ? "" : ",");
  }
  fprintf(f, "]\n"); fclose(f);
  // dump the 16x128 block values as bf16 hex + float, and the store order
  f = fopen("block.json", "w");
  fprintf(f, "{\"tokens\":[");
  for (int T = 16; T < 32; ++T) {
    fprintf(f, "%s{\"T\":%d,\"vals\":[", T == 16 ? "" : ",", T);
    for (int d = 0; d < 128; ++d) fprintf(f, "%s%.6g", d ? "," : "", float(rows_mem[T][d]));
    fprintf(f, "],\"hex\":[");
    for (int d = 0; d < 128; ++d) fprintf(f, "%s\"%04X\"", d ? "," : "", rows_mem[T][d].to_bits());
    fprintf(f, "]}");
  }
  // store order from store_block's loops: s outer (0..3), dp inner (0..15); c = 1
  fprintf(f, "],\"stores\":[");
  int n = 0;
  for (int s = 0; s < 4; ++s) for (int dp = 0; dp < 16; ++dp) {
    size_t byte = ((s * 4 + 1) * 256 + dp * 16) * 4;  // PANEL_DWORDS_256, ROW_DWORDS_16, 4 bytes
    fprintf(f, "%s{\"n\":%d,\"s\":%d,\"dp\":%d,\"byte\":%zu,\"line\":%zu}", n ? "," : "", n + 1, s, dp, byte, byte / 64);
    ++n;
  }
  fprintf(f, "]}\n"); fclose(f);
  // sanity: the first bytes of line for (s=0,dp=0): token 16..31 pair 0
  const uint16_t* p = reinterpret_cast<const uint16_t*>(plane) + ((0 * 4 + 1) * 256) * 2;
  printf("line(s0,dp0) first 4 dwords as bf16: ");
  for (int k = 0; k < 8; ++k) printf("%g ", float(bf16::from_bits(p[k])));
  printf("\n");
  printf("token21 pair0 bytes (little endian): ");
  const uint8_t* b = reinterpret_cast<const uint8_t*>(plane) + index(21, 0) * 2;
  for (int k = 0; k < 4; ++k) printf("%02X ", b[k]);
  printf("\n");
  return bad + poison;
}
