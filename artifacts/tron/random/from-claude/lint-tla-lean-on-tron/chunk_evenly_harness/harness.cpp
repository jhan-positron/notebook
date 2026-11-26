// Runs the real text of TRON's chunk_evenly (h/tron/models/model.hpp:212-346,
// tron commit 7eddde7895) on many inputs and tests the two properties that
// TRON states as asserts:
//   - model.hpp:288  the chunk sizes add up to n_token_jobs
//   - model.hpp:359  no chunk is larger than max_minibatch_size
//
// chunk_evenly_extract.inc is cut from model.hpp by run.sh. Only the types
// around it are substitutes. Layout used for the even/odd partner step: one KV
// page per group, the group's first token at page offset 0.
#include <algorithm>
#include <compare>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <type_traits>
#include <vector>

#define TRON(...)
#define TRON_ASSERT_EQ(a, b)                                          \
  do {                                                                \
    if (!((a) == (b))) {                                              \
      std::printf("TRON_ASSERT_EQ failed: %s == %s\n", #a, #b);       \
      std::abort();                                                   \
    }                                                                 \
  } while (0)

namespace tron {

constexpr size_t minibatch_grain_size = 8;  // h/tron/models/common.hpp:359

struct token_id {
  size_t i;
  explicit token_id(size_t i)
  : i(i) {}
  bool operator!=(token_id o) const noexcept {
    return i != o.i;
  }
};
struct token_job_id {
  size_t i;
  explicit token_job_id(size_t i)
  : i(i) {}
  token_job_id()
  : i(0) {}
};
struct token_batching_affinity_id {
  uint8_t i;
  explicit constexpr token_batching_affinity_id(uint8_t i) noexcept
  : i(i) {}
  constexpr std::strong_ordering operator<=>(
      token_batching_affinity_id const&) const noexcept = default;
};

struct mock_page {
  size_t first_token;
  size_t n;
  int offset_in_page(token_id t) const {
    return static_cast<int>(t.i - first_token);
  }
  size_t count() const {
    return n;
  }
  token_id at_offset(int o) const {
    return token_id(first_token + static_cast<size_t>(o));
  }
};

template <size_t Cap>
struct mock_state {
  static constexpr size_t max_minibatch_size = Cap;
  struct {
    int max_minibatches = -1;
  } cfg;
  struct {
    token_id operator[](token_job_id j) const {
      return token_id(j.i);  // token job k runs token k
    }
  } token_jobs;
  struct {
    token_job_id operator[](token_id t) const {
      return token_job_id(t.i);
    }
  } token_job_id_of_token;
  std::vector<mock_page> pages;
  std::vector<size_t> page_of_token;
  mock_page& page_of(token_id t) {
    return pages[page_of_token[t.i]];
  }
};

#include "chunk_evenly_extract.inc"

}  // namespace tron

namespace {

constexpr size_t cap = 128;  // max_minibatch_size of the llama plugin

std::vector<size_t> run(const std::vector<size_t>& group_sizes, int max_minibatches) {
  tron::mock_state<cap> state;
  state.cfg.max_minibatches = max_minibatches;
  std::vector<tron::token_batching_affinity_id> ids;
  for (size_t g = 0; g < group_sizes.size(); ++g) {
    state.pages.push_back({ids.size(), group_sizes[g]});
    for (size_t k = 0; k < group_sizes[g]; ++k) {
      ids.emplace_back(static_cast<uint8_t>(g));
      state.page_of_token.push_back(g);
    }
  }
  const auto chunks = tron::chunk_evenly(ids.size(), ids.data(), state);
  std::vector<size_t> sizes;
  for (const auto& c : chunks)
    sizes.push_back(c.size());
  return sizes;
}

void print(const char* label, const std::vector<size_t>& group_sizes, int mm) {
  const auto sizes = run(group_sizes, mm);
  std::printf("%s groups [", label);
  for (size_t i = 0; i < group_sizes.size(); ++i)
    std::printf("%s%zu", i ? ", " : "", group_sizes[i]);
  std::printf("] max_minibatches %d -> chunks [", mm);
  for (size_t i = 0; i < sizes.size(); ++i)
    std::printf("%s%zu", i ? ", " : "", sizes[i]);
  std::printf("]\n");
}

}  // namespace

int main() {
  // The worked examples of the October page, as a check of the harness.
  print("check:", {1, 1, 1, 1}, -1);
  print("check:", {20}, -1);
  print("check:", {300}, -1);

  // Every split of n token jobs into two groups (a, n - a), for every n up to
  // the scheduler's hard limit max_minibatches * max_minibatch_size
  // (h/tron/scheduler/full.hpp:1845-1852).
  for (int mm : {-1, 1, 2, 3, 4}) {
    const size_t n_max = mm > 0 ? static_cast<size_t>(mm) * cap : 4 * cap;
    size_t inputs = 0, sum_bad = 0, cap_bad = 0, count_bad = 0;
    std::vector<size_t> first_bad;
    for (size_t n = 1; n <= n_max; ++n) {
      for (size_t a = 1; a <= n; ++a) {
        std::vector<size_t> groups{a};
        if (n - a > 0) groups.push_back(n - a);
        const auto sizes = run(groups, mm);
        ++inputs;
        size_t total = 0, largest = 0;
        for (size_t s : sizes) {
          total += s;
          largest = std::max(largest, s);
        }
        if (total != n) ++sum_bad;
        if (mm > 0 && sizes.size() > static_cast<size_t>(mm)) ++count_bad;
        if (largest > cap) {
          if (cap_bad == 0) first_bad = groups;
          ++cap_bad;
        }
      }
    }
    std::printf("max_minibatches %2d: %6zu inputs (n <= %zu), sum wrong: %zu, "
                "too many chunks: %zu, chunk over %zu tokens: %zu\n",
        mm, inputs, n_max, sum_bad, count_bad, cap, cap_bad);
    if (!first_bad.empty()) print("  first input over the cap:", first_bad, mm);
  }
  return 0;
}
