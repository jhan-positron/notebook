// bench_qpack: per-call cost of the real Q packers on the test host.
// Context: PR3879 review thread r3858305362 (the eager Q pack); the only
// prior figure was 65-95 ns est. on a non-production host.
//
// Links the REAL kernel TU (src/tron/kernels/amx_attn.cpp compiled under nix
// clang; see exec/jeremy-measure-20260831.sh) - no hand copy of the kernels.
// The packers are scalar/memcpy code: no tile instruction runs here, so no
// begin_region()/arch_prctl is needed.
//
// Production-faithful details:
//   - the 4 KB destination is zeroed ONCE outside the timed loop (the pack
//     contracts let the caller keep padding zero; the packers write only the
//     live 4 columns/rows - the old fused bench memset per call and is NOT
//     comparable);
//   - 8 rotating source Q groups so the source is not one hot cache line;
//   - one fixed destination slot, like a token's slot reused across pages.
//
// Usage: bench_qpack rows|group <iters>
// Output: one line, ns/op via CLOCK_MONOTONIC around the loop.
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>

namespace tron::amx_attn {
void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
void pack_q_rows_128x4(const uint16_t* q_group, uint16_t* padded) noexcept;
}  // namespace tron::amx_attn

namespace {
constexpr size_t kGroupElems = 4 * 128;   // 4 query heads x head size 128
constexpr size_t kPackElems = 16 * 128;   // Q_PACK_ELEMS_2048, 4096 bytes
constexpr int kSources = 8;

uint16_t bf16_bits(float f) {
  uint32_t u;
  std::memcpy(&u, &f, 4);
  return static_cast<uint16_t>(u >> 16);
}

double now_ns() {
  timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec * 1e9 + ts.tv_nsec;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::fprintf(stderr, "usage: %s rows|group <iters>\n", argv[0]);
    return 2;
  }
  const bool rows = std::strcmp(argv[1], "rows") == 0;
  if (!rows && std::strcmp(argv[1], "group") != 0) {
    std::fprintf(stderr, "unknown fn %s\n", argv[1]);
    return 2;
  }
  const long iters = std::atol(argv[2]);

  static uint16_t sources[kSources][kGroupElems];
  for (int s = 0; s < kSources; ++s)
    for (size_t i = 0; i < kGroupElems; ++i)
      sources[s][i] = bf16_bits(0.5f + 0.001f * ((s * 131 + i) % 1000));

  uint16_t* packed =
      static_cast<uint16_t*>(aligned_alloc(64, kPackElems * sizeof(uint16_t)));
  if (!packed) return 1;
  std::memset(packed, 0, kPackElems * sizeof(uint16_t));  // padding, once

  for (int w = 0; w < 3 * kSources; ++w)  // warmup
    rows ? tron::amx_attn::pack_q_rows_128x4(sources[w % kSources], packed)
         : tron::amx_attn::pack_q_group_128x4(sources[w % kSources], packed);

  const double t0 = now_ns();
  for (long i = 0; i < iters; ++i)
    rows ? tron::amx_attn::pack_q_rows_128x4(sources[i & (kSources - 1)], packed)
         : tron::amx_attn::pack_q_group_128x4(sources[i & (kSources - 1)], packed);
  const double t1 = now_ns();

  uint64_t sum = 0;  // consume the output so nothing is optimized away
  for (size_t i = 0; i < kPackElems; ++i) sum += packed[i];
  std::printf(
      "qpack fn=%s iters=%ld total_ns=%.0f ns_per_op=%.2f dst_mod64=%zu sum=%" PRIu64 "\n",
      rows ? "rows" : "group", iters, t1 - t0, (t1 - t0) / iters,
      reinterpret_cast<uintptr_t>(packed) % 64, sum);
  free(packed);
  return 0;
}
