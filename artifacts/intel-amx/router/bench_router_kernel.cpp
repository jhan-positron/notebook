// bench_router_kernel.cpp — P0b standalone router-kernel microbenchmark
// (plan: intel-AMX/router/02-option-c-plan.md, section P0b).
//
// logits[M][N] = act[M][K=2880] x W^T, N in {32,128}, M in {1..16}.
// Arms:
//   avx_fp32 : weights stored fp32; bf16 activations widened per 16-lane chunk
//              (mirrors the current tron tensor::matmul / dotter inner path).
//   avx_bf16 : weights stored bf16; _mm512_dpbf16_ps, 6 alternating accumulators
//              (2 accumulators left each dot dependency-chain bound: 45 serial
//              vdpbf16ps per chain; 6 cut it to 15 and measured 1.2-1.36x on Zen5).
//   amx_bf16 : weights stored bf16 pre-packed to VNNI (tron pack_k_vnni layout);
//              tile kernel, up to 4 C tiles per 64-column pass.
// Self-contained: no tron includes. pack_k_vnni is copied from
// tron-pr2934-reconciled h/tron/kernels/amx_kv_layout.hpp (N_TILE=16 inlined).
// Every invocation validates against a double-precision scalar reference over
// the SAME rounded values the arm consumes, before any timing.
//
// Cache regimes: l2 (one layer, reused), cyclic (L distinct layer buffers,
// round-robin per call), disrupted (cyclic + D threads streaming 1 GiB each).
// Multi-core: --workers W splits the N columns; the timed call includes the
// release/wait barrier (that dispatch overhead is part of what P0b bounds).
//
// Output: '#' free-form lines plus exactly one RESULT (or VALIDATE) line.
// On a host without AMX permission the amx_bf16 arm prints
// "SKIP amx_bf16 (no AMX permission)" and exits 0.

#include <algorithm>
#include <atomic>
#include <cassert>
#include <cmath>
#include <cpuid.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <immintrin.h>
#include <pthread.h>
#include <random>
#include <string>
#include <sys/syscall.h>
#include <thread>
#include <time.h>
#include <unistd.h>
#include <vector>

#ifndef ARCH_REQ_XCOMP_PERM
#define ARCH_REQ_XCOMP_PERM 0x1023
#endif
#define XFEATURE_XTILEDATA 18

using bf16 = uint16_t;

static constexpr int K = 2880;  // router hidden size (fixed by the model)
static constexpr int MAXM = 16;

