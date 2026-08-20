#pragma once
// deep-dive K/V-wait / station probe (2026-08-11). When TRON_KVWAIT_FILE is
// set, records (tsc, dur, tag) triples into a file-backed mmap (survives
// SIGKILL). Tags: 0xx Q-channel wait (layer), 1xxx KV latch, 2xxx attn done
// barrier, 3xxx tx_launch dispatch instant (3000+dev idx), 4xxx rx completion
// instant (4000+dev idx). Dormant when the env var is unset.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <new>
#include <sys/mman.h>
#include <unistd.h>
#include <x86intrin.h>

namespace kvwait_probe {
struct state_t {
  static constexpr size_t kMax = size_t{1} << 24;
  struct rec { uint64_t t0, dur, tag; };
  rec* recs = nullptr;
  std::atomic<uint64_t>* count = nullptr;
  bool enabled = false;
  state_t() noexcept {
    const char* path = std::getenv("TRON_KVWAIT_FILE");
    if (!path) return;
    int fd = ::open(path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    if (fd < 0) return;
    size_t bytes = sizeof(uint64_t) + kMax * sizeof(rec);
    if (::ftruncate(fd, static_cast<off_t>(bytes)) != 0) { ::close(fd); return; }
    void* m = ::mmap(nullptr, bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    ::close(fd);
    if (m == MAP_FAILED) return;
    count = new (m) std::atomic<uint64_t>(0);
    recs = reinterpret_cast<rec*>(static_cast<char*>(m) + sizeof(uint64_t));
    enabled = true;
  }
  static uint64_t now() noexcept { return __rdtsc(); }
  void add(uint64_t t0, uint64_t dur, uint64_t tag) noexcept {
    uint64_t i = count->fetch_add(1, std::memory_order_relaxed);
    if (i < kMax) recs[i] = rec{t0, dur, tag};
  }
};
inline state_t& state() noexcept { static state_t s; return s; }
}  // namespace kvwait_probe
