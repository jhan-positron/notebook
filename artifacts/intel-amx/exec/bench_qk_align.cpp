// bench_qk_align: does a misaligned packed-Q buffer slow the mirror QK kernel?
// Context: PR3879 review thread r3858305367. The packer contracts demand a
// 64B-aligned 4 KB buffer; production passed a plain std::vector whose base is
// 16 or 48 mod 64 in practice. TILELOADD tolerates misalignment; the predicted
// cost is split-cache-line tile rows (4 Q-tile loads x 16 rows per page).
// This bench times qk_mirror_128x4 per 64-token page with the packed-Q base
// at +0 vs +16 bytes from a 64B boundary - the A/B the review left open.
//
// Links the REAL kernel TU (see exec/jeremy-measure-20260831.sh). Runs tile
// instructions: 3bda only, after available() (arch_prctl tile grant).
//
// Usage: bench_qk_align <offset_bytes 0|16> <iters> <pages>
//   pages ring sizes L2/RAM residency like the fused sweep: 1 / 512 / 16384.
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>

namespace tron::amx_attn {
bool available() noexcept;
void begin_region() noexcept;
void end_region() noexcept;
void pack_q_rows_128x4(const uint16_t* q_group, uint16_t* padded) noexcept;
void qk_mirror_128x4(
    const uint16_t* k_mirror, const uint16_t* q_rows, float* s) noexcept;
}  // namespace tron::amx_attn

namespace {
constexpr size_t kGroupElems = 4 * 128;
constexpr size_t kPackElems = 16 * 128;      // 4096 bytes
constexpr size_t kMirrorElems = 8192;        // one page's K mirror, 16 KB
constexpr size_t kSRows = 16, kSCols = 64;   // kernel stores 16 rows x 256 B

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
  if (argc != 4) {
    std::fprintf(stderr, "usage: %s <offset_bytes 0|16> <iters> <pages>\n", argv[0]);
    return 2;
  }
  const size_t offset = std::atol(argv[1]);
  const long iters = std::atol(argv[2]);
  const long pages = std::atol(argv[3]);
  if (offset % 2 != 0 || offset >= 64) {
    std::fprintf(stderr, "offset must be even and < 64\n");
    return 2;
  }
  if (!tron::amx_attn::available()) {
    std::fprintf(stderr, "AMX unavailable on this host\n");
    return 1;
  }

  // K mirror ring: valid bf16 content (values in [0.5, 1.5); content does not
  // matter numerically, but NaN/denormal bit patterns are avoided).
  uint16_t* ring = static_cast<uint16_t*>(
      aligned_alloc(64, pages * kMirrorElems * sizeof(uint16_t)));
  if (!ring) return 1;
  for (long p = 0; p < pages; ++p)
    for (size_t i = 0; i < kMirrorElems; ++i)
      ring[p * kMirrorElems + i] = bf16_bits(0.5f + 0.001f * ((p + i) % 1000));

  // Packed Q at a controlled base: 64B allocation + 0 or 16 byte offset.
  uint16_t* qbuf = static_cast<uint16_t*>(
      aligned_alloc(64, kPackElems * sizeof(uint16_t) + 64));
  if (!qbuf) return 1;
  std::memset(qbuf, 0, kPackElems * sizeof(uint16_t) + 64);
  uint16_t* q_rows =
      reinterpret_cast<uint16_t*>(reinterpret_cast<char*>(qbuf) + offset);
  if (reinterpret_cast<uintptr_t>(q_rows) % 64 != offset) {
    std::fprintf(stderr, "base not at requested offset\n");
    return 1;
  }
  uint16_t q_group[kGroupElems];
  for (size_t i = 0; i < kGroupElems; ++i)
    q_group[i] = bf16_bits(0.5f + 0.001f * (i % 1000));
  tron::amx_attn::pack_q_rows_128x4(q_group, q_rows);  // pack once, reuse

  alignas(64) static float s[kSRows * kSCols];

  tron::amx_attn::begin_region();
  for (int w = 0; w < 3; ++w)  // warmup passes over the ring
    for (long p = 0; p < pages; ++p)
      tron::amx_attn::qk_mirror_128x4(ring + p * kMirrorElems, q_rows, s);

  const double t0 = now_ns();
  for (long i = 0; i < iters; ++i)
    for (long p = 0; p < pages; ++p)
      tron::amx_attn::qk_mirror_128x4(ring + p * kMirrorElems, q_rows, s);
  const double t1 = now_ns();
  tron::amx_attn::end_region();

  double sum = 0;  // consume
  for (size_t i = 0; i < kSRows * kSCols; ++i) sum += s[i];
  std::printf(
      "qk_align off=%zu pages=%ld iters=%ld per_page_ns=%.1f q_mod64=%zu sum=%.3e\n",
      offset, pages, iters, (t1 - t0) / (double(iters) * pages),
      reinterpret_cast<uintptr_t>(q_rows) % 64, sum);
  free(qbuf);
  free(ring);
  return 0;
}