// ---------- scalar bf16 helpers ----------
static inline float b2f(bf16 v) {
  uint32_t u = (uint32_t)v << 16;
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
static inline bf16 f2b(float f) {  // round-to-nearest-even, like cvtne
  uint32_t u;
  std::memcpy(&u, &f, 4);
  uint32_t lsb = (u >> 16) & 1;
  u += 0x7fff + lsb;
  return (bf16)(u >> 16);
}

// ---------- CPU feature detection ----------
struct CpuFeat {
  bool avx512f = false, avx512_bf16 = false, amx_tile = false, amx_bf16 = false;
};
static CpuFeat detect_cpu() {
  CpuFeat f;
  unsigned a, b, c, d;
  if (__get_cpuid_count(7, 0, &a, &b, &c, &d)) {
    f.avx512f = b & (1u << 16);
    f.amx_tile = d & (1u << 24);
    f.amx_bf16 = d & (1u << 22);
  }
  if (__get_cpuid_count(7, 1, &a, &b, &c, &d))
    f.avx512_bf16 = a & (1u << 5);
  return f;
}

// ---------- AMX plumbing ----------
struct tile_config {
  uint8_t palette, start_row;
  uint8_t reserved[14];
  uint16_t column_bytes[16];
  uint8_t rows[16];
};
static bool amx_request() {
  return syscall(SYS_arch_prctl, ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA) == 0;
}
#ifdef __AMX_BF16__
static void amx_config_maxshape() {  // one max-shape LDTILECFG per region
  tile_config c{};
  c.palette = 1;
  for (int i = 0; i < 8; i++) {
    c.rows[i] = 16;
    c.column_bytes[i] = 64;
  }
  _tile_loadconfig(&c);
}
#endif

// ---------- VNNI B-pack (copied from tron amx_kv_layout.hpp, N_TILE=16) ----------
// dst[(key/16)*head_dim*16 + kp*32 + (key%16)*2 + {0,1}] = row[2*kp + {0,1}]
// For router weight W[N][K] row-major: pack_k_vnni(W, W_vnni, N, K) packs the
// AMX B operand directly (key = output column n, head_dim = K).
static void pack_k_vnni(const bf16* src, bf16* dst, size_t n_keys, size_t head_dim) {
  for (size_t key = 0; key < n_keys; ++key) {
    const bf16* row = src + key * head_dim;
    bf16* out = dst + (key / 16) * head_dim * 16;
    const size_t nl = key % 16;
    for (size_t kp = 0; kp < head_dim / 2; ++kp) {
      out[kp * 32 + nl * 2 + 0] = row[2 * kp + 0];
      out[kp * 32 + nl * 2 + 1] = row[2 * kp + 1];
    }
  }
}

// ---------- kernels ----------
// widen 16 bf16 lanes to fp32 (dotter's bf16s_to_fp32s pattern)
static inline __m512 bf16_widen16(const bf16* p) {
  __m256i v = _mm256_loadu_si256((const __m256i*)p);
  return _mm512_castsi512_ps(_mm512_slli_epi32(_mm512_cvtepu16_epi32(v), 16));
}

// arm 1: fp32 weight row x bf16 act row, 180 chunks of 16, 2 alternating FMA accumulators
static void slice_avx_fp32(
    const bf16* act, const float* wf, float* logits, int M, int N, int n0, int n1) {
  for (int m = 0; m < M; ++m) {
    const bf16* a = act + (size_t)m * K;
    for (int n = n0; n < n1; ++n) {
      const float* w = wf + (size_t)n * K;
      __m512 s0 = _mm512_setzero_ps(), s1 = _mm512_setzero_ps();
      for (int k = 0; k < K; k += 32) {
        s0 = _mm512_fmadd_ps(bf16_widen16(a + k), _mm512_loadu_ps(w + k), s0);
        s1 = _mm512_fmadd_ps(bf16_widen16(a + k + 16), _mm512_loadu_ps(w + k + 16), s1);
      }
      logits[(size_t)m * N + n] = _mm512_reduce_add_ps(_mm512_add_ps(s0, s1));
    }
  }
}

// arm 2: bf16 weight, vdpbf16ps over 90 chunks of 32, 6 alternating accumulators
// (K = 2880 = 15 iterations x 192 bf16; reduction tree at the end)
static void slice_avx_bf16(
    const bf16* act, const bf16* wb, float* logits, int M, int N, int n0, int n1) {
  static_assert(K % 192 == 0, "K must split into whole 6x32 bf16 iterations");
  for (int m = 0; m < M; ++m) {
    const bf16* a = act + (size_t)m * K;
    for (int n = n0; n < n1; ++n) {
      const bf16* w = wb + (size_t)n * K;
      __m512 s0 = _mm512_setzero_ps(), s1 = _mm512_setzero_ps(),
             s2 = _mm512_setzero_ps(), s3 = _mm512_setzero_ps(),
             s4 = _mm512_setzero_ps(), s5 = _mm512_setzero_ps();
      for (int k = 0; k < K; k += 192) {
        s0 = _mm512_dpbf16_ps(s0, (__m512bh)_mm512_loadu_si512(a + k),
            (__m512bh)_mm512_loadu_si512(w + k));
        s1 = _mm512_dpbf16_ps(s1, (__m512bh)_mm512_loadu_si512(a + k + 32),
            (__m512bh)_mm512_loadu_si512(w + k + 32));
        s2 = _mm512_dpbf16_ps(s2, (__m512bh)_mm512_loadu_si512(a + k + 64),
            (__m512bh)_mm512_loadu_si512(w + k + 64));
        s3 = _mm512_dpbf16_ps(s3, (__m512bh)_mm512_loadu_si512(a + k + 96),
            (__m512bh)_mm512_loadu_si512(w + k + 96));
        s4 = _mm512_dpbf16_ps(s4, (__m512bh)_mm512_loadu_si512(a + k + 128),
            (__m512bh)_mm512_loadu_si512(w + k + 128));
        s5 = _mm512_dpbf16_ps(s5, (__m512bh)_mm512_loadu_si512(a + k + 160),
            (__m512bh)_mm512_loadu_si512(w + k + 160));
      }
      const __m512 t01 = _mm512_add_ps(s0, s1), t23 = _mm512_add_ps(s2, s3),
                   t45 = _mm512_add_ps(s4, s5);
      logits[(size_t)m * N + n] =
          _mm512_reduce_add_ps(_mm512_add_ps(_mm512_add_ps(t01, t23), t45));
    }
  }
}

#ifdef __AMX_BF16__
// tile register numbers are immediates; dispatch through switches
static inline void amx_zero_c(int c) {
  switch (c) {
  case 0: _tile_zero(0); break;
  case 1: _tile_zero(1); break;
  case 2: _tile_zero(2); break;
  default: _tile_zero(3); break;
  }
}
static inline void amx_ldb(bool b6, const void* p) {
  if (b6) _tile_loadd(6, p, 64);
  else _tile_loadd(5, p, 64);
}
static inline void amx_dp(int c, bool b6) {
  if (b6) switch (c) {
    case 0: _tile_dpbf16ps(0, 4, 6); break;
    case 1: _tile_dpbf16ps(1, 4, 6); break;
    case 2: _tile_dpbf16ps(2, 4, 6); break;
    default: _tile_dpbf16ps(3, 4, 6); break;
    }
  else switch (c) {
    case 0: _tile_dpbf16ps(0, 4, 5); break;
    case 1: _tile_dpbf16ps(1, 4, 5); break;
    case 2: _tile_dpbf16ps(2, 4, 5); break;
    default: _tile_dpbf16ps(3, 4, 5); break;
    }
}
static inline void amx_store_c(int c, float* st) {
  switch (c) {
  case 0: _tile_stored(0, st, 64); break;
  case 1: _tile_stored(1, st, 64); break;
  case 2: _tile_stored(2, st, 64); break;
  default: _tile_stored(3, st, 64); break;
  }
}

// arm 3: C tiles tmm0..3 (one per 16-column block, up to 4 per pass);
// A = tmm4 from the zero-padded 16 x K act; B = tmm5/tmm6 alternating from VNNI W.
// apad MUST be 16 rows (rows >= M zeroed once at setup).
static void slice_amx(const bf16* apad, const bf16* wv, float* logits, int M, int N,
    int cb0, int nblocks, float* staging) {
  constexpr int KSTEPS = K / 32;  // 90
  for (int g = 0; g < nblocks; g += 4) {
    const int ncb = std::min(4, nblocks - g);
    for (int c = 0; c < ncb; ++c)
      amx_zero_c(c);
    bool b6 = false;
    for (int s = 0; s < KSTEPS; ++s) {
      _tile_loadd(4, apad + (size_t)s * 32, K * 2);
      for (int c = 0; c < ncb; ++c) {
        const bf16* bp = wv + ((size_t)(cb0 + g + c) * K * 16 + (size_t)s * 512);
        amx_ldb(b6, bp);
        amx_dp(c, b6);
        b6 = !b6;
      }
    }
    for (int c = 0; c < ncb; ++c) {
      // Note [Tile stores write 16 rows]: _tile_stored always writes all 16
      // configured rows — staging must be a full 16x16 fp32 buffer, never M rows.
      amx_store_c(c, staging);
      const int col0 = (cb0 + g + c) * 16;
      assert(col0 + 16 <= N && M <= 16);  // copy stays inside this pass's columns
      for (int m = 0; m < M; ++m)
        std::memcpy(logits + (size_t)m * N + col0, staging + (size_t)m * 16,
            16 * sizeof(float));
    }
  }
}
#endif  // __AMX_BF16__

// ---------- globals (bench state) ----------
enum Arm { ARM_FP32, ARM_BF16, ARM_AMX };
enum Regime { R_L2, R_CYCLIC, R_DISRUPTED };

static Arm g_arm;
static int g_M, g_N, g_L, g_W;
static Regime g_regime;
static const bf16* g_act = nullptr;      // M x K
static const float* g_wf = nullptr;      // L x N x K (fp32 arm)
static const bf16* g_wb = nullptr;       // L x N x K (bf16 arm)
static const bf16* g_wv = nullptr;       // L x N x K VNNI (amx arm)
static float* g_logits = nullptr;        // 16 x N (rows >= M untouched)
static bf16* g_apad_main = nullptr;      // 16 x K, zero-padded act (amx, W==1)
static float* g_staging_main = nullptr;  // 16 x 16 fp32 (amx, W==1)

static volatile float g_vsink;
static volatile uint64_t g_vsink64;

template <typename T>
static T* alloc64(size_t n) {
  void* p = nullptr;
  if (posix_memalign(&p, 64, n * sizeof(T)) != 0) {
    fprintf(stderr, "alloc %zu bytes failed\n", n * sizeof(T));
    exit(1);
  }
  std::memset(p, 0, n * sizeof(T));
  return (T*)p;
}

static bool pin_to_cpu(int cpu) {
  cpu_set_t s;
  CPU_ZERO(&s);
  CPU_SET(cpu, &s);
  return pthread_setaffinity_np(pthread_self(), sizeof(s), &s) == 0;
}

static void build_apad(bf16* apad) {  // rows >= M stay zero
  std::memset(apad, 0, (size_t)MAXM * K * sizeof(bf16));
  for (int m = 0; m < g_M; ++m)
    std::memcpy(apad + (size_t)m * K, g_act + (size_t)m * K, (size_t)K * sizeof(bf16));
}

static void compute_slice(int layer, int n0, int n1, bf16* apad, float* staging) {
  if (n0 >= n1) return;
  const size_t off = (size_t)layer * g_N * K;
  switch (g_arm) {
  case ARM_FP32: slice_avx_fp32(g_act, g_wf + off, g_logits, g_M, g_N, n0, n1); break;
  case ARM_BF16: slice_avx_bf16(g_act, g_wb + off, g_logits, g_M, g_N, n0, n1); break;
  case ARM_AMX:
#ifdef __AMX_BF16__
    slice_amx(apad, g_wv + off, g_logits, g_M, g_N, n0 / 16, (n1 - n0) / 16, staging);
#else
    (void)apad;
    (void)staging;
#endif
    break;
  }
}

// ---------- worker pool (workers > 1 only; W==1 is a plain function call) ----------
static std::vector<std::thread> g_workers;
static std::vector<int> g_n0, g_n1;
static std::atomic<long> g_gen{0};
static std::atomic<int> g_done{0};
static std::atomic<int> g_layer_idx{0};
static std::atomic<bool> g_quit{false};

static void worker_body(int w, int cpu) {
  bf16* apad = nullptr;
  float* staging = nullptr;
  long seen = 0;
  if (cpu >= 0 && !pin_to_cpu(cpu))
    fprintf(stderr, "worker %d: pin to cpu %d failed\n", w, cpu);
#ifdef __AMX_BF16__
  if (g_arm == ARM_AMX) {
    amx_config_maxshape();  // per-thread tile state
    apad = alloc64<bf16>((size_t)MAXM * K);
    build_apad(apad);
    staging = alloc64<float>(16 * 16);
  }
#endif
  for (;;) {
    while (g_gen.load(std::memory_order_acquire) == seen) {
      if (g_quit.load(std::memory_order_relaxed)) goto out;
      _mm_pause();
    }
    seen = g_gen.load(std::memory_order_relaxed);
    compute_slice(g_layer_idx.load(std::memory_order_relaxed), g_n0[w], g_n1[w], apad,
        staging);
    g_done.fetch_add(1, std::memory_order_release);
  }
out:
#ifdef __AMX_BF16__
  if (g_arm == ARM_AMX) _tile_release();
#endif
  free(apad);
  free(staging);
}

// one timed call = one layer's full M x N logits (barrier included when W > 1)
static void run_call(int layer) {
  if (g_W == 1) {
    compute_slice(layer, 0, g_N, g_apad_main, g_staging_main);
    return;
  }
  g_layer_idx.store(layer, std::memory_order_relaxed);
  g_done.store(0, std::memory_order_relaxed);
  g_gen.fetch_add(1, std::memory_order_release);
  while (g_done.load(std::memory_order_acquire) != g_W)
    _mm_pause();
}

// ---------- cache disruptors ----------
static std::vector<std::thread> g_disruptors;
static std::atomic<bool> g_disrupt_stop{false};
static std::atomic<int> g_disrupt_ready{0};

static void disruptor_body(int cpu) {
  if (cpu >= 0 && !pin_to_cpu(cpu))
    fprintf(stderr, "disruptor: pin to cpu %d failed\n", cpu);
  const size_t n64 = (1ull << 30) / 8;  // 1 GiB
  std::vector<uint64_t> buf(n64, 0x0101010101010101ull);
  g_disrupt_ready.fetch_add(1, std::memory_order_release);
  uint64_t s = 0;
  while (!g_disrupt_stop.load(std::memory_order_relaxed)) {
    const uint64_t* p = buf.data();
    for (size_t i = 0; i < n64; i += 8)  // one load per 64 B line = read stream
      s += p[i];
    g_vsink64 = s;
  }
}

// ---------- misc ----------
static double now_s() {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec + t.tv_nsec * 1e-9;
}

static long g_call_no = 0;
static inline int next_layer() {
  if (g_L == 1) return 0;
  return (int)(g_call_no++ % g_L);
}

static std::vector<int> parse_cpu_list(const char* s) {
  std::vector<int> v;
  std::string tok;
  for (const char* p = s;; ++p) {
    if (*p == ',' || *p == 0) {
      if (!tok.empty()) v.push_back(atoi(tok.c_str()));
      tok.clear();
      if (*p == 0) break;
    } else {
      tok += *p;
    }
  }
  return v;
}

static void usage() {
  fprintf(stderr,
      "usage: bench_router_kernel --arm {avx_fp32|avx_bf16|amx_bf16} --n {32|128}\n"
      "  --m M(1..16) --regime {l2|cyclic|disrupted} [--layers L=1] [--iters I=auto]\n"
      "  [--workers W=1] [--worker-cpus a,b,..] [--disruptors D=1]\n"
      "  [--disruptor-cpus a,b,..] [--seconds S=2.0] [--validate]\n");
  exit(1);
}

int main(int argc, char** argv) {
  std::string arm_s, regime_s;
  int N = 0, M = 0, L = 1, W = 1, D = 1;
  long iters = 0;  // 0 = auto
  double seconds = 2.0;
  bool validate_only = false;
  std::vector<int> worker_cpus, disruptor_cpus;

  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto val = [&]() -> const char* {
      if (i + 1 >= argc) usage();
      return argv[++i];
    };
    if (a == "--arm") arm_s = val();
    else if (a == "--n") N = atoi(val());
    else if (a == "--m") M = atoi(val());
    else if (a == "--regime") regime_s = val();
    else if (a == "--layers") L = atoi(val());
    else if (a == "--iters") iters = atol(val());
    else if (a == "--workers") W = atoi(val());
    else if (a == "--worker-cpus") worker_cpus = parse_cpu_list(val());
    else if (a == "--disruptors") D = atoi(val());
    else if (a == "--disruptor-cpus") disruptor_cpus = parse_cpu_list(val());
    else if (a == "--seconds") seconds = atof(val());
    else if (a == "--validate") validate_only = true;
    else {
      fprintf(stderr, "unknown option %s\n", a.c_str());
      usage();
    }
  }

  if (arm_s == "avx_fp32") g_arm = ARM_FP32;
  else if (arm_s == "avx_bf16") g_arm = ARM_BF16;
  else if (arm_s == "amx_bf16") g_arm = ARM_AMX;
  else usage();
  if (N != 32 && N != 128) usage();
  if (M < 1 || M > MAXM) usage();
  if (regime_s == "l2") g_regime = R_L2;
  else if (regime_s == "cyclic") g_regime = R_CYCLIC;
  else if (regime_s == "disrupted") g_regime = R_DISRUPTED;
  else usage();
  if (g_regime == R_L2 && L != 1) {
    printf("# --layers ignored in l2 regime (forced to 1)\n");
    L = 1;
  }
  if (L < 1 || W < 1 || W > 64 || D < 1 || seconds <= 0) usage();
  if (!worker_cpus.empty() && (int)worker_cpus.size() < W) {
    fprintf(stderr, "--worker-cpus has %zu entries, need %d\n", worker_cpus.size(), W);
    return 1;
  }
  g_M = M;
  g_N = N;
  g_L = L;
  g_W = W;

  CpuFeat cpu = detect_cpu();
  printf("# bench_router_kernel arm=%s n=%d m=%d k=%d regime=%s layers=%d workers=%d"
         " disruptors=%d seconds=%.2f validate=%d\n",
      arm_s.c_str(), N, M, K, regime_s.c_str(), L, W,
      g_regime == R_DISRUPTED ? D : 0, seconds, (int)validate_only);
  printf("# cpu: avx512f=%d avx512_bf16=%d amx_tile=%d amx_bf16=%d\n", (int)cpu.avx512f,
      (int)cpu.avx512_bf16, (int)cpu.amx_tile, (int)cpu.amx_bf16);

  // runtime capability gates (SKIP is a success exit for the campaign script)
  if (!cpu.avx512f) {
    printf("SKIP %s (no avx512f)\n", arm_s.c_str());
    return 0;
  }
  if ((g_arm == ARM_BF16 || g_arm == ARM_AMX) && !cpu.avx512_bf16) {
    printf("SKIP %s (no avx512_bf16)\n", arm_s.c_str());
    return 0;
  }
  if (g_arm == ARM_AMX) {
#ifdef __AMX_BF16__
    if (!cpu.amx_tile || !cpu.amx_bf16 || !amx_request()) {
      printf("SKIP amx_bf16 (no AMX permission)\n");
      return 0;
    }
    printf("# amx: XTILEDATA permission granted\n");
#else
    printf("# not an AMX-enabled build\n");
    printf("SKIP amx_bf16 (no AMX permission)\n");
    return 0;
#endif
  }

  // worker column splits (amx needs 16-aligned splits: tile blocking granularity)
  g_n0.resize(W);
  g_n1.resize(W);
  for (int w = 0; w < W; ++w) {
    g_n0[w] = (int)((long)w * N / W);
    g_n1[w] = (int)((long)(w + 1) * N / W);
    if (g_arm == ARM_AMX && (g_n0[w] % 16 || g_n1[w] % 16)) {
      fprintf(stderr, "amx arm needs 16-aligned worker splits; n=%d workers=%d gives"
                      " [%d,%d)\n",
          N, W, g_n0[w], g_n1[w]);
      return 1;
    }
  }

  // ---- data: same fixed seed for all arms; per-arm storage rounding ----
  std::mt19937 rng(42);
  std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
  const size_t NK = (size_t)N * K;
  bf16* act = alloc64<bf16>((size_t)M * K);
  float* actf = alloc64<float>((size_t)M * K);  // widened act, for the reference
  for (size_t i = 0; i < (size_t)M * K; ++i) {
    act[i] = f2b(dist(rng));
    actf[i] = b2f(act[i]);
  }
  g_act = act;
  float* wf = nullptr;
  bf16* wb = nullptr;
  bf16* wv = nullptr;
  float* w0f = alloc64<float>(NK);  // layer-0 weights as the arm sees them
  std::vector<bf16> tmp_row(g_arm == ARM_AMX ? NK : 0);
  if (g_arm == ARM_FP32) wf = alloc64<float>((size_t)L * NK);
  else if (g_arm == ARM_BF16) wb = alloc64<bf16>((size_t)L * NK);
  else wv = alloc64<bf16>((size_t)L * NK);
  for (int l = 0; l < L; ++l) {
    for (size_t i = 0; i < NK; ++i) {
      const float v = dist(rng);
      if (g_arm == ARM_FP32) {
        wf[(size_t)l * NK + i] = v;
        if (l == 0) w0f[i] = v;
      } else {
        const bf16 r = f2b(v);
        if (g_arm == ARM_BF16) wb[(size_t)l * NK + i] = r;
        else tmp_row[i] = r;
        if (l == 0) w0f[i] = b2f(r);
      }
    }
    if (g_arm == ARM_AMX) pack_k_vnni(tmp_row.data(), wv + (size_t)l * NK, N, K);
  }
  g_wf = wf;
  g_wb = wb;
  g_wv = wv;
  g_logits = alloc64<float>((size_t)MAXM * N);

  if (g_arm == ARM_AMX && W == 1) {
    g_apad_main = alloc64<bf16>((size_t)MAXM * K);
    build_apad(g_apad_main);
    g_staging_main = alloc64<float>(16 * 16);
#ifdef __AMX_BF16__
    amx_config_maxshape();
#endif
  }
  if (W > 1) {
    for (int w = 0; w < W; ++w)
      g_workers.emplace_back(worker_body, w, worker_cpus.empty() ? -1 : worker_cpus[w]);
  }
  auto shutdown_workers = [&] {
    if (g_workers.empty()) return;
    g_quit.store(true, std::memory_order_relaxed);
    for (auto& t : g_workers)
      t.join();
    g_workers.clear();
  };

  // ---- reference (double accumulation over the values the arm sees) ----
  std::vector<double> ref((size_t)M * N);
  for (int m = 0; m < M; ++m)
    for (int n = 0; n < N; ++n) {
      double acc = 0;
      for (int k = 0; k < K; ++k)
        acc += (double)actf[(size_t)m * K + k] * (double)w0f[(size_t)n * K + k];
      ref[(size_t)m * N + n] = acc;
    }

  // ---- validation (always, before any timing; layer 0) ----
  const float CANARY = -777777.0f;
  for (size_t i = 0; i < (size_t)MAXM * N; ++i)
    g_logits[i] = CANARY;
  run_call(0);
  double worst_rel = 0;
  int worst_m = 0, worst_n = 0;
  for (int m = 0; m < M; ++m)
    for (int n = 0; n < N; ++n) {
      const double a = g_logits[(size_t)m * N + n], b = ref[(size_t)m * N + n];
      const double rel = std::fabs(a - b) / (std::fabs(b) + 1e-3);
      if (rel > worst_rel) {
        worst_rel = rel;
        worst_m = m;
        worst_n = n;
      }
    }
  if (worst_rel >= 2e-2) {
    fprintf(stderr,
        "VALIDATION FAIL: worst rel %.4g at m=%d n=%d got=%.8g want=%.8g\n", worst_rel,
        worst_m, worst_n, (double)g_logits[(size_t)worst_m * N + worst_n],
        ref[(size_t)worst_m * N + worst_n]);
    shutdown_workers();
    return 1;
  }
  for (int m = M; m < MAXM; ++m)  // zero-padded act rows must not leak into output
    for (int n = 0; n < N; ++n)
      if (g_logits[(size_t)m * N + n] != CANARY) {
        fprintf(stderr, "VALIDATION FAIL: padding row m=%d n=%d was written\n", m, n);
        shutdown_workers();
        return 1;
      }
  // abs-mass cross-check on sampled elements (t_amx_numerics.cpp pattern)
  {
    const int sm[4] = {0, M / 2, M - 1, 0};
    const int sn[4] = {0, N / 2, N - 1, N - 1};
    for (int s = 0; s < 4; ++s) {
      const int m = sm[s], n = sn[s];
      double mass = 0;
      for (int k = 0; k < K; ++k)
        mass += std::fabs(
            (double)actf[(size_t)m * K + k] * (double)w0f[(size_t)n * K + k]);
      const double tol = 1e-4 * mass + 1e-6;
      const double diff =
          std::fabs((double)g_logits[(size_t)m * N + n] - ref[(size_t)m * N + n]);
      if (diff > tol) {
        fprintf(stderr,
            "VALIDATION FAIL: abs-mass check m=%d n=%d diff=%.4g tol=%.4g\n", m, n,
            diff, tol);
        shutdown_workers();
        return 1;
      }
    }
  }
  double checksum = 0;
  for (int m = 0; m < M; ++m)
    for (int n = 0; n < N; ++n)
      checksum += g_logits[(size_t)m * N + n];
  printf("# validation: worst_rel=%.3e checksum=%.6e\n", worst_rel, checksum);

  if (validate_only) {
    printf("VALIDATE arm=%s n=%d m=%d regime=%s layers=%d workers=%d worst_rel=%.3e"
           " checksum=%.6e status=OK\n",
        arm_s.c_str(), N, M, regime_s.c_str(), L, W, worst_rel, checksum);
    shutdown_workers();
#ifdef __AMX_BF16__
    if (g_arm == ARM_AMX && W == 1) _tile_release();
#endif
    return 0;
  }

  // ---- disruptors (before calibration/warmup; stopped after timing) ----
  int n_disr = 0;
  if (g_regime == R_DISRUPTED) {
    if (!disruptor_cpus.empty() && (int)disruptor_cpus.size() < D) {
      fprintf(stderr, "--disruptor-cpus has %zu entries, need %d\n",
          disruptor_cpus.size(), D);
      shutdown_workers();
      return 1;
    }
    for (int d = 0; d < D; ++d)
      g_disruptors.emplace_back(
          disruptor_body, disruptor_cpus.empty() ? -1 : disruptor_cpus[d]);
    while (g_disrupt_ready.load(std::memory_order_acquire) != D)
      usleep(1000);  // wait for 1 GiB buffers to exist before measuring anything
    n_disr = D;
    printf("# disruptors: %d x 1 GiB read streams running\n", D);
  }

  // ---- iters calibration ----
  if (iters <= 0) {
    long batch = 1;
    double dt = 0;
    for (;;) {
      const double t0 = now_s();
      for (long i = 0; i < batch; ++i) {
        run_call(next_layer());
        g_vsink = g_logits[0];
      }
      dt = now_s() - t0;
      if (dt >= 0.05) break;
      batch *= 4;
    }
    iters = (long)(seconds / (dt / batch));
    if (iters < 100) iters = 100;
    printf("# calibrated iters=%ld (pre-measure %.3f us/call)\n", iters,
        dt / batch * 1e6);
  }
  const long warmup = std::max(3L, iters / 100);

  // ---- warmup + timed region ----
  for (long i = 0; i < warmup; ++i) {
    run_call(next_layer());
    g_vsink = g_logits[0];
  }
  const double t0 = now_s();
  for (long i = 0; i < iters; ++i) {
    run_call(next_layer());
    g_vsink = g_logits[0];
  }
  const double t1 = now_s();

  if (g_regime == R_DISRUPTED) {
    g_disrupt_stop.store(true, std::memory_order_relaxed);
    for (auto& t : g_disruptors)
      t.join();
  }
  shutdown_workers();
#ifdef __AMX_BF16__
  if (g_arm == ARM_AMX && W == 1) _tile_release();
#endif

  const double ns_per_call = (t1 - t0) * 1e9 / iters;
  printf("RESULT arm=%s n=%d m=%d regime=%s layers=%d workers=%d disruptors=%d"
         " iters=%ld ns_per_call=%.1f us_per_layer_call=%.3f gflops=%.2f"
         " checksum=%.6e\n",
      arm_s.c_str(), N, M, regime_s.c_str(), L, W, n_disr, iters, ns_per_call,
      ns_per_call / 1000.0, 2.0 * M * K * N / ns_per_call, checksum);

  free(act);
  free(actf);
  free(w0f);
  free(wf);
  free(wb);
  free(wv);
  free(g_logits);
  free(g_apad_main);
  free(g_staging_main);
  return 0;
}
