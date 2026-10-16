#pragma once

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cmath>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <immintrin.h>
#include <limits>
#include <memory>
#include <new>
#include <optional>
#include <random>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include <sys/mman.h>  // mmap, munmap

#include "common/numerics/bf16.hpp"
#include "system/memory.hpp"
#include "tron/kernels/expr.hpp"
#include "tron/models/common.hpp"
#include "tron/simd/auto.hpp"
#include "tron/simd/fp32.hpp"
#include "tron/simd/types.hpp"
#include "tron/tensor/k_vnni.hpp"
#include "tron/tensor/slice.hpp"  // IWYU pragma: keep
#include "tron/tensor/tensor.hpp"
#include "tron/tensor/v_vnni.hpp"

// Note [KV Cache Store]
// ~~~~~~~~~~~~~~~~~~~~
//
// The way we store the KV cache is worth a lot of performance for the
// software attention kernel.
//
// The KV cache store in this file deals with two concepts:
// - The K and V data itself, see Note [KV Memory Layout] and
// - The causality portion of the attention mask, namely, which K tokens
//   affect which Q tokens.  See Note [Attention Causality Mask Representation].
//
// The causality mask is quite non-trivial in the presence of prompt
// sharing.
//
// The public interface to the KV cache store is the (public methods of
// the) `book` and `page` structs, and incidentally the `page_mask_t`
// struct for which subset of tokens on a page are to be computed when
// filling the KV cache.  The user is not expected to construct `page`
// instances directly.

// Note [KV Memory Layout]
// ~~~~~~~~~~~~~~~~~~~~~~
//
// We store K and V data to line up with the access pattern of the
// software attention kernel, so as to optimize the performance of the
// CPU's cache prefetcher, and the SIMD instructions needed to actually
// compute attention.
//
// At the finest grain, that means we store the KV data in _pages_ of
// contiguous tokens.  The attention computation proceeds page-wise,
// first doing Q*K^T for the query tokens affected by this page, then
// applying rolling softmax, and then finishing with E*V.  The latter
// benefits from pages having at least as many tokens as the SIMD width,
// because each V token becomes a SIMD lane.  These pages also form the
// minimum units of sequence-parallel reduction, per paged attention.
// See Note [Computing self-attention] for details.
//
// However, we also found it beneficial to lay out the pages themselves
// contiguously, so that the CPU cache prefetcher has the next page ready
// by the time a worker thread finishes with the current page.  Thus, the
// unit of memory allocation is the _book_, which reserves space for a
// request number of pages.  The book struct owns the actual memory, and
// a page is a lightweight reference to an appropriate section of a book.
// The book creates all the pages it will need when constructed and hands
// out references to them on demand.  The client is not expected to
// construct `page` instances directly.

// Note [Attention Causality Mask Representation]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
//
// The attention mask answers the question "For a particular Q token $i$, which K
// tokens may token $i$ attend to?". The models we are concerned with use causal
// attention, where each Q token may attend to the K tokens which precede it in the
// sequence. Ergo, in the token tree, each Q token attends to exactly its ancestors.
// Equivalently, each K token affects exactly its descendants.
//
// When we prepare a forward pass, we lay out the tokens present in the
// token tree using a pre-order traversal.  Therefore, for any K token,
// its descendants in the tree are laid out contiguously, starting with
// itself.  We store `lo` on each page via `set_lo` so that
// `at_offset`, `offset_for`, `contains`, and `offset_in_page` can map
// between token IDs and page offsets.  Visibility decisions are handled
// entirely by the ranged mask; see ranged_mask.hpp.

namespace tron {

struct node_base;

// Cache layout consumes geometry as data. Attention kernels separately carry
// the same dimensions as template arguments so their inner loops stay static.
struct kv_geometry {
  size_t n_kv_heads;
  size_t head_size;

  constexpr bool operator==(kv_geometry const&) const noexcept = default;
};

// Note [KV slot retention]
// ~~~~~~~~~~~~~~~~~~~~~~~~
// KV storage is reclaimed by slot, not by model layer or attention operation.
// Several operations can consume one slot, so its retention is the conservative
// aggregate of every consumer: one full-history consumer keeps the slot, while
// an all-sliding set uses its largest window. Generated plugins derive this
// value from their operation descriptors. Handwritten compatibility caches
// default to full history.
//
// Keeping the result in the persistent slot descriptor lets book allocation and
// reclamation use one immutable storage contract. It also avoids a per-node
// policy mask. Uniform full-history geometry lets a view preselect its arena,
// keeping policy lookup out of its K/V access path. Sliding storage adds a
// page-aligned chunk lookup so old pages can be reclaimed independently.
enum class kv_slot_retention_kind : uint8_t {
  full_history,
  sliding_window,
};

struct kv_slot_retention {
  kv_slot_retention_kind kind = kv_slot_retention_kind::full_history;
  size_t sliding_window_size = 0;

  static constexpr kv_slot_retention full_history() noexcept {
    return {};
  }

  static constexpr kv_slot_retention sliding_window(size_t size) noexcept {
    return {kv_slot_retention_kind::sliding_window, size};
  }

  constexpr bool reclaimable() const noexcept {
    return kind == kv_slot_retention_kind::sliding_window;
  }

  constexpr bool valid() const noexcept {
    return reclaimable() ? sliding_window_size > 0 : sliding_window_size == 0;
  }

  constexpr bool operator==(kv_slot_retention const&) const noexcept = default;
};

// Persistent K/V storage is described by slots, independently of the
// operations that read or write them.
struct kv_slot_spec {
  kv_geometry geometry;
  kv_slot_retention retention{};

  constexpr bool operator==(kv_slot_spec const&) const noexcept = default;
};

// A recurrent slot describes one opaque checkpoint in a cache topology (see
// sequence_cache_topology): the slot's complete recurrent state after the last
// token of a sequence. Its representation, storage, and lifecycle live outside
// the K/V cache.
struct recurrent_slot_spec {
  size_t checkpoint_bytes;
  size_t alignment;

  constexpr bool operator==(recurrent_slot_spec const&) const noexcept = default;
};

inline constexpr std::array<recurrent_slot_spec, 0> no_recurrent_slot_specs{};

// Note [Attention kernel registry]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// Attention has four independent identities:
//
// * attention_op_id orders execution;
// * model_layer_id carries diagnostics and model truncation
//   metadata;
// * kv_slot_id selects persistent K/V storage described by kv_slot_specs; and
// * attention_kernel_id selects static compute geometry.
//
// A plugin declares a dense registry of attention_kernel_spec values and an
// ordered array of attention_operation_descriptor values. Generated calls use
// the selected geometry as a non-type template argument, keeping inner loops
// static without deriving geometry from layers or cache slots. Runtime checks
// still verify that the selected slot declares the kernel's KV geometry.
//
// attention_operation_descriptor::hardware declares whether an operation is a
// hardware-attention candidate. Model construction validates its kernel and slot;
// runtime selection applies the remaining instance, device, configuration, scale,
// and window gates. See Note [Hardware attention eligibility] in model.hpp.
//
// Software-attention scratch arrays are sized to the largest registered geometry
// so operations can reuse them. Generated query and output buffers retain each
// operation's exact compile-time width.

struct attention_geometry {
  size_t n_query_heads;
  kv_geometry kv;

  constexpr size_t query_width() const noexcept {
    return n_query_heads * kv.head_size;
  }
  constexpr size_t kv_width() const noexcept {
    return kv.n_kv_heads * kv.head_size;
  }
  constexpr size_t kv_mul() const noexcept {
    return n_query_heads / kv.n_kv_heads;
  }
  constexpr bool valid() const noexcept {
    return n_query_heads > 0 && kv.n_kv_heads > 0 && kv.head_size > 0 &&
           n_query_heads % kv.n_kv_heads == 0 &&
           n_query_heads <= std::numeric_limits<size_t>::max() / kv.head_size &&
           kv.n_kv_heads <= std::numeric_limits<size_t>::max() / kv.head_size;
  }

  constexpr bool operator==(attention_geometry const&) const noexcept = default;
};

struct attention_kernel_spec {
  attention_kernel_id id;
  attention_geometry geometry;

  constexpr bool operator==(attention_kernel_spec const&) const noexcept = default;
};

enum class attention_hardware_capability {
  software_only,
  // Static operation, kernel, and KV-slot compatibility. Runtime routing still
  // applies device, policy, context-window, and model-wide scale gates.
  kv_slot_candidate,
};

struct attention_sink_id {
  size_t i;

  explicit constexpr attention_sink_id(size_t i) noexcept
  : i(i) {}

  constexpr bool operator==(attention_sink_id const&) const noexcept = default;
};

struct attention_sink_spec {
  attention_sink_id id;
  size_t n_query_heads;

  constexpr bool operator==(attention_sink_spec const&) const noexcept = default;
};

struct attention_operation_config {
  // Missing means full causal attention.
  std::optional<int> sliding_window_size;
  // Missing means this operation has no attention sink.
  std::optional<attention_sink_id> sink;
  float scale;

  constexpr attention_operation_config(std::optional<int> sliding_window_size,
      std::optional<attention_sink_id> sink,
      float scale) noexcept
  : sliding_window_size(sliding_window_size)
  , sink(sink)
  , scale(scale) {}

  constexpr bool operator==(attention_operation_config const&) const noexcept = default;
};

struct attention_operation_descriptor {
  attention_binding binding;
  attention_kernel_id kernel;
  attention_hardware_capability hardware;
  bool writes_kv;
  attention_operation_config config;

  constexpr bool operator==(
      attention_operation_descriptor const&) const noexcept = default;
};

// Hardware attention programs one model-wide scale. Require every operation that
// opts into it to use the same scale.
template <size_t n_operations>
constexpr bool valid_uniform_hardware_attention_scale(
    std::array<attention_operation_descriptor, n_operations> const&
        operations) noexcept {
  std::optional<float> scale;
  for (auto const& operation : operations) {
    if (operation.hardware != attention_hardware_capability::kv_slot_candidate)
      continue;
    if (scale && *scale != operation.config.scale) return false;
    scale = operation.config.scale;
  }
  return true;
}

template <size_t n_operations>
constexpr std::optional<float> uniform_hardware_attention_scale(
    std::array<attention_operation_descriptor, n_operations> const&
        operations) noexcept {
  for (auto const& operation : operations)
    if (operation.hardware == attention_hardware_capability::kv_slot_candidate)
      return operation.config.scale;
  return std::nullopt;
}

template <size_t n_kernels>
constexpr bool valid_attention_kernel_registry(
    std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  for (size_t i = 0; i < n_kernels; ++i) {
    if (kernels[i].id.i != i || !kernels[i].geometry.valid()) return false;
  }
  return true;
}

template <size_t n_kernels, size_t n_operations>
constexpr bool valid_attention_operation_descriptors(
    std::array<attention_kernel_spec, n_kernels> const& kernels,
    std::array<attention_operation_descriptor, n_operations> const&
        operations) noexcept {
  for (size_t i = 0; i < n_operations; ++i) {
    auto const& operation = operations[i];
    if (operation.binding.operation.i != i || operation.kernel.i >= n_kernels ||
        kernels[operation.kernel.i].id != operation.kernel ||
        (operation.hardware == attention_hardware_capability::kv_slot_candidate &&
            !operation.writes_kv) ||
        (operation.config.sliding_window_size &&
            *operation.config.sliding_window_size <= 0) ||
        (!(operation.config.scale > 0.0f) ||
            !(operation.config.scale < std::numeric_limits<float>::infinity())))
      return false;

    size_t slot_writers = 0;
    for (size_t j = 0; j < n_operations; ++j) {
      auto const& other = operations[j];
      if (operation.binding.kv_slot != other.binding.kv_slot) continue;
      slot_writers += other.writes_kv;
      if (!operation.writes_kv && other.writes_kv && j > i) return false;
    }
    if (slot_writers != 1) return false;
  }
  return true;
}

template <size_t n_operations, size_t n_slots>
constexpr bool valid_kv_slot_retentions(
    std::array<attention_operation_descriptor, n_operations> const& operations,
    std::array<kv_slot_spec, n_slots> const& slots) noexcept {
  for (size_t slot = 0; slot < n_slots; ++slot) {
    bool has_consumer = false;
    bool has_full_history_consumer = false;
    size_t largest_window = 0;
    for (auto const& operation : operations) {
      if (operation.binding.kv_slot.i != slot) continue;
      has_consumer = true;
      if (operation.config.sliding_window_size) {
        largest_window = std::max(
            largest_window, static_cast<size_t>(*operation.config.sliding_window_size));
      } else {
        has_full_history_consumer = true;
      }
    }
    kv_slot_retention const expected =
        has_consumer && !has_full_history_consumer
            ? kv_slot_retention::sliding_window(largest_window)
            : kv_slot_retention::full_history();
    if (slots[slot].retention != expected) return false;
  }
  return true;
}

template <size_t n_kernels, size_t n_operations, size_t n_slots, size_t n_sinks>
constexpr bool valid_attention_configuration(
    std::array<attention_kernel_spec, n_kernels> const& kernels,
    std::array<attention_operation_descriptor, n_operations> const& operations,
    std::array<kv_slot_spec, n_slots> const& slots,
    std::array<attention_sink_spec, n_sinks> const& sinks) noexcept {
  if (!valid_attention_kernel_registry(kernels) ||
      !valid_attention_operation_descriptors(kernels, operations) ||
      !valid_kv_slot_retentions(operations, slots))
    return false;
  for (size_t i = 0; i < n_sinks; ++i)
    if (sinks[i].id.i != i || sinks[i].n_query_heads == 0) return false;
  for (auto const& operation : operations) {
    if (operation.binding.kv_slot.i >= n_slots ||
        slots[operation.binding.kv_slot.i].geometry !=
            kernels[operation.kernel.i].geometry.kv)
      return false;
    if (operation.config.sink) {
      attention_sink_id const sink = *operation.config.sink;
      if (sink.i >= n_sinks || sinks[sink.i].id != sink ||
          sinks[sink.i].n_query_heads !=
              kernels[operation.kernel.i].geometry.n_query_heads)
        return false;
    }
  }
  return true;
}

template <size_t n_kernels, size_t n_operations, size_t n_slots>
constexpr bool valid_attention_configuration(
    std::array<attention_kernel_spec, n_kernels> const& kernels,
    std::array<attention_operation_descriptor, n_operations> const& operations,
    std::array<kv_slot_spec, n_slots> const& slots) noexcept {
  constexpr std::array<attention_sink_spec, 0> no_sinks{};
  return valid_attention_configuration(kernels, operations, slots, no_sinks);
}

template <size_t n_kernels, size_t n_slots>
constexpr bool is_hardware_attention_candidate(
    std::array<attention_kernel_spec, n_kernels> const& kernels,
    std::array<kv_slot_spec, n_slots> const& slots,
    attention_operation_descriptor const& operation,
    attention_geometry hardware_geometry) noexcept {
  if (operation.hardware != attention_hardware_capability::kv_slot_candidate ||
      !operation.writes_kv || operation.config.sliding_window_size ||
      operation.kernel.i >= n_kernels || operation.binding.kv_slot.i >= n_slots)
    return false;
  auto const& kernel = kernels[operation.kernel.i];
  return kernel.id == operation.kernel && kernel.geometry == hardware_geometry &&
         slots[operation.binding.kv_slot.i].geometry == kernel.geometry.kv;
}

template <size_t n_kernels>
constexpr attention_kernel_spec const& attention_kernel_at(
    std::array<attention_kernel_spec, n_kernels> const& kernels,
    attention_kernel_id id) noexcept {
  TRON_ASSERT_LT(id.i, n_kernels);
  TRON_ASSERT_EQ(kernels[id.i].id.i, id.i);
  return kernels[id.i];
}

template <size_t n_kernels>
constexpr size_t max_attention_query_width(
    std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  size_t result = 0;
  for (auto const& kernel : kernels)
    result = std::max(result, kernel.geometry.query_width());
  return result;
}

template <size_t n_kernels>
constexpr size_t max_attention_query_heads(
    std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  size_t result = 0;
  for (auto const& kernel : kernels)
    result = std::max(result, kernel.geometry.n_query_heads);
  return result;
}

template <size_t n_kernels>
constexpr size_t max_attention_kv_heads(
    std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  size_t result = 0;
  for (auto const& kernel : kernels)
    result = std::max(result, kernel.geometry.kv.n_kv_heads);
  return result;
}

template <size_t n_ops, size_t... i>
constexpr std::array<attention_operation_descriptor, n_ops>
uniform_attention_operations_impl(float scale, std::index_sequence<i...>) noexcept {
  return {attention_operation_descriptor{uniform_attention_binding(attention_op_id(i)),
      attention_kernel_id(0), attention_hardware_capability::kv_slot_candidate, true,
      attention_operation_config{std::nullopt, std::nullopt, scale}}...};
}

template <size_t n_ops>
constexpr std::array<attention_operation_descriptor, n_ops>
uniform_attention_operations(float scale) noexcept {
  return uniform_attention_operations_impl<n_ops>(
      scale, std::make_index_sequence<n_ops>{});
}

template <size_t n_slots>
constexpr std::array<kv_slot_spec, n_slots> uniform_kv_slot_specs(
    kv_geometry geometry) noexcept {
  std::array<kv_slot_spec, n_slots> slots{};
  for (kv_slot_spec& slot : slots)
    slot = {geometry};
  return slots;
}

template <size_t n_slots>
constexpr std::array<kv_slot_spec, n_slots> uniform_kv_slot_specs(kv_geometry geometry,
    std::array<kv_slot_retention, n_slots> const& retentions) noexcept {
  std::array<kv_slot_spec, n_slots> slots{};
  for (size_t slot = 0; slot < n_slots; ++slot)
    slots[slot] = {geometry, retentions[slot]};
  return slots;
}

template <size_t n_slots>
constexpr std::array<kv_slot_retention, n_slots>
full_history_kv_slot_retentions() noexcept {
  std::array<kv_slot_retention, n_slots> retentions{};
  return retentions;
}

// Implements a mask interface that is actually a contiguous range [lo,hi).
struct page_mask_t {
  static const size_t capacity = 1ul << 16;
  uint16_t lo, hi;

  page_mask_t() noexcept
  : lo(0)
  , hi(0) {}

  size_t count() const noexcept {
    return hi - lo;
  }

  bool contains(size_t i) const noexcept {
    return lo <= i && i < hi;
  }

  void insert(size_t i) noexcept {
    if (lo == hi) {
      lo = i;
      hi = i + 1;
    } else {
      TRON_ASSERT(i == hi, "non-contiguous page_mask_t not supported");
      ++hi;
    }
  }

  struct page_mask_iterator {
    uint16_t i;
    bool operator!=(const page_mask_iterator& other) const noexcept {
      return i != other.i;
    }
    page_mask_iterator& operator++() noexcept {
      ++i;
      return *this;
    }
    uint16_t operator*() const noexcept {
      return i;
    }
  };

  page_mask_iterator begin() const noexcept {
    return {lo};
  }
  page_mask_iterator end() const noexcept {
    return {hi};
  }
};

namespace detail {
template <size_t page_size, size_t head_size>
struct kv_block;
template <size_t page_size, size_t head_size>
  requires(head_size % chunk_size == 0)
struct scaled_v_expr;
}  // namespace detail

TRON(inline)
void log_kv_footprint(int64_t delta_bytes, int64_t delta_books) {
  static std::atomic_int64_t total_bytes = 0;
  static std::atomic_int64_t total_books = 0;
  static std::atomic_int64_t last_print_bytes = 0;
  static const int64_t granularity = [] {
    const char* env = std::getenv("TRON_LOG_KV_GRANULARITY");
    return env ? std::stoll(env) : 1024 * 1024 * 1024;  // 1GB
  }();

  int64_t old_bytes = total_bytes.fetch_add(delta_bytes, std::memory_order_relaxed);
  int64_t old_books = total_books.fetch_add(delta_books, std::memory_order_relaxed);
  int64_t new_bytes = old_bytes + delta_bytes;
  if (std::abs(new_bytes - last_print_bytes.load(std::memory_order_relaxed)) <
      granularity)
    return;
  last_print_bytes.store(new_bytes, std::memory_order_release);
  int64_t new_books = old_books + delta_books;
  double new_gb = new_bytes / (1024.0 * 1024.0 * 1024.0);
  spdlog::info("KV cache footprint: {:.2f} GB in {} books", new_gb, new_books);
}

// Note [Shared KV cache mechanics]
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
// `book` and `page` implement the mutable mechanics shared by uniform and
// value-described KV caches. Their layout policy supplies slot descriptors,
// per-arena prefix byte offsets, and whether a model-layer prefix may select
// fewer logical slots. Allocation, physical addressing, page completion, append,
// packed-V storage (through the typed operations of h/tron/tensor/v_vnni.hpp,
// see Note [VNNI Packed V layout]), packed-K storage (h/tron/tensor/k_vnni.hpp,
// see Note [K VNNI storage]), and EAGLE views therefore have one implementation.
//
// Uniform storage retains its [slot][head][page] ordering. A value-described
// layout replaces the constant slot stride with retention-group prefix byte
// offsets. Retained slots occupy a whole-book arena; sliding slots occupy
// independent chunks of whole pages, with the same within-page representation.
// EAGLE KV follows the active retained slots. Uniform full-history views
// preselect their base pointer when the view changes, so inner K/V access
// performs direct indexing. Other layouts select each slot's arena or chunk
// and offset. Execution scheduling is separate from storage policy.

template <size_t n_slots>
constexpr bool valid_kv_slot_specs(
    std::array<kv_slot_spec, n_slots> const& specs) noexcept {
  if constexpr (n_slots == 0) return false;
  for (kv_slot_spec const& spec : specs) {
    if (spec.geometry.n_kv_heads == 0 || spec.geometry.head_size == 0) return false;
    if (spec.geometry.head_size % chunk_size != 0) return false;
    if (!spec.retention.valid()) return false;
  }
  return true;
}

template <size_t n_slots>
constexpr bool uniform_kv_slot_geometry(
    std::array<kv_slot_spec, n_slots> const& specs) noexcept {
  if constexpr (n_slots == 0) return true;
  for (kv_slot_spec const& spec : specs)
    if (spec.geometry != specs[0].geometry) return false;
  return true;
}

template <size_t n_slots>
constexpr bool uniform_kv_slot_reclaimability(
    std::array<kv_slot_spec, n_slots> const& specs) noexcept {
  if constexpr (n_slots == 0) return true;
  for (kv_slot_spec const& spec : specs)
    if (spec.retention.reclaimable() != specs[0].retention.reclaimable()) return false;
  return true;
}

// The alignment floor of alignof(void*) equals sizeof(void*) on our targets, so
// every standard aligned allocator, posix_memalign included, accepts a valid
// alignment. A valid checkpoint_bytes rounds up to its alignment without
// overflowing size_t. An empty list is valid: it is the default for caches
// without recurrent state.
template <size_t n_slots>
constexpr bool valid_recurrent_slot_specs(
    std::array<recurrent_slot_spec, n_slots> const& specs) noexcept {
  for (recurrent_slot_spec const& spec : specs) {
    if (spec.checkpoint_bytes == 0 || spec.alignment < alignof(void*) ||
        !std::has_single_bit(spec.alignment))
      return false;
    if (spec.checkpoint_bytes >
        std::numeric_limits<size_t>::max() - (spec.alignment - 1))
      return false;
  }
  return true;
}

namespace detail {

constexpr bool checked_add(size_t lhs, size_t rhs, size_t& result) noexcept {
  if (rhs > std::numeric_limits<size_t>::max() - lhs) return false;
  result = lhs + rhs;
  return true;
}

constexpr bool checked_multiply(size_t lhs, size_t rhs, size_t& result) noexcept {
  if (lhs != 0 && rhs > std::numeric_limits<size_t>::max() / lhs) return false;
  result = lhs * rhs;
  return true;
}

struct kv_arena_offsets final {
  size_t retained = 0;
  size_t reclaimable = 0;

  constexpr size_t total() const noexcept {
    return retained + reclaimable;
  }
};

struct kv_slot_location final {
  bool reclaimable;
  size_t byte_offset;
};

template <size_t n_slots>
struct kv_slot_offsets final {
  std::array<kv_arena_offsets, n_slots + 1> values{};
  bool valid = true;
};

// Note [K VNNI storage]
// ~~~~~~~~~~~~~~~~~~~~~
// With TRON_K_VNNI (CMake option, default OFF) the K plane of every
// 128-dimension head holds the VNNI pair-interleaved layout of
// h/tron/tensor/k_vnni.hpp instead of one row per token. The bytes and the
// page capacity are the same. Only the order of the values changes. The gate
// is k_vnni::layout_on<head_size>, a property of the storage geometry. So
// every reader and writer of a slot sees the same layout, whatever the query
// type and whether AMX (Intel Advanced Matrix Extensions) is available at run
// time. V is unchanged. Its pair-interleaved layout is already the AMX B
// operand (the second matrix of the tile multiply).
//
// The plane is typed. kv_block::k is a k_vnni_tensor (the owner of the 16 KiB
// plane) for a VNNI slot and a bf16 array for a row-major slot. The plane is
// reached only through the owner's views (k_vnni_view) and the typed
// operations of h/tron/tensor/k_vnni.hpp (store_row, load_row, copy_token).
// No raw plane pointer leaves the cache. detail::k_vnni_access is
// the one route from a view to the plane address, for those operations, the
// score reader k_vnni::qk_group and the test-only book::fill_random. That
// mirrors the packed V plane (Note [VNNI Packed V layout]).
//
// Why: the VNNI plane is the B operand layout of the AMX tile multiply. An
// AMX QK kernel can read it directly and compute the scores S = Q . K^T in
// the orientation the softmax wants. The transposing store of the row-major
// kernel (Note [QK orientation] in amx_attn_iface.hpp) is then not needed.
// That kernel is not part of this change.
//
// Consumers of a VNNI slot, and how each one changes:
//   1. save_k (model.hpp) stores every token's row with page::set_k_row. That
//      store scatters the 64 dimension pairs into the token's column
//      (store_row). It issues 4 AVX-512 scatters that together write 4 bytes
//      into each of 64 64-byte pair rows. The row-major store was 4 64-byte
//      stores per token. TRON_AMX_DISABLE leaves the store untouched.
//   2. the dense AMX page path (self_attention.hpp) is not compiled for a
//      VNNI slot. Its kernel reads row-major K. Every page of a VNNI slot
//      takes the software path (temporary until the VNNI AMX kernel lands).
//   3. the software path, for every page of a VNNI slot, uses k_vnni::qk_group
//      with page::k_packed, the read-only view of the plane. That reader is
//      AVX-512 code with one token per vector
//      lane. It needs no per-token gather and no horizontal reduction. The
//      row-major dotter loop (the per-token dot-product loop of
//      self_attention.hpp) is
//      compiled only for row-major slots.
//   4. the FPGA (field-programmable gate array) staging path (gof::populate ->
//      shuffle_k_entry) needs one row per token. So page_info::k_head_fn
//      materializes it with page::get_k_row into caller-owned scratch.
//      v_head_fn already does the same for V. The staging bytes and the HBM
//      (High Bandwidth Memory, the FPGA device memory) layout are unchanged.
//   5. page copies (copy_storage_slot: append and defrag) copy a whole page
//      as one owner assignment (dst_block.k = src_block.k) when the range
//      covers the page. A token's position inside the page decides its column.
//      So every other range moves token by token (copy_token).
//   6. the row view page::k() does not exist for VNNI slots. A token's values
//      are not contiguous there. The layout-agnostic set_k_row / get_k_row
//      accessors exist for every slot.
// The kill switch keeps the layout. With TRON_AMX_DISABLE=1 a TRON_K_VNNI
// binary runs the AVX-512 VNNI reader, not the row-major dotter. So it is an
// AMX-off run of the same layout, not a rollback to the row-major binary's
// numerics. The fp32 (32-bit float) add order of the two readers differs (see
// the numerics contract in Note [AMX attention dispatch]). Until the VNNI AMX
// kernel is merged, TRON_AMX_DISABLE=1 changes no score and no visit path for
// 128-dimension heads. No AMX visit can occur for a VNNI slot.

// A kv_block holds two planes, K and V. Each plane is
// page_size tokens x head_size dims of bf16, so a block's size in bytes is
// KV_BLOCK_PLANES_2 * page_size * head_size * sizeof(bf16).
inline constexpr size_t KV_BLOCK_PLANES_2 = 2;

template <size_t n_slots>
consteval kv_slot_offsets<n_slots> make_kv_slot_offsets(
    std::array<kv_slot_spec, n_slots> const& specs) {
  kv_slot_offsets<n_slots> result;
  for (size_t slot = 0; slot < n_slots; ++slot) {
    size_t block_bytes;
    size_t slot_bytes;
    auto& next = result.values[slot + 1];
    next = result.values[slot];
    size_t& arena_offset =
        specs[slot].retention.reclaimable() ? next.reclaimable : next.retained;
    size_t total;
    result.valid =
        result.valid &&
        checked_multiply(KV_BLOCK_PLANES_2 * size_t{64} * sizeof(bf16),
            specs[slot].geometry.head_size, block_bytes) &&
        checked_multiply(specs[slot].geometry.n_kv_heads, block_bytes, slot_bytes) &&
        checked_add(arena_offset, slot_bytes, arena_offset) &&
        checked_add(next.retained, next.reclaimable, total);
    if (!result.valid) return result;
  }
  return result;
}

// primary_geometry is explicit because an empty uniform cache still needs a
// geometry for its source-compatible, untyped page accessors.
//
// The layout is the cache's compile-time slot schema, so it also carries the
// recurrent slot declarations; it assigns them no bytes. book and page are both
// parameterized by the layout, so caches that differ only in recurrent slots
// are distinct types.
template <auto slot_specs_,
    bool allow_layer_prefix_,
    kv_geometry primary_geometry_,
    auto recurrent_slot_specs_ = no_recurrent_slot_specs>
struct kv_layout final {
  inline static constexpr auto slot_specs = slot_specs_;
  inline static constexpr auto recurrent_slot_specs = recurrent_slot_specs_;
  static constexpr size_t n_slots = slot_specs.size();
  static constexpr bool allow_layer_prefix = allow_layer_prefix_;
  static constexpr bool uniform_geometry = uniform_kv_slot_geometry(slot_specs);
  static constexpr bool uniform_reclaimability =
      uniform_kv_slot_reclaimability(slot_specs);
  static constexpr kv_geometry primary_geometry = primary_geometry_;
  inline static constexpr auto offsets = make_kv_slot_offsets(slot_specs);

  static_assert(
      allow_layer_prefix || n_slots > 0, "A fixed KV cache requires at least one slot");
  static_assert(n_slots == 0 || slot_specs[0].geometry == primary_geometry,
      "Primary KV geometry must match slot zero");
  static_assert(n_slots == 0 || valid_kv_slot_specs(slot_specs),
      "KV slots must have nonzero, SIMD-aligned geometries");
  static_assert(valid_recurrent_slot_specs(recurrent_slot_specs),
      "Recurrent slots require nonzero checkpoints, power-of-two alignments of at "
      "least alignof(void*), and checkpoint sizes that still fit size_t after "
      "rounding up to alignment");
  static_assert(offsets.valid, "KV slot byte offsets overflow size_t");

  static constexpr size_t logical_slot_count_for_layers(
      size_t max_model_layers) noexcept {
    if constexpr (allow_layer_prefix) {
      TRON_ASSERT_LE(max_model_layers, n_slots);
      return max_model_layers;
    } else {
      (void)max_model_layers;
      return n_slots;
    }
  }

  static constexpr bool valid_logical_slot_count(size_t count) noexcept {
    if constexpr (allow_layer_prefix)
      return count <= n_slots;
    else
      return count == n_slots;
  }

  static constexpr std::optional<kv_arena_offsets> arena_sizes(
      size_t logical_slot_count, bool support_eagle) noexcept {
    if (!valid_logical_slot_count(logical_slot_count)) return std::nullopt;
    auto result = offsets.values[logical_slot_count];
    if (support_eagle &&
        (logical_slot_count == 0 ||
            !checked_add(result.retained, offsets.values[1].total(), result.retained)))
      return std::nullopt;
    size_t total;
    if (!checked_add(result.retained, result.reclaimable, total)) return std::nullopt;
    return result;
  }

  // Per-page offsets; EAGLE follows the active retained prefix.
  static constexpr kv_slot_location storage_location(
      kv_storage_offset offset, size_t logical_slot_count) noexcept {
    TRON_ASSERT(valid_logical_slot_count(logical_slot_count));
    TRON_ASSERT_LE(offset.i, logical_slot_count);
    bool const reclaimable =
        offset.i < logical_slot_count && slot_specs[offset.i].retention.reclaimable();
    auto const prefix = offsets.values[offset.i];
    return {reclaimable, reclaimable ? prefix.reclaimable : prefix.retained};
  }
};

template <size_t n_layers, size_t n_kv_heads, size_t head_size>
using uniform_kv_layout =
    kv_layout<uniform_kv_slot_specs<n_layers>(kv_geometry{n_kv_heads, head_size}),
        true,
        kv_geometry{n_kv_heads, head_size}>;

template <auto slot_specs,
    kv_geometry empty_geometry,
    auto recurrent_slot_specs = no_recurrent_slot_specs>
using fixed_kv_layout =
    kv_layout<slot_specs, false, empty_geometry, recurrent_slot_specs>;

}  // namespace detail

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t =
        detail::uniform_kv_layout<n_layers, n_kv_heads, head_size>>
struct alignas(64) page;

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t =
        detail::uniform_kv_layout<n_layers, n_kv_heads, head_size>>
struct alignas(64) book final
: noncopyable<book<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>> {
  using layout_t = layout_policy_t;
  using page_t = page<n_layers, n_kv_heads, head_size, x_bytes, layout_t>;
  inline static constexpr auto kv_slot_specs = layout_t::slot_specs;
  inline static constexpr auto recurrent_slot_specs = layout_t::recurrent_slot_specs;
  static constexpr size_t n_slots = kv_slot_specs.size();
  static constexpr size_t n_recurrent_slots = recurrent_slot_specs.size();
  // moving this to requires would require a lot of excessive inlining
  inline static const size_t page_size = page_t::page_size;
  static constexpr bool eagle_compatible = layout_t::uniform_geometry && x_bytes > 0;

  static_assert(n_layers == layout_t::n_slots);
  static_assert(layout_t::primary_geometry == kv_geometry{n_kv_heads, head_size});

  // Uniform topology has one logical KV slot per active model
  // layer. Fixed layouts retain their full descriptor count; the scheduler
  // never derives their slot count from the model-layer cap.
  static constexpr size_t logical_slot_count_for_layers(
      size_t max_model_layers) noexcept {
    return layout_t::logical_slot_count_for_layers(max_model_layers);
  }

  // EAGLE stores its logical slot-zero view after the validator's logical
  // slots. The extra physical storage has no logical descriptor.
  static constexpr size_t storage_slot_count_for_layers(
      size_t max_model_layers, bool support_eagle) noexcept {
    TRON_ASSERT(!support_eagle || eagle_compatible,
        "EAGLE cache views require uniform geometry and embedding storage");
    size_t storage_slot_count;
    TRON_ASSERT(detail::checked_add(logical_slot_count_for_layers(max_model_layers),
                    static_cast<size_t>(support_eagle), storage_slot_count),
        "KV storage slot count overflow");
    return storage_slot_count;
  }

  static constexpr size_t max_reclaimable_window_size(
      size_t logical_slot_count = n_slots) noexcept {
    TRON_ASSERT(layout_t::valid_logical_slot_count(logical_slot_count),
        "KV retention query exceeds the active logical slots");
    size_t result = 0;
    for (size_t slot_ix = 0; slot_ix < logical_slot_count; ++slot_ix) {
      kv_slot_spec const& slot = kv_slot_specs[slot_ix];
      if (slot.retention.reclaimable())
        result = std::max(result, slot.retention.sliding_window_size);
    }
    return result;
  }

  // Bound logical book capacity by the whole-book byte count of each retention
  // group and the EAGLE embeddings. The sliding-group bound covers all chunks
  // combined. See Note [KV slot retention] and Note [DMA-sized KV books].
  TRON(nodiscard, pure)
  static size_t max_pages_for_dma_allocation(size_t max_allocation_bytes,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false) noexcept {
    auto const per_page =
        calculate_allocation_sizes(1, storage_slot_count, support_eagle);
    if (!per_page) return 0;
    auto pages_for_buffer = [max_allocation_bytes](size_t bytes) {
      return bytes == 0 ? std::numeric_limits<size_t>::max()
                        : max_allocation_bytes / bytes;
    };
    size_t pages = std::min({pages_for_buffer(per_page->retained_kv_bytes),
        pages_for_buffer(per_page->reclaimable_kv_bytes),
        pages_for_buffer(per_page->x_storage_bytes)});
    if (per_page->total_bytes != 0) {
      pages = std::min(pages, static_cast<size_t>(std::numeric_limits<int64_t>::max()) /
                                  per_page->total_bytes);
    }
    return pages;
  }

  // Layer-keyed compatibility paths (including GOF) resolve only the logical
  // cache slot they need. Operation bindings live in attention descriptors.
  static constexpr kv_slot_id kv_slot(model_layer_id layer) noexcept
    requires(layout_t::allow_layer_prefix)
  {
    return uniform_kv_slot(layer);
  }

private:
  struct adopt_t {
    explicit adopt_t() = default;
  };

public:
  book(size_t n_pages,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false) noexcept
  : book(adopt_t{}, n_pages, storage_slot_count, support_eagle) {
    TRON_ASSERT(storage_valid_, "KV cache DMA allocation failed");
  }

  ~book() noexcept {
    if (storage_valid_) log_kv_footprint(-dma_size_bytes(), -1);
  }

  // The capacity of this book in pages.  Does not change during the
  // lifetime of the book.
  TRON(nodiscard, inline, pure)
  size_t page_capacity() const noexcept {
    return n_pages;
  }

  // The capacity of this book in tokens.  Does not change during the
  // lifetime of the book.
  TRON(nodiscard, inline, pure)
  size_t token_capacity() const noexcept {
    size_t result;
    TRON_ASSERT(detail::checked_multiply(n_pages, page_size, result),
        "KV token capacity overflow");
    return result;
  }

  // All DMA memory owned by this book, including EAGLE embedding storage.
  TRON(nodiscard, inline, pure)
  int64_t dma_size_bytes() const noexcept {
    size_t bytes = resident_kv_bytes();
    if (x_data) {
      size_t total;
      TRON_ASSERT(detail::checked_add(bytes, x_storage_bytes_, total),
          "KV allocation accounting overflow");
      bytes = total;
    }
    TRON_ASSERT_LE(bytes, static_cast<size_t>(std::numeric_limits<int64_t>::max()));
    return static_cast<int64_t>(bytes);
  }

  // Select EAGLE's secondary logical view, rooted at its extra,
  // descriptor-less physical slot. Other storage offsets do not define views.
  void set_storage_view(kv_storage_offset offset) noexcept {
    TRON_ASSERT(has_eagle_storage(), "Cache has no EAGLE storage view");
    TRON_ASSERT(offset == eagle_storage_offset(),
        "Only the declared EAGLE storage offset may select a secondary view");
    storage_view_offset_ = offset;
    refresh_kv_blocks_alias();
  }

  void reset_storage_view() noexcept {
    storage_view_offset_ = kv_storage_offset(0);
    refresh_kv_blocks_alias();
  }

  TRON(nodiscard, inline, pure)
  kv_storage_offset eagle_storage_offset() const noexcept {
    TRON_ASSERT(has_eagle_storage(), "EAGLE storage view requires EAGLE support");
    return kv_storage_offset(logical_slot_count());
  }

  // The number of physically allocated K/V slots. This may exceed the logical
  // descriptor count when the book carries an EAGLE cache view.
  TRON(nodiscard, inline, pure)
  size_t storage_slot_count() const noexcept {
    return storage_slot_count_;
  }

  // The number of logical K/V slots described by this cache's active layout.
  TRON(nodiscard, inline, pure)
  size_t logical_slot_count() const noexcept {
    return storage_slot_count_ - static_cast<size_t>(has_eagle_storage());
  }

  TRON(nodiscard, inline, pure)
  bool has_eagle_storage() const noexcept {
    return support_eagle_;
  }

  TRON(nodiscard, inline, pure)
  bool has_reclaimed_kv_storage() const noexcept {
    for (auto const& chunk : reclaimable_chunks_)
      if (chunk.state == reclaimable_chunk_state::reclaimed) return true;
    return false;
  }

  TRON(nodiscard, inline, pure)
  uint64_t reclaimable_kv_restore_attempt() const noexcept {
    return reclaimable_kv_restore_attempt_;
  }

  TRON(nodiscard, inline, pure)
  int64_t reclaimable_kv_storage_bytes() const noexcept {
    if (reclaimable_kv_restore_attempt_ != 0) {
      size_t bytes = 0;
      for (auto const& chunk : reclaimable_chunks_)
        if (chunk.restore_attempt == reclaimable_kv_restore_attempt_)
          bytes += chunk.bytes;
      return static_cast<int64_t>(bytes);
    }
    TRON_ASSERT_LE(reclaimable_kv_bytes_,
        static_cast<size_t>(std::numeric_limits<int64_t>::max()));
    return static_cast<int64_t>(reclaimable_kv_bytes_);
  }

  size_t reclaimable_chunk_count() const noexcept {
    return reclaimable_chunks_.size();
  }

  bool reclaimable_chunk_needs_restore(size_t index, uint64_t attempt) const noexcept {
    TRON_ASSERT_LT(index, reclaimable_chunks_.size());
    auto const& chunk = reclaimable_chunks_[index];
    return chunk.state == reclaimable_chunk_state::reclaimed ||
           (attempt != 0 && chunk.restore_attempt == attempt);
  }

  size_t reclaimable_chunk_token_begin(size_t index) const noexcept {
    TRON_ASSERT_LT(index, reclaimable_chunks_.size());
    return index * reclaimable_chunk_pages_ * page_size;
  }

  size_t reclaimable_chunk_token_end(size_t index) const noexcept {
    TRON_ASSERT_LT(index, reclaimable_chunks_.size());
    return reclaimable_chunk_token_begin(index) +
           reclaimable_chunks_[index].pages * page_size;
  }

  bool token_range_has_storage(size_t begin, size_t end) const noexcept {
    TRON_ASSERT_LE(begin, end);
    TRON_ASSERT_LE(end, token_capacity());
    if (begin == end || reclaimable_chunks_.empty()) return true;
    size_t const first = begin / (reclaimable_chunk_pages_ * page_size);
    size_t const last = (end - 1) / (reclaimable_chunk_pages_ * page_size);
    for (size_t index = first; index <= last; ++index)
      if (reclaimable_chunks_[index].state != reclaimable_chunk_state::resident)
        return false;
    return true;
  }

  // The scheduler proves that every populated page in the chunk is outside
  // every consumer's window before releasing it. Page identities stay stable.
  int64_t free_reclaimable_kv_chunk(size_t index) noexcept {
    TRON_ASSERT_LT(index, reclaimable_chunks_.size());
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == 0,
        "Cannot reclaim during unpublished KV restoration");
    auto& chunk = reclaimable_chunks_[index];
    if (chunk.state != reclaimable_chunk_state::resident) return 0;
    chunk.data.reset();
    // Lazy reservations beyond the populated range contain no history to replay.
    // Eager callers retain their allocate-all/free-all/restore-all behavior.
    chunk.state = lazy_reclaimable_ && reclaimable_chunk_token_begin(index) >= tok_ct
                      ? reclaimable_chunk_state::unallocated
                      : reclaimable_chunk_state::reclaimed;
    refresh_kv_blocks_alias();
    log_kv_footprint(-static_cast<int64_t>(chunk.bytes), 0);
    return static_cast<int64_t>(chunk.bytes);
  }

  // Compatibility operation for callers that have proved the whole book dead.
  int64_t free_reclaimable_kv_storage() noexcept {
    int64_t released = 0;
    for (size_t index = 0; index < reclaimable_chunks_.size(); ++index)
      released += free_reclaimable_kv_chunk(index);
    return released;
  }

  // Reserve sliding storage for new tokens before changing the token tree.
  // Failure preserves every pre-existing chunk; an unused tail is different
  // from reclaimed history and must not trigger cached-token replay.
  TRON(nodiscard)
  std::optional<int64_t> reserve_token_range(size_t begin, size_t end) noexcept {
    TRON_ASSERT_LE(begin, end);
    TRON_ASSERT_LE(end, token_capacity());
    if (begin == end || reclaimable_chunks_.empty()) return int64_t{0};
    size_t const first = begin / (reclaimable_chunk_pages_ * page_size);
    size_t const last = (end - 1) / (reclaimable_chunk_pages_ * page_size);
    for (size_t index = first; index <= last; ++index) {
      auto const state = reclaimable_chunks_[index].state;
      if (state != reclaimable_chunk_state::unallocated &&
          state != reclaimable_chunk_state::resident &&
          !(state == reclaimable_chunk_state::restoring &&
              reclaimable_chunks_[index].restore_attempt ==
                  reclaimable_kv_restore_attempt_))
        return std::nullopt;
    }
    size_t bytes = 0;
    for (size_t index = first; index <= last; ++index) {
      auto& chunk = reclaimable_chunks_[index];
      if (chunk.state != reclaimable_chunk_state::unallocated) continue;
      if (!allocate_reclaimable_chunk(chunk)) {
        // Unallocated chunks keep their state until the reservation commits.
        for (size_t rollback = first; rollback < index; ++rollback)
          if (reclaimable_chunks_[rollback].state ==
              reclaimable_chunk_state::unallocated)
            reclaimable_chunks_[rollback].data.reset();
        return std::nullopt;
      }
      bytes += chunk.bytes;
    }
    // A matched cached prefix may be provisionally restored while its novel
    // suffix reserves storage. Preserve those restoration tags until the
    // scheduler publishes readiness invalidation or rolls the attempt back.
    for (size_t index = first; index <= last; ++index)
      if (reclaimable_chunks_[index].state == reclaimable_chunk_state::unallocated)
        reclaimable_chunks_[index].state = reclaimable_chunk_state::resident;
    refresh_kv_blocks_alias();
    if (storage_valid_ && bytes != 0) log_kv_footprint(static_cast<int64_t>(bytes), 0);
    return static_cast<int64_t>(bytes);
  }

  // Restore missing chunks' addressability, not their contents. The scheduler
  // invalidates the whole populated book before publication. Never-allocated
  // tail chunks are excluded; resident neighbours survive a failed restore.
  TRON(nodiscard)
  std::optional<int64_t> restore_reclaimable_kv_storage(uint64_t attempt) noexcept {
    TRON_ASSERT(attempt != 0, "KV restore attempt zero is reserved");
    if (!has_reclaimed_kv_storage()) return int64_t{0};
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == 0,
        "KV book already belongs to a restore attempt");
    size_t bytes = 0;
    for (auto& chunk : reclaimable_chunks_) {
      if (chunk.state != reclaimable_chunk_state::reclaimed) continue;
      if (!allocate_reclaimable_chunk(chunk)) {
        for (auto& rollback : reclaimable_chunks_)
          if (rollback.restore_attempt == attempt) {
            rollback.data.reset();
            rollback.restore_attempt = 0;
          }
        return std::nullopt;
      }
      chunk.restore_attempt = attempt;
      bytes += chunk.bytes;
    }
    for (auto& chunk : reclaimable_chunks_)
      if (chunk.restore_attempt == attempt)
        chunk.state = reclaimable_chunk_state::restoring;
    reclaimable_kv_restore_attempt_ = attempt;
    refresh_kv_blocks_alias();
    log_kv_footprint(static_cast<int64_t>(bytes), 0);
    return static_cast<int64_t>(bytes);
  }

  int64_t abort_reclaimable_kv_restore(uint64_t attempt) noexcept {
    TRON_ASSERT(attempt != 0, "KV restore attempt zero is reserved");
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == attempt,
        "KV book belongs to another restore attempt");
    int64_t released = 0;
    for (size_t index = 0; index < reclaimable_chunks_.size(); ++index) {
      auto& chunk = reclaimable_chunks_[index];
      if (chunk.restore_attempt == attempt) {
        chunk.data.reset();
        // Allocation retry can evict an inactive continuation while this
        // book is provisionally restored. Its empty tail is now fresh space.
        chunk.state = reclaimable_chunk_token_begin(index) >= tok_ct
                          ? reclaimable_chunk_state::unallocated
                          : reclaimable_chunk_state::reclaimed;
        chunk.restore_attempt = 0;
        released += static_cast<int64_t>(chunk.bytes);
      }
    }
    reclaimable_kv_restore_attempt_ = 0;
    refresh_kv_blocks_alias();
    log_kv_footprint(-released, 0);
    return released;
  }

  // Publish only after the scheduler invalidates every dependent edge's
  // readiness. Restored KV must be recomputed before it is read.
  void finish_reclaimable_kv_restore(uint64_t attempt) noexcept {
    TRON_ASSERT(attempt != 0, "KV restore attempt zero is reserved");
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == attempt,
        "KV book belongs to another restore attempt");
    for (auto& chunk : reclaimable_chunks_)
      if (chunk.restore_attempt == attempt) {
        chunk.state = reclaimable_chunk_state::resident;
        chunk.restore_attempt = 0;
      }
    reclaimable_kv_restore_attempt_ = 0;
  }

  // Number of tokens' worth of space that is actually in use for
  // valid tokens (see Note [KV Token Lifetimes]) in this book.  The
  // used tokens are always in the beginning.
  TRON(nodiscard, inline, pure)
  size_t size() const noexcept {
    return tok_ct;
  }

  // Allocate more valid tokens in this book.  The new tokens are
  // always allocated at the end.
  void increment_tokens_used(size_t amount = 1) noexcept {
    size_t new_count;
    TRON_ASSERT(
        detail::checked_add(tok_ct, amount, new_count) && new_count <= token_capacity(),
        "KV token count exceeds capacity");
    tok_ct = new_count;
  }

  // Deallocate tokens that were valid in this book.  The tokens
  // are always deallocated from the end.
  void decrement_tokens_used(size_t amount = 1) noexcept {
    TRON_ASSERT_GE(tok_ct, amount);
    tok_ct -= amount;
    if (amount == 0) return;
    // Once a reclaimed chunk contains no valid tokens, future writes are a
    // fresh reservation rather than restoration of cached history. No DMA
    // allocation or accounting changes: reclaimed chunks already own no bytes.
    for (size_t index = 0; index < reclaimable_chunks_.size(); ++index) {
      auto& chunk = reclaimable_chunks_[index];
      if (chunk.state == reclaimable_chunk_state::reclaimed &&
          reclaimable_chunk_token_begin(index) >= tok_ct)
        chunk.state = reclaimable_chunk_state::unallocated;
    }
  }

  // The page that contains the given token, by offset _in this book_.
  page_t* page_of(size_t token) noexcept {
    return &(pages[token / page_size]);
  }

  // The page that contains the given token, by offset _in this book_.
  const page_t* page_of(size_t token) const noexcept {
    return &(pages[token / page_size]);
  }

  // Append another book's data onto my data.
  // Used for defragmenting books created by tree-shaped speculation.
  void append(const book& src) noexcept {
    TRON_ASSERT_EQ(storage_slot_count_, src.storage_slot_count_);
    TRON_ASSERT_EQ(has_eagle_storage(), src.has_eagle_storage());
    TRON_ASSERT(!has_reclaimed_kv_storage() && !src.has_reclaimed_kv_storage(),
        "Cannot defragment a book with reclaimed KV storage");
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == 0 &&
                    src.reclaimable_kv_restore_attempt_ == 0,
        "Cannot defragment a book with unpublished KV restoration");
    // Copy page-wise.
    // Each destination page copies from at most two source pages, and
    // each source page copies to at most two destination pages.
    size_t src_begin = 0;
    const size_t src_end = src.tok_ct;
    size_t dst_begin = tok_ct;
    size_t dst_end;
    TRON_ASSERT(detail::checked_add(dst_begin, src.tok_ct, dst_end) &&
                    dst_end <= token_capacity(),
        "Appended KV tokens exceed capacity");
    TRON_ASSERT(token_range_has_storage(dst_begin, dst_end) &&
                    src.token_range_has_storage(0, src.tok_ct),
        "Cannot defragment into unreserved KV storage");
    while (src_begin != src_end) {
      const page_t* src_pg = src.page_of(src_begin);
      page_t* dst_pg = page_of(dst_begin);
      size_t src_offset = src_begin % page_size;
      size_t dst_offset = dst_begin % page_size;
      size_t count = std::min(page_size - dst_offset, page_size - src_offset);
      count = std::min(count, src_end - src_begin);
      dst_pg->copy_from(src_pg, src_offset, dst_offset, count);
      src_begin += count;
      dst_begin += count;
    }
    TRON_ASSERT_EQ(dst_begin, dst_end);
    tok_ct = dst_end;
  }

  // Fill all kv_block data with random values from the given generator.
  // For testing only.  Writes raw bf16 data that bypasses the zero-init
  // V slot invariant (see Note [Zero-Initialized V Slots]). This whole-block
  // fill is the one documented exception to the typed packed-V and packed-K
  // access rules (Note [VNNI Packed V layout] in h/tron/tensor/v_vnni.hpp, Note
  // [K VNNI storage] above): it interprets no coordinates and marks no token
  // complete.
  template <typename Gen>
  void fill_random(Gen& gen) noexcept {
    std::normal_distribution<> dis(0.0, 1.0);
    for_each_active_slot([&]<size_t slot, kv_geometry geometry>() {
      fill_storage_slot<geometry>(kv_storage_offset(slot), dis, gen);
    });
    if (has_eagle_storage())
      fill_storage_slot<layout_t::primary_geometry>(eagle_storage_offset(), dis, gen);
  }

private:
  friend struct page<n_layers, n_kv_heads, head_size, x_bytes, layout_t>;

public:
  // Fallible KV-book factory for cache growth (memory_pressure_governor §8).
  // Allocates the DMA payload through the fallible
  // try_ forms and returns nullptr if either allocation fails, instead of
  // aborting like the public constructor. The shared_ptr control block and the
  // page vector stay infallible host-heap allocations (the backstop covers
  // DMA-payload failure only). log_kv_footprint fires exactly once, in
  // the adopt-constructor.
  TRON(nodiscard)
  static std::shared_ptr<book> try_create(size_t n_pages,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false) noexcept {
    auto result =
        std::make_shared<book>(adopt_t{}, n_pages, storage_slot_count, support_eagle);
    return result->storage_valid_ ? std::move(result) : nullptr;
  }

  // Scheduler construction reserves only retained storage. Sliding chunks are
  // reserved transactionally for the actual novel token range before insertion.
  TRON(nodiscard)
  static std::shared_ptr<book> try_create_lazy(size_t n_pages,
      size_t storage_slot_count = n_slots,
      bool support_eagle = false) noexcept {
    auto result = std::make_shared<book>(
        adopt_t{}, n_pages, storage_slot_count, support_eagle, true);
    return result->storage_valid_ ? std::move(result) : nullptr;
  }

  // Tag-gated fallible construction keeps a partially allocated book private.
  // Eager consumers reserve every group; scheduler books defer sliding chunks.
  // Failure releases every allocation and leaves storage_valid_ false.
  book(adopt_t,
      size_t n_pages,
      size_t storage_slot_count,
      bool support_eagle,
      bool lazy_reclaimable = false) noexcept
  : n_pages(n_pages)
  , support_eagle_(support_eagle)
  , lazy_reclaimable_(lazy_reclaimable)
  , storage_slot_count_(storage_slot_count)
  , tok_ct(0) {
    auto const sizes =
        calculate_allocation_sizes(n_pages, storage_slot_count, support_eagle);
    if (!sizes) return;
    retained_kv_bytes_ = sizes->retained_kv_bytes;
    reclaimable_kv_bytes_ = sizes->reclaimable_kv_bytes;
    x_storage_bytes_ = sizes->x_storage_bytes;
    if (!initialize_reclaimable_chunks() || !allocate_retained_storage() ||
        (!lazy_reclaimable && !reserve_token_range(0, token_capacity()).has_value())) {
      clear_kv_storage();
      return;
    }
    if (support_eagle) {
      auto x = hardware::try_make_unique_dma_for_overwrite<uint8_t[]>(x_storage_bytes_);
      if (!x) {
        clear_kv_storage();
        return;
      }
      x_data.emplace(std::move(x));
    }
    refresh_kv_blocks_alias();
    initialize_pages();
    storage_valid_ = true;
    log_kv_footprint(dma_size_bytes(), 1);
  }

private:
  const size_t n_pages;

  // Retained KV keeps its whole-book arena. Sliding slots are packed together
  // into independent page-aligned chunks, preserving each page's K/V layout.
  std::optional<hardware::unique_dma<uint8_t[]>> retained_data;
  enum class reclaimable_chunk_state : uint8_t {
    unallocated,
    resident,
    reclaimed,
    restoring,
  };
  struct reclaimable_chunk final {
    size_t pages;
    size_t bytes;
    std::optional<hardware::unique_dma<uint8_t[]>> data;
    reclaimable_chunk_state state = reclaimable_chunk_state::unallocated;
    uint64_t restore_attempt = 0;
  };
  std::vector<reclaimable_chunk> reclaimable_chunks_;
  size_t reclaimable_chunk_pages_ = 0;
  // Shifted so a model and its EAGLE speculator can share a KV cache.
  uint8_t* kv_blocks_alias = nullptr;
  kv_storage_offset storage_view_offset_{0};
  bool support_eagle_;
  bool lazy_reclaimable_;
  std::optional<hardware::unique_dma<uint8_t[]>> x_data;

  std::vector<page_t> pages;
  size_t storage_slot_count_;
  size_t retained_kv_bytes_ = 0;
  size_t reclaimable_kv_bytes_ = 0;
  size_t x_storage_bytes_ = 0;
  bool storage_valid_ = false;
  uint64_t reclaimable_kv_restore_attempt_ = 0;
  // The number of valid tokens in this book, in the sense of Note [KV Token Lifetimes].
  size_t tok_ct;

  static constexpr size_t storage_alignment = std::max<size_t>(64, chunk_alignment);

  struct allocation_sizes final {
    size_t retained_kv_bytes;
    size_t reclaimable_kv_bytes;
    size_t x_storage_bytes;
    size_t total_bytes;
  };

  static std::optional<allocation_sizes> calculate_allocation_sizes(
      size_t n_pages, size_t storage_slot_count, bool support_eagle) noexcept {
    if (storage_slot_count < static_cast<size_t>(support_eagle)) return std::nullopt;
    size_t const logical_slot_count =
        storage_slot_count - static_cast<size_t>(support_eagle);
    if (!layout_t::valid_logical_slot_count(logical_slot_count)) return std::nullopt;
    if (support_eagle && (!eagle_compatible || logical_slot_count == 0))
      return std::nullopt;

    auto const unit_bytes = layout_t::arena_sizes(logical_slot_count, support_eagle);
    if (!unit_bytes) return std::nullopt;
    size_t retained_kv_bytes;
    size_t reclaimable_kv_bytes;
    if (!detail::checked_multiply(n_pages, unit_bytes->retained, retained_kv_bytes) ||
        !detail::checked_multiply(
            n_pages, unit_bytes->reclaimable, reclaimable_kv_bytes))
      return std::nullopt;

    size_t x_storage_bytes = 0;
    if (support_eagle) {
      size_t token_capacity;
      if (!detail::checked_multiply(n_pages, page_size, token_capacity) ||
          !detail::checked_multiply(token_capacity, x_bytes, x_storage_bytes))
        return std::nullopt;
    }
    size_t kv_bytes;
    size_t total_bytes;
    if (!detail::checked_add(retained_kv_bytes, reclaimable_kv_bytes, kv_bytes) ||
        !detail::checked_add(kv_bytes, x_storage_bytes, total_bytes) ||
        total_bytes > static_cast<size_t>(std::numeric_limits<int64_t>::max()))
      return std::nullopt;
    return allocation_sizes{
        retained_kv_bytes, reclaimable_kv_bytes, x_storage_bytes, total_bytes};
  }

  TRON(nodiscard, inline, pure)
  uint8_t* slot_base(kv_storage_offset offset) const noexcept {
    TRON_ASSERT_LT(offset.i, storage_slot_count_);
    auto const location = layout_t::storage_location(offset, logical_slot_count());
    if (location.reclaimable && reclaimable_chunks_.empty()) return nullptr;
    auto const& arena =
        location.reclaimable ? reclaimable_chunks_.front().data : retained_data;
    if (!arena) return nullptr;
    size_t const storage_pages =
        location.reclaimable ? reclaimable_chunks_.front().pages : n_pages;
    size_t byte_offset;
    TRON_ASSERT(
        detail::checked_multiply(storage_pages, location.byte_offset, byte_offset),
        "KV slot byte offset overflow");
    return arena->get() + byte_offset;
  }

  bool initialize_reclaimable_chunks() {
    if (reclaimable_kv_bytes_ == 0) return true;
    TRON_ASSERT_GT(n_pages, 0);
    size_t const page_bytes = reclaimable_kv_bytes_ / n_pages;
    constexpr size_t chunk_target_bytes = size_t{256} * 1024 * 1024;
    size_t const allocation_limit = hardware::dma_max_allocation_bytes();
    if (page_bytes > allocation_limit) return false;
    size_t const target = std::min(chunk_target_bytes, allocation_limit);
    reclaimable_chunk_pages_ =
        std::min(n_pages, std::max(size_t{1}, target / page_bytes));
    size_t remaining = n_pages;
    while (remaining != 0) {
      size_t const pages = std::min(remaining, reclaimable_chunk_pages_);
      reclaimable_chunks_.push_back(
          {.pages = pages, .bytes = pages * page_bytes, .data = std::nullopt});
      remaining -= pages;
    }
    return true;
  }

  bool allocate_retained_storage() noexcept {
    if (retained_kv_bytes_ == 0) return true;
    if (retained_kv_bytes_ > hardware::dma_max_allocation_bytes()) return false;
    auto arena = hardware::try_make_unique_dma_for_overwrite<uint8_t[]>(
        retained_kv_bytes_, std::align_val_t(storage_alignment));
    if (!arena) return false;
    retained_data.emplace(std::move(arena));
    return true;
  }

  bool allocate_reclaimable_chunk(reclaimable_chunk& chunk) noexcept {
    TRON_ASSERT(!chunk.data, "KV chunk already has storage");
    if (chunk.bytes > hardware::dma_max_allocation_bytes()) return false;
    auto arena = hardware::try_make_unique_dma_for_overwrite<uint8_t[]>(
        chunk.bytes, std::align_val_t(storage_alignment));
    if (!arena) return false;
    chunk.data.emplace(std::move(arena));
    return true;
  }

  // Note [KV block lifetime]
  // ~~~~~~~~~~~~~~~~~~~~~~~~
  // The cache reads each arena and chunk as arrays of kv_block objects. C++
  // allows a member access only on an object whose lifetime has started. A
  // cast does not start it. Here the allocation starts it.
  // try_make_unique_dma_for_overwrite gets the memory through a function named
  // operator new[], and such a call creates the objects that the program then
  // uses (Note [DMA allocation creates objects] in system/memory.hpp). These are
  // a byte array over the whole arena and, nested in it, the kv_block arrays:
  // one per arena in the uniform layout, one per slot region otherwise
  // ([intro.object]). This works only while kv_block and its members stay
  // trivial to construct and to destroy. The accessors assert that. No bytes are
  // written.
  //
  // The accessors turn an arena address (a uint8_t*) into a kv_block pointer
  // with std::launder. A plain cast would still point at the byte, not at the
  // kv_block that lives there ([expr.static.cast], [basic.life], [ptr.launder]).
  //
  // K and V are separate members: a bf16 array, or a trivially copyable owner
  // (k_vnni_tensor for packed K, v_vnni_tensor for packed V). Fill each member
  // separately. SIMD load addresses inside a packed plane come from the plane's
  // access helper (detail::k_vnni_access, detail::v_vnni_access). SIMD
  // operations still use compiler intrinsics, but do not require vector
  // objects in the stored plane.

  void clear_kv_storage() noexcept {
    retained_data.reset();
    reclaimable_chunks_.clear();
    x_data.reset();
    kv_blocks_alias = nullptr;
  }

  size_t resident_kv_bytes() const noexcept {
    size_t bytes = retained_data ? retained_kv_bytes_ : 0;
    for (auto const& chunk : reclaimable_chunks_)
      if (chunk.data) bytes += chunk.bytes;
    return bytes;
  }

  struct storage_page final {
    uint8_t* base;
    size_t pages;
    size_t page;
  };

  storage_page slot_page(kv_storage_offset offset, size_t pg) const noexcept {
    auto const location = layout_t::storage_location(offset, logical_slot_count());
    if (!location.reclaimable) return {slot_base(offset), n_pages, pg};
    size_t const chunk_index = pg / reclaimable_chunk_pages_;
    auto const& chunk = reclaimable_chunks_[chunk_index];
    uint8_t* const base =
        chunk.data ? chunk.data->get() + chunk.pages * location.byte_offset : nullptr;
    return {base, chunk.pages, pg % reclaimable_chunk_pages_};
  }

  void refresh_kv_blocks_alias() noexcept {
    TRON_ASSERT(
        storage_slot_count_ == 0 || storage_view_offset_.i < storage_slot_count_,
        "KV storage view offset out of bounds");
    kv_blocks_alias =
        storage_slot_count_ == 0 ? nullptr : slot_base(storage_view_offset_);
  }

  void initialize_pages() {
    pages.reserve(n_pages);
    for (size_t pg = 0; pg < n_pages; ++pg)
      pages.emplace_back(*this);
  }

  template <size_t... slots, typename F>
  static constexpr void for_each_slot_impl(
      std::index_sequence<slots...>, F&& function) {
    (function.template operator()<slots, kv_slot_specs[slots].geometry>(), ...);
  }

  template <typename F>
  void for_each_active_slot(F&& function) const {
    size_t const active_slots = logical_slot_count();
    for_each_slot_impl(
        std::make_index_sequence<n_slots>{}, [&]<size_t slot, kv_geometry geometry>() {
          if (slot < active_slots) function.template operator()<slot, geometry>();
        });
  }

public:
  template <kv_geometry geometry>
  static consteval bool declares_geometry() {
    if constexpr (n_slots == 0)
      return layout_t::uniform_geometry && geometry == layout_t::primary_geometry;
    for (kv_slot_spec const& spec : kv_slot_specs)
      if (spec.geometry == geometry) return true;
    return false;
  }

  template <kv_geometry geometry>
  static constexpr bool slot_matches(kv_slot_id slot) noexcept {
    return slot.i < n_slots && kv_slot_specs[slot.i].geometry == geometry;
  }

  static constexpr size_t kv_storage_bytes_for_pages(size_t n_pages) noexcept {
    size_t result;
    TRON_ASSERT(detail::checked_multiply(
                    n_pages, layout_t::offsets.values.back().total(), result),
        "KV storage byte count overflow");
    return result;
  }

private:
  TRON(nodiscard, inline, pure)
  auto& kv_block(kv_slot_id slot, size_t kv_head, size_t pg) noexcept
    requires(layout_t::uniform_geometry)
  {
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == 0,
        "Access to unpublished reclaimable KV restoration");
    using kv_block_t = detail::kv_block<page_size, head_size>;
    static_assert(std::is_trivially_default_constructible_v<kv_block_t> &&
                      std::is_trivially_copyable_v<kv_block_t> &&
                      std::is_trivially_destructible_v<kv_block_t>,
        "The DMA allocation creates KV blocks; see Note [KV block lifetime]");
    TRON_ASSERT_LT(pg, n_pages);
    TRON_ASSERT_LT(kv_head, n_kv_heads);
    if constexpr (layout_t::uniform_reclaimability &&
                  (n_slots == 0 || !kv_slot_specs[0].retention.reclaimable())) {
      TRON_ASSERT(kv_blocks_alias != nullptr, "Access to reclaimed KV slot {}", slot.i);
      if (storage_view_offset_.i != 0)
        TRON_ASSERT(slot.i == 0, "EAGLE exposes only logical KV slot zero");
      auto* blocks = std::launder(reinterpret_cast<kv_block_t*>(kv_blocks_alias));
      return blocks[(slot.i * n_kv_heads + kv_head) * n_pages + pg];
    } else {
      size_t const physical_slot =
          storage_view_offset_.i == 0 ? slot.i : storage_view_offset_.i;
      TRON_ASSERT(storage_view_offset_.i == 0 || slot.i == 0,
          "EAGLE exposes only logical KV slot zero");
      auto const storage = slot_page(kv_storage_offset(physical_slot), pg);
      TRON_ASSERT(storage.base != nullptr, "Access to missing KV slot {}", slot.i);
      auto* blocks = std::launder(reinterpret_cast<kv_block_t*>(storage.base));
      return blocks[kv_head * storage.pages + storage.page];
    }
  }

  TRON(nodiscard, inline, pure)
  auto const& kv_block(kv_slot_id slot, size_t kv_head, size_t pg) const noexcept
    requires(layout_t::uniform_geometry)
  {
    return const_cast<book*>(this)->kv_block(slot, kv_head, pg);
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto& kv_block_at_storage(
      kv_storage_offset offset, size_t kv_head, size_t pg) noexcept {
    TRON_ASSERT(reclaimable_kv_restore_attempt_ == 0,
        "Access to unpublished reclaimable KV restoration");
    using kv_block_t = detail::kv_block<page_size, geometry.head_size>;
    constexpr size_t expected_block_bytes =
        detail::KV_BLOCK_PLANES_2 * page_size * geometry.head_size * sizeof(bf16);
    static_assert(sizeof(kv_block_t) == expected_block_bytes);
    static_assert(alignof(kv_block_t) == storage_alignment);
    static_assert(std::is_trivially_default_constructible_v<kv_block_t> &&
                      std::is_trivially_copyable_v<kv_block_t> &&
                      std::is_trivially_destructible_v<kv_block_t>,
        "The DMA allocation creates KV blocks; see Note [KV block lifetime]");
    TRON_ASSERT_LT(pg, n_pages);
    TRON_ASSERT_LT(kv_head, geometry.n_kv_heads);
    if (offset.i < logical_slot_count()) {
      TRON_ASSERT(slot_matches<geometry>(kv_slot_id(offset.i)),
          "KV geometry does not match slot {}", offset.i);
    } else {
      TRON_ASSERT(has_eagle_storage() && offset == eagle_storage_offset(),
          "Invalid physical KV storage offset {}", offset.i);
      TRON_ASSERT(geometry == layout_t::primary_geometry,
          "EAGLE geometry must match cache slot zero");
    }
    auto const storage = slot_page(offset, pg);
    TRON_ASSERT(storage.base != nullptr, "Access to missing KV slot {}", offset.i);
    auto* blocks = std::launder(reinterpret_cast<kv_block_t*>(storage.base));
    return blocks[kv_head * storage.pages + storage.page];
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto const& kv_block_at_storage(
      kv_storage_offset offset, size_t kv_head, size_t pg) const noexcept {
    return const_cast<book*>(this)->template kv_block_at_storage<geometry>(
        offset, kv_head, pg);
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto& kv_block(kv_slot_id slot, size_t kv_head, size_t pg) noexcept {
    if constexpr (layout_t::uniform_geometry) {
      static_assert(geometry == layout_t::primary_geometry);
      return kv_block(slot, kv_head, pg);
    } else {
      TRON_ASSERT_LT(slot.i, logical_slot_count());
      TRON_ASSERT(
          slot_matches<geometry>(slot), "KV geometry does not match slot {}", slot.i);
      return kv_block_at_storage<geometry>(kv_storage_offset(slot.i), kv_head, pg);
    }
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto const& kv_block(kv_slot_id slot, size_t kv_head, size_t pg) const noexcept {
    return const_cast<book*>(this)->template kv_block<geometry>(slot, kv_head, pg);
  }

  template <kv_geometry geometry, typename Distribution, typename Gen>
  void fill_storage_slot(
      kv_storage_offset offset, Distribution& distribution, Gen& gen) noexcept {
    for (size_t kv_head = 0; kv_head < geometry.n_kv_heads; ++kv_head)
      for (size_t pg = 0; pg < n_pages; ++pg) {
        auto& block = kv_block_at_storage<geometry>(offset, kv_head, pg);
        if constexpr (k_vnni::layout_on<geometry.head_size>) {
          bf16* k = detail::k_vnni_access::plane(block.k.as_view());
          for (size_t i = 0; i < page_size * geometry.head_size; ++i) {
            k[i] = static_cast<bf16>(distribution(gen));
          }
        } else {
          for (auto& value : block.k) {
            value = static_cast<bf16>(distribution(gen));
          }
        }
        bf16* v = detail::v_vnni_access::plane(block.v.as_view());
        for (size_t i = 0; i < page_size * geometry.head_size; ++i)
          v[i] = static_cast<bf16>(distribution(gen));
      }
  }
};

// Cache topology whose logical K/V slots share one geometry and use `book`'s
// slot-major storage.
template <size_t n_slots,
    kv_geometry geometry,
    size_t x_bytes,
    auto slot_retentions = full_history_kv_slot_retentions<n_slots>()>
using uniform_kv_cache = book<n_slots,
    geometry.n_kv_heads,
    geometry.head_size,
    x_bytes,
    detail::
        kv_layout<uniform_kv_slot_specs(geometry, slot_retentions), true, geometry>>;

// A cache topology describes slot shapes only: a book owns K/V bytes, and
// recurrent-state ownership remains outside the K/V cache. Execution
// descriptors own operation-to-slot bindings.
template <typename T>
concept sequence_cache_topology =
    requires(size_t max_model_layers, bool support_eagle) {
      typename T::page_t;
      requires std::same_as<std::remove_cvref_t<decltype(T::kv_slot_specs)>,
          std::array<kv_slot_spec, T::n_slots>>;
      requires std::same_as<std::remove_cvref_t<decltype(T::recurrent_slot_specs)>,
          std::array<recurrent_slot_spec, T::n_recurrent_slots>>;
      requires valid_recurrent_slot_specs(T::recurrent_slot_specs);
      { T::logical_slot_count_for_layers(max_model_layers) } -> std::same_as<size_t>;
      {
        T::storage_slot_count_for_layers(max_model_layers, support_eagle)
      } -> std::same_as<size_t>;
    };

// Non-recursive book operations used by the token tree and scheduler. Page
// operations remain checked at their typed call sites; requiring them here
// would recursively instantiate the model while its plugin is incomplete.
template <typename T>
concept sequence_cache_behavior = requires(T& cache,
    T const& const_cache,
    size_t n_pages,
    size_t storage_slot_count,
    bool support_eagle,
    kv_storage_offset offset) {
  requires std::constructible_from<T, size_t, size_t, bool>;
  {
    T::try_create(n_pages, storage_slot_count, support_eagle)
  } -> std::same_as<std::shared_ptr<T>>;
  {
    T::try_create_lazy(n_pages, storage_slot_count, support_eagle)
  } -> std::same_as<std::shared_ptr<T>>;
  { T::page_size } -> std::convertible_to<size_t>;
  { T::max_reclaimable_window_size() } -> std::same_as<size_t>;
  { cache.page_capacity() } -> std::same_as<size_t>;
  { cache.token_capacity() } -> std::same_as<size_t>;
  { cache.dma_size_bytes() } -> std::same_as<int64_t>;
  { cache.storage_slot_count() } -> std::same_as<size_t>;
  { cache.has_reclaimed_kv_storage() } -> std::same_as<bool>;
  { cache.reclaimable_kv_restore_attempt() } -> std::same_as<uint64_t>;
  { cache.reclaimable_kv_storage_bytes() } -> std::same_as<int64_t>;
  { cache.free_reclaimable_kv_storage() } -> std::same_as<int64_t>;
  { cache.reclaimable_chunk_count() } -> std::same_as<size_t>;
  { cache.reclaimable_chunk_needs_restore(size_t{}, uint64_t{}) } -> std::same_as<bool>;
  { cache.reclaimable_chunk_token_begin(size_t{}) } -> std::same_as<size_t>;
  { cache.reclaimable_chunk_token_end(size_t{}) } -> std::same_as<size_t>;
  { cache.free_reclaimable_kv_chunk(size_t{}) } -> std::same_as<int64_t>;
  { cache.token_range_has_storage(size_t{}, size_t{}) } -> std::same_as<bool>;
  {
    cache.reserve_token_range(size_t{}, size_t{})
  } -> std::same_as<std::optional<int64_t>>;
  {
    cache.restore_reclaimable_kv_storage(uint64_t{})
  } -> std::same_as<std::optional<int64_t>>;
  { cache.abort_reclaimable_kv_restore(uint64_t{}) } -> std::same_as<int64_t>;
  cache.finish_reclaimable_kv_restore(uint64_t{});
  { cache.size() } -> std::same_as<size_t>;
  { cache.page_of(size_t{}) } -> std::same_as<typename T::page_t*>;
  { const_cache.page_of(size_t{}) } -> std::same_as<typename T::page_t const*>;
  { cache.eagle_storage_offset() } -> std::same_as<kv_storage_offset>;
  cache.set_storage_view(offset);
  cache.reset_storage_view();
  cache.increment_tokens_used(size_t{});
  cache.decrement_tokens_used(size_t{});
  cache.append(const_cache);
};

template <typename T>
concept sequence_cache = sequence_cache_topology<T> && sequence_cache_behavior<T>;

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
struct alignas(64) page final {
  using layout_t = layout_policy_t;
  inline static const size_t page_size = 64;
  static_assert(page_size % chunk_size == 0);  // Must be compatible with bf16s.
  using page_mask_t = tron::page_mask_t;

  using book_t = book<n_layers, n_kv_heads, head_size, x_bytes, layout_t>;

  static_assert(n_layers == layout_t::n_slots);
  static_assert(layout_t::primary_geometry == kv_geometry{n_kv_heads, head_size});

  // Spiritually, only books should construct pages, but book
  // delegates the actual constructing to `std::vector`, which makes
  // keeping the constructor private annoying.
  explicit page(book_t& book) noexcept
  : book(book)
  , offset_bound(0) {}

  // Explicit move: std::atomic is not movable, so copy counter
  // values. Only called during vector construction (single-threaded).
  page(page&& other) noexcept
  : book(other.book)
  , lo(other.lo)
  , offset_bound(other.offset_bound) {
    for (size_t o = 0; o < page_size; ++o)
      for (size_t l = 0; l < layout_t::n_slots; ++l)
        kv_saves_[o][l].store(other.kv_saves_[o][l].load(std::memory_order_relaxed),
            std::memory_order_relaxed);
  }

  // How many kv entries are live (see Note [KV Token Lifetimes]) on
  // this page alone.  Count will typically be `page_size` for
  // internal nodes, but a leaf page may not have enough
  // tokens. Branching followed by deletion could also lead to an
  // internal node not all of whose tokens are live.
  // Note that `count()` is only accurate after `compute_forward_args`
  // has decided which tokens are live and filled in the underlying
  // data with `set_offset_bound()`.
  TRON(nodiscard, inline, pure)
  size_t count() const noexcept {
    return offset_bound;
  }

  // Mark the lower bound of the interval of Q tokens influenced by the
  // K token at the given offset in this page.
  // See Note [Attention Causality Mask Representation].
  TRON(inline)
  void set_lo(size_t offset, size_t lower_bound) noexcept {
    // Tokens are laid out preorder, so the lower bound is always
    // the token itself.  Ergo, every token's lower bound is deducible
    // from any of them.
    lo = lower_bound - offset;
  }

  TRON(inline)
  void set_offset_bound(size_t bound) noexcept {
    // Check that any token the client alleges to be live is also valid,
    // per Note [KV Token Lifetimes].
    TRON_ASSERT_LE(pageno() * page_size + bound, book.tok_ct);
    offset_bound = bound;
  }

  // Return the `token_id` of the token at the given offset in this page.
  TRON(inline)
  token_id at_offset(size_t offset) const {
    return token_id(lo + offset);
  }

  // Return the offset of a token within this page, clamped to [0, count()].
  TRON(inline)
  size_t offset_for(token_id tok) const noexcept {
    ptrdiff_t diff = tok - at_offset(0);
    if (diff <= 0) return 0;
    return std::min(count(), (size_t)diff);
  }

  // Does this page contain the given token?
  // This interprets the token as a KV token.
  TRON(inline)
  bool contains(token_id tok) const {
    return lo <= tok.i && tok.i < lo + count();
  }

  // Map back from `token_id` to an offset in this page.
  TRON(inline)
  int offset_in_page(token_id tok) const {
    return (int)tok.i - (int)lo;
  }

  // Debug helper summarizing what's on this page.
  void report_coverage(size_t ix) {
    spdlog::info("KV page {} with {} tokens starting at {}", ix, count(), lo);
  }

  // K data indexed by [token][head element]. For a VNNI slot use set_k_row /
  // get_k_row below (Note [K VNNI storage]).
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head) noexcept TRON(this_lifetimebound)
  requires(layout_t::uniform_geometry && !k_vnni::layout_on<head_size>) {
    return kv_block(slot, kv_head).k_view();
  }

  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
  requires(layout_t::uniform_geometry && !k_vnni::layout_on<head_size>) {
    return kv_block(slot, kv_head).k_view();
  }

  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             !k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head) noexcept TRON(this_lifetimebound)
  {
    return kv_block<geometry>(slot, kv_head).k_view();
  }

  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             !k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
  {
    return kv_block<geometry>(slot, kv_head).k_view();
  }

  // One token's K data.
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head, size_t i_page) noexcept
      TRON(this_lifetimebound)
  requires(layout_t::uniform_geometry && !k_vnni::layout_on<head_size>) {
    return k(slot, kv_head)[i_page];
  }

  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head, size_t i_page) const noexcept
      TRON(this_lifetimebound)
  requires(layout_t::uniform_geometry && !k_vnni::layout_on<head_size>) {
    return k(slot, kv_head)[i_page];
  }

  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             !k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head, size_t i_page) noexcept
      TRON(this_lifetimebound)
  {
    return k<geometry>(slot, kv_head)[i_page];
  }

  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             !k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  auto k(kv_slot_id slot, size_t kv_head, size_t i_page) const noexcept
      TRON(this_lifetimebound)
  {
    return k<geometry>(slot, kv_head)[i_page];
  }

  // The read-only K plane view for the score reader k_vnni::qk_group. Internal
  // cache writes take writable views from the block owner instead.
  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>() &&
             k_vnni::layout_on<geometry.head_size>)
  TRON(nodiscard, inline, pure)
  k_vnni_view<const bf16, page_size, geometry.head_size> k_packed(
      kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
  {
    return kv_block<geometry>(slot, kv_head).k.as_view();
  }

  // Store one token's K row in the slot's K layout. The row may be unaligned.
  template <kv_geometry geometry, bool Aligned, bool Dma>
    requires(book_t::template declares_geometry<geometry>())
  TRON(inline)
  void set_k_row(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      const_k_row_view<geometry.head_size, Aligned, Dma> row) noexcept {
    TRON_ASSERT_LT(i_page, page_size);
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      store_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
    } else {
      std::memcpy(kv_block<geometry>(slot, kv_head).k_at(i_page).data, row.data,
          geometry.head_size * sizeof(bf16));
    }
  }

  // Load one token's K row, the inverse of set_k_row. The row may be unaligned.
  template <kv_geometry geometry, bool Aligned, bool Dma>
    requires(book_t::template declares_geometry<geometry>())
  TRON(inline)
  void get_k_row(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      k_row_view<geometry.head_size, Aligned, Dma> row) const noexcept {
    TRON_ASSERT_LT(i_page, page_size);
    if constexpr (k_vnni::layout_on<geometry.head_size>) {
      load_row(kv_block<geometry>(slot, kv_head).k.as_view(), i_page, row);
    } else {
      std::memcpy(row.data, kv_block<geometry>(slot, kv_head).k_at(i_page).data,
          geometry.head_size * sizeof(bf16));
    }
  }

  template <bool Aligned, bool Dma>
  TRON(inline)
  void set_k_row(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      const_k_row_view<head_size, Aligned, Dma> row) noexcept
    requires(layout_t::uniform_geometry)
  {
    set_k_row<layout_t::primary_geometry>(slot, kv_head, i_page, row);
  }

  template <bool Aligned, bool Dma>
  TRON(inline)
  void get_k_row(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      k_row_view<head_size, Aligned, Dma> row) const noexcept
    requires(layout_t::uniform_geometry)
  {
    get_k_row<layout_t::primary_geometry>(slot, kv_head, i_page, row);
  }

  // The actual V data for a token in this page.
  // Packed V: the plane is a v_vnni_tensor (see Note [VNNI Packed V layout] in
  // h/tron/tensor/v_vnni.hpp), pair-interleaved for the SIMD dot products, so
  // it is not compatible with the general `view` machinery. V is therefore
  // written one aligned source row at a time (set_v -> append_v_row), read back
  // one aligned destination row at a time (get_v -> load_row), and handed to
  // layout-specific kernels as a read-only packed view (v_packed). The source
  // row holds bf16, fp16 or float; the destination row bf16 or float. The rows'
  // `aligned` flag is a precondition on the caller's buffer, not a promise the
  // wrapper makes.
  template <typename Source, bool Dma>
  TRON(inline)
  void set_v(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      const_v_row_view<Source, head_size, Dma> src)
    requires(layout_t::uniform_geometry && head_size % 32 == 0);

  template <typename Destination, bool Dma>
  TRON(inline)
  void get_v(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      v_row_view<Destination, head_size, Dma> dst) const noexcept
    requires(layout_t::uniform_geometry && head_size % 32 == 0);

  template <kv_geometry geometry, typename Source, bool Dma>
  TRON(inline)
  void set_v(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      const_v_row_view<Source, geometry.head_size, Dma> src)
    requires(
        book_t::template declares_geometry<geometry>() && geometry.head_size % 32 == 0);

  template <kv_geometry geometry, typename Destination, bool Dma>
  TRON(inline)
  void get_v(kv_slot_id slot,
      size_t kv_head,
      size_t i_page,
      v_row_view<Destination, geometry.head_size, Dma> dst) const noexcept
    requires(
        book_t::template declares_geometry<geometry>() && geometry.head_size % 32 == 0);

  // This page's packed V plane for one KV head of one slot, read-only: the
  // argument type of the layout-specific kernels (the AMX PV kernel reads it in
  // place as its B operand). Internal cache writes take writable views from the
  // block owner instead.
  template <kv_geometry geometry>
    requires(book_t::template declares_geometry<geometry>())
  TRON(nodiscard, inline, pure)
  v_vnni_view<const bf16, page_size, geometry.head_size> v_packed(
      kv_slot_id slot, size_t kv_head) const noexcept TRON(this_lifetimebound)
  {
    return kv_block<geometry>(slot, kv_head).v.as_view();
  }

  // The useful thing to do with V data in this page, namely compute a
  // weighted sum of it in SIMD.
  TRON(nodiscard, inline, pure)
  detail::scaled_v_expr<page_size, head_size> scaled_v(kv_slot_id slot,
      size_t kv_head,
      const tensor<page_size>& scales,
      tensor<head_size>& scratch) const noexcept TRON(this_lifetimebound)
  requires(layout_t::uniform_geometry);

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  detail::scaled_v_expr<page_size, geometry.head_size> scaled_v(kv_slot_id slot,
      size_t kv_head,
      const tensor<page_size>& scales,
      tensor<geometry.head_size>& scratch) const noexcept TRON(this_lifetimebound)
  requires(book_t::template declares_geometry<geometry>());

  // EAGLE-style speculation stores the validation model's final embedding
  // from past tokens alongside its KV page.
  template <typename T>
  T* x(size_t i_page) noexcept {
    TRON_ASSERT(book.has_eagle_storage(), "Cache has no EAGLE embedding data");
    return reinterpret_cast<T*>(
        book.x_data->get() + (pageno() * page_size + i_page) * x_bytes);
  }

  template <typename T>
  const T* x(size_t i_page) const noexcept {
    TRON_ASSERT(book.has_eagle_storage(), "Cache has no EAGLE embedding data");
    return reinterpret_cast<const T*>(
        book.x_data->get() + (pageno() * page_size + i_page) * x_bytes);
  }

  // ---------------------------------------------------------------------------
  // Per-token KV completion tracking for GOF dispatch.
  //
  // Indexed [offset][slot]. Atomic counter per entry: save_k and
  // save_v each increment by 1. Exactly one thread sees the count
  // reach 2 and fires gof_rodeo for that (offset, slot).
  // ---------------------------------------------------------------------------

  // Returns true if this was the completing save (count reached 2).
  bool mark_k_complete(kv_slot_id slot, size_t offset) noexcept {
    TRON_ASSERT_LT(slot.i, book.logical_slot_count());
    TRON_ASSERT_LT(offset, page_size);
    return kv_saves_[offset][slot.i].fetch_add(1, std::memory_order_acq_rel) == 1;
  }

  // Returns true if this was the completing save (count reached 2).
  bool mark_v_complete(kv_slot_id slot, size_t offset) noexcept {
    TRON_ASSERT_LT(slot.i, book.logical_slot_count());
    TRON_ASSERT_LT(offset, page_size);
    return kv_saves_[offset][slot.i].fetch_add(1, std::memory_order_acq_rel) == 1;
  }

  TRON(nodiscard, inline)
  bool is_kv_complete(kv_slot_id slot, size_t offset) const noexcept {
    TRON_ASSERT_LT(slot.i, book.logical_slot_count());
    TRON_ASSERT_LT(offset, page_size);
    return kv_saves_[offset][slot.i].load(std::memory_order_acquire) >= 2;
  }

  // Clear completion state for a single offset across all slots.
  // Called when a new token is assigned to this page offset.
  void clear_kv_complete_at(size_t offset) noexcept {
    TRON_ASSERT_LT(offset, page_size);
    for (size_t l = 0; l < book.logical_slot_count(); ++l)
      kv_saves_[offset][l].store(0, std::memory_order_relaxed);
  }

private:
  using kv_block_t = detail::kv_block<page_size, head_size>;
  friend struct book<n_layers, n_kv_heads, head_size, x_bytes, layout_t>;

  // Which book am I in?
  book_t& book;

  // Base token index for this page within the current forward() call.
  // The pre-order traversal lays out the tokens of a page consecutively
  // starting at `lo`.  Used by at_offset, offset_for, contains, etc.
  uint32_t lo;

  // The (exclusive, of course) bound on offsets from `lo` (in
  // KV-token space) of a live token.  Live tokens are ones that
  // participate in this forward pass, as opposed to ones whose data
  // is being cached for a potential future request.
  // See Note [KV Token Lifetimes].
  uint32_t offset_bound;

  // Per-token per-slot save counter. Indexed [offset][slot].
  // 0 = neither K nor V saved, 1 = one saved, 2 = both saved.
  std::array<std::array<std::atomic<uint8_t>, layout_t::n_slots>, page_size>
      kv_saves_{};

  // Which page am I in the book?
  TRON(nodiscard, inline, pure)
  size_t pageno() const noexcept {
    return this - book.pages.data();
  }

  TRON(nodiscard, inline, pure)
  kv_block_t& kv_block(kv_slot_id slot, size_t kv_head) noexcept
    requires(layout_t::uniform_geometry)
  {
    return book.kv_block(slot, kv_head, pageno());
  }

  TRON(nodiscard, inline, pure)
  const kv_block_t& kv_block(kv_slot_id slot, size_t kv_head) const noexcept
    requires(layout_t::uniform_geometry)
  {
    return book.kv_block(slot, kv_head, pageno());
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto& kv_block(kv_slot_id slot, size_t kv_head) noexcept {
    return book.template kv_block<geometry>(slot, kv_head, pageno());
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto const& kv_block(kv_slot_id slot, size_t kv_head) const noexcept {
    return book.template kv_block<geometry>(slot, kv_head, pageno());
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto& kv_block_at_storage(kv_storage_offset offset, size_t kv_head) noexcept {
    return book.template kv_block_at_storage<geometry>(offset, kv_head, pageno());
  }

  template <kv_geometry geometry>
  TRON(nodiscard, inline, pure)
  auto const& kv_block_at_storage(
      kv_storage_offset offset, size_t kv_head) const noexcept {
    return book.template kv_block_at_storage<geometry>(offset, kv_head, pageno());
  }

  // Copying has to keep the pair-interleaved layout as well: one packed token
  // copy per token (copy_token in h/tron/tensor/v_vnni.hpp).
  // Even-destination paths zero the odd partner instead of preserving it.
  // This is safe because append_v is only called via copy_from in append(),
  // where destinations are always fresh ranges (dst_begin = tok_ct).
  template <kv_geometry geometry>
  TRON(inline)
  void append_v(kv_storage_offset storage_offset,
      size_t kv_head,
      size_t dst_i_page,
      const page* src_page,
      size_t src_i_page) noexcept {
    copy_token(kv_block_at_storage<geometry>(storage_offset, kv_head).v.as_view(),
        dst_i_page,
        src_page->template kv_block_at_storage<geometry>(storage_offset, kv_head)
            .v.as_view(),
        src_i_page);
  }

  template <kv_geometry geometry>
  void copy_storage_slot(kv_storage_offset storage_offset,
      const page* src_page,
      size_t src_begin,
      size_t dst_begin,
      size_t count) noexcept {
    for (size_t kv_head = 0; kv_head < geometry.n_kv_heads; ++kv_head) {
      if constexpr (k_vnni::layout_on<geometry.head_size>) {
        // A token's column depends on its offset in the page. So only a whole page
        // copies as one block, and any other range goes token by token.
        auto const& src_block =
            src_page->template kv_block_at_storage<geometry>(storage_offset, kv_head);
        auto& dst_block = kv_block_at_storage<geometry>(storage_offset, kv_head);
        if (src_begin == 0 && dst_begin == 0 && count == page_size) {
          dst_block.k = src_block.k;
        } else {
          for (size_t i = 0; i < count; ++i) {
            copy_token(dst_block.k.as_view(), dst_begin + i, src_block.k.as_view(),
                src_begin + i);
          }
        }
      } else {
        // The .k data is contiguous, so we can simply memcpy each head.
        constexpr size_t k_size = geometry.head_size * sizeof(bf16);
        const bf16* src =
            src_page->template kv_block_at_storage<geometry>(storage_offset, kv_head)
                .k_at(src_begin)
                .data;
        bf16* dst =
            kv_block_at_storage<geometry>(storage_offset, kv_head).k_at(dst_begin).data;
        memcpy(dst, src, count * k_size);
      }
      // The .v data is interleaved in token pairs, so we copy individual tokens.
      for (size_t i = 0; i < count; ++i)
        append_v<geometry>(
            storage_offset, kv_head, dst_begin + i, src_page, src_begin + i);
    }
  }

  // Copies count-many tokens from src_page to this page, starting at the given offsets.
  void copy_from(
      const page* src_page, size_t src_begin, size_t dst_begin, size_t count) noexcept {
    TRON_ASSERT_LE(src_begin + count, page_size);
    TRON_ASSERT_LE(dst_begin + count, page_size);
    book.for_each_active_slot([&]<size_t slot, kv_geometry geometry>() {
      copy_storage_slot<geometry>(
          kv_storage_offset(slot), src_page, src_begin, dst_begin, count);
      for (size_t i = 0; i < count; ++i) {
        uint8_t const completion =
            src_page->kv_saves_[src_begin + i][slot].load(std::memory_order_acquire);
        kv_saves_[dst_begin + i][slot].store(completion, std::memory_order_release);
      }
    });
    if (book.has_eagle_storage())
      copy_storage_slot<layout_t::primary_geometry>(
          book.eagle_storage_offset(), src_page, src_begin, dst_begin, count);
    if constexpr (x_bytes) {
      if (book.has_eagle_storage() && src_page->book.has_eagle_storage()) {
        const uint8_t* src = src_page->x<uint8_t>(src_begin);
        uint8_t* dst = x<uint8_t>(dst_begin);
        memcpy(dst, src, count * x_bytes);
      }
    }
  }
};

namespace detail {
template <size_t page_size, size_t head_size>
  requires(head_size % chunk_size == 0)
struct scaled_v_expr final : expr<scaled_v_expr<page_size, head_size>, head_size> {
  const tensor<page_size>& scales;
  const bf16* const data;
  const size_t count;
  tensor<head_size>& scratch;

private:
  const __m512i hi_16_of_32;

  TRON(nodiscard, inline, pure)
  fp32x16 odd_part(bf16x32 x) const noexcept {
    return _mm512_castsi512_ps(_mm512_and_epi32(x, hi_16_of_32));
  }

  TRON(nodiscard, inline, pure)
  fp32x16 even_part(bf16x32 x) const noexcept {
    return _mm512_castsi512_ps(_mm512_slli_epi32(x, 16));
  }

  template <size_t chunk_offset>
  TRON(inline)
  void accumulate_16_chunks(size_t end) noexcept {
    static_assert(chunk_offset + 16 <= head_size / chunk_size);
    fp32s t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15;
    for (size_t i = 0; i < end; i += 2) {
      const bf16x32 scale = interleave_bf16_ps(scales[i], scales[i + 1]);
      const bf16* tile = data + i * head_size + 2 * chunk_size * chunk_offset;
      t0 = _mm512_dpbf16_ps(t0, _mm512_load_si512(tile + 2 * chunk_size * 0), scale);
      t1 = _mm512_dpbf16_ps(t1, _mm512_load_si512(tile + 2 * chunk_size * 1), scale);
      t2 = _mm512_dpbf16_ps(t2, _mm512_load_si512(tile + 2 * chunk_size * 2), scale);
      t3 = _mm512_dpbf16_ps(t3, _mm512_load_si512(tile + 2 * chunk_size * 3), scale);
      t4 = _mm512_dpbf16_ps(t4, _mm512_load_si512(tile + 2 * chunk_size * 4), scale);
      t5 = _mm512_dpbf16_ps(t5, _mm512_load_si512(tile + 2 * chunk_size * 5), scale);
      t6 = _mm512_dpbf16_ps(t6, _mm512_load_si512(tile + 2 * chunk_size * 6), scale);
      t7 = _mm512_dpbf16_ps(t7, _mm512_load_si512(tile + 2 * chunk_size * 7), scale);
      t8 = _mm512_dpbf16_ps(t8, _mm512_load_si512(tile + 2 * chunk_size * 8), scale);
      t9 = _mm512_dpbf16_ps(t9, _mm512_load_si512(tile + 2 * chunk_size * 9), scale);
      t10 = _mm512_dpbf16_ps(t10, _mm512_load_si512(tile + 2 * chunk_size * 10), scale);
      t11 = _mm512_dpbf16_ps(t11, _mm512_load_si512(tile + 2 * chunk_size * 11), scale);
      t12 = _mm512_dpbf16_ps(t12, _mm512_load_si512(tile + 2 * chunk_size * 12), scale);
      t13 = _mm512_dpbf16_ps(t13, _mm512_load_si512(tile + 2 * chunk_size * 13), scale);
      t14 = _mm512_dpbf16_ps(t14, _mm512_load_si512(tile + 2 * chunk_size * 14), scale);
      t15 = _mm512_dpbf16_ps(t15, _mm512_load_si512(tile + 2 * chunk_size * 15), scale);
    }
    scratch.store_chunk(chunk_offset + 0, t0);
    scratch.store_chunk(chunk_offset + 1, t1);
    scratch.store_chunk(chunk_offset + 2, t2);
    scratch.store_chunk(chunk_offset + 3, t3);
    scratch.store_chunk(chunk_offset + 4, t4);
    scratch.store_chunk(chunk_offset + 5, t5);
    scratch.store_chunk(chunk_offset + 6, t6);
    scratch.store_chunk(chunk_offset + 7, t7);
    scratch.store_chunk(chunk_offset + 8, t8);
    scratch.store_chunk(chunk_offset + 9, t9);
    scratch.store_chunk(chunk_offset + 10, t10);
    scratch.store_chunk(chunk_offset + 11, t11);
    scratch.store_chunk(chunk_offset + 12, t12);
    scratch.store_chunk(chunk_offset + 13, t13);
    scratch.store_chunk(chunk_offset + 14, t14);
    scratch.store_chunk(chunk_offset + 15, t15);
  }

public:
  // Note [Zero-Initialized V Slots]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~
  // V data is stored as interleaved bf16 pairs (see Note [VNNI Packed V layout] in
  // h/tron/tensor/v_vnni.hpp): pair p holds tokens (2p, 2p+1). When count is
  // odd, the loop below rounds up to process the padding slot.
  // IEEE 754: NaN * 0.0 = NaN, so any NaN in the padding slot propagates
  // through _mm512_dpbf16_ps despite a zero scale.
  //
  // Invariant: every even-token cache append clears the odd partner:
  //   - set_v -> append_v_row (h/tron/tensor/v_vnni.hpp): the even path writes
  //     zeros into the odd half of every lane without reading the destination.
  //   - append_v -> copy_token (same header): even-destination paths zero the
  //     odd partner.
  // A packed view has no element write (v_vnni_view::at is read-only). No V
  // write marks a token complete: the model calls page::mark_v_complete after
  // set_v.
  // When count is odd, count-1 is even, so its write zeroes slot count.
  //
  // The plane arrives as its typed view. This weighted sum is the one
  // cache-side kernel that takes the plane address (through v_vnni_access,
  // Note [VNNI Packed V layout]). Its dot-product loop reads pair rows directly.
  // Page methods, book::append and tests go through the typed operations
  // instead. book::fill_random is the one documented exception: it fills a
  // whole kv_block without interpreting coordinates (Note [VNNI Packed V layout]).
  scaled_v_expr(const tensor<page_size>& scales,
      v_vnni_view<const bf16, page_size, head_size> v_page,
      const size_t count,
      tensor<head_size>& scratch) noexcept
    requires(head_size == 64 || head_size == 128 || head_size == 256 ||
                head_size == 512)
  : expr<scaled_v_expr, head_size>()
  , scales(scales)
  , data(v_vnni_access::plane(v_page))
  , count(count)
  , scratch(scratch)
  , hi_16_of_32(_mm512_set1_epi32(0xffff0000)) {
    const size_t end = (count + 1) / 2 * 2;  // Round up to even to operate on pairs.
    if constexpr (head_size == 64) {
      // Constructor zero-initializes with *_setzero_ps which is cheaper than writing `=
      // 0` to trigger *_set1_ps.
      fp32s t0, t1, t2, t3;
      for (size_t i = 0; i < end; i += 2) {
        const bf16x32 scale = interleave_bf16_ps(scales[i], scales[i + 1]);
        const bf16* tile = data + i * head_size;
        t0 = _mm512_dpbf16_ps(t0, _mm512_load_si512(tile + 2 * chunk_size * 0), scale);
        t1 = _mm512_dpbf16_ps(t1, _mm512_load_si512(tile + 2 * chunk_size * 1), scale);
        t2 = _mm512_dpbf16_ps(t2, _mm512_load_si512(tile + 2 * chunk_size * 2), scale);
        t3 = _mm512_dpbf16_ps(t3, _mm512_load_si512(tile + 2 * chunk_size * 3), scale);
      }
      scratch.store_chunk(0, t0);
      scratch.store_chunk(1, t1);
      scratch.store_chunk(2, t2);
      scratch.store_chunk(3, t3);
    } else if constexpr (head_size == 128) {
      fp32s t0, t1, t2, t3, t4, t5, t6, t7;
      for (size_t i = 0; i < end; i += 2) {
        const bf16x32 scale = interleave_bf16_ps(scales[i], scales[i + 1]);
        const bf16* tile = data + i * head_size;
        t0 = _mm512_dpbf16_ps(t0, _mm512_load_si512(tile + 2 * chunk_size * 0), scale);
        t1 = _mm512_dpbf16_ps(t1, _mm512_load_si512(tile + 2 * chunk_size * 1), scale);
        t2 = _mm512_dpbf16_ps(t2, _mm512_load_si512(tile + 2 * chunk_size * 2), scale);
        t3 = _mm512_dpbf16_ps(t3, _mm512_load_si512(tile + 2 * chunk_size * 3), scale);
        t4 = _mm512_dpbf16_ps(t4, _mm512_load_si512(tile + 2 * chunk_size * 4), scale);
        t5 = _mm512_dpbf16_ps(t5, _mm512_load_si512(tile + 2 * chunk_size * 5), scale);
        t6 = _mm512_dpbf16_ps(t6, _mm512_load_si512(tile + 2 * chunk_size * 6), scale);
        t7 = _mm512_dpbf16_ps(t7, _mm512_load_si512(tile + 2 * chunk_size * 7), scale);
      }
      scratch.store_chunk(0, t0);
      scratch.store_chunk(1, t1);
      scratch.store_chunk(2, t2);
      scratch.store_chunk(3, t3);
      scratch.store_chunk(4, t4);
      scratch.store_chunk(5, t5);
      scratch.store_chunk(6, t6);
      scratch.store_chunk(7, t7);
    } else if constexpr (head_size == 256) {
      accumulate_16_chunks<0>(end);
    } else if constexpr (head_size == 512) {
      // Thirty-two accumulators leave no ZMM registers for scales and tile
      // loads, so process two 256-wide halves and rescan the scales for each.
      accumulate_16_chunks<0>(end);
      accumulate_16_chunks<16>(end);
    } else {
      static_assert(false);  // ~And you may ask yourself, "Well, how did I get here?"~
    }
  }

  TRON(inline)
  bf16x32 interleave_bf16_ps(fp32x16 lo_fp32, fp32x16 hi_fp32) const noexcept {
    bf16x32 lo_bf16 = _mm512_srli_epi32(_mm512_castps_si512(lo_fp32), 16);
    bf16x32 hi_bf16 = _mm512_castps_si512(hi_fp32);
    return _mm512_ternarylogic_epi32(
        lo_bf16, hi_bf16, hi_16_of_32, _MM_TERNLOG_A | (_MM_TERNLOG_B & _MM_TERNLOG_C));
  }
  TRON(nodiscard, inline, pure)
  fp32s chunk(size_t i) const noexcept {
    return scratch.chunk(i);
  }
};

static const size_t kv_block_alignment = std::max<size_t>(64, chunk_alignment);

// This stores the {k,v} data contiguously to make prefetching easier.
// One kv_block is the KV cache for one KV head in one KV slot.
template <size_t page_size, size_t head_size>
struct alignas(kv_block_alignment) kv_block {
  // Native K: letting p index the token within a page and i index into
  // head_size, k is indexed as [p * head_size + i], one row of head_size bf16
  // values per token. Packed K: see Note [K VNNI storage].
  using native_k_storage = bf16[page_size * head_size];
  using k_storage = std::conditional_t<k_vnni::layout_on<head_size>,
      k_vnni_tensor<page_size, head_size>,
      native_k_storage>;
  static_assert(std::is_trivially_default_constructible_v<k_storage> &&
                    std::is_trivially_copyable_v<k_storage> &&
                    std::is_trivially_destructible_v<k_storage>,
      "the DMA allocation creates kv_blocks; see Note [KV block lifetime]");
  static_assert(sizeof(k_storage) == page_size * head_size * sizeof(bf16),
      "packed K holds the same bytes as native K");
  alignas(kv_block_alignment) k_storage k;
  // and v is the packed plane (the typed owner v_vnni_tensor): element (p, i)
  // sits at bf16 index (p/2) * 2 * head_size + 2 * i + p%2. Layout: see
  // Note [VNNI Packed V layout] in h/tron/tensor/v_vnni.hpp; pair invariant: see
  // Note [Zero-Initialized V Slots].
  using v_storage = v_vnni_tensor<page_size, head_size>;
  static_assert(std::is_trivially_default_constructible_v<v_storage> &&
                    std::is_trivially_copyable_v<v_storage> &&
                    std::is_trivially_destructible_v<v_storage>,
      "the DMA allocation creates kv_blocks; see Note [KV block lifetime]");
  alignas(kv_block_alignment) v_storage v;
  // This ensures scaled_v_expr linearly scans through v data, easing the job
  // of the hardware prefetcher.
  static_assert(sizeof(k) == sizeof(v));

  // Native K only: a packed plane has no contiguous rows.
  TRON(nodiscard, inline, pure)
  auto k_view() noexcept TRON(this_lifetimebound)
  requires(!k_vnni::layout_on<head_size>) {
    return view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>{k};
  }

  TRON(nodiscard, inline, pure)
  auto k_view() const noexcept TRON(this_lifetimebound)
  requires(!k_vnni::layout_on<head_size>) {
    return const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
        seq<page_size, head_size>>{k};
  }

  TRON(nodiscard, inline, pure)
  auto k_at(size_t i_page) noexcept TRON(this_lifetimebound)
  requires(!k_vnni::layout_on<head_size>) { return k_view()[i_page]; }

  TRON(nodiscard, inline, pure)
  auto k_at(size_t i_page) const noexcept TRON(this_lifetimebound)
  requires(!k_vnni::layout_on<head_size>) { return k_view()[i_page]; }
};

}  // namespace detail

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
template <kv_geometry geometry>
TRON(nodiscard, inline, pure)
auto page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::scaled_v(
    kv_slot_id slot,
    size_t kv_head,
    const tensor<page_size>& scales,
    tensor<geometry.head_size>& scratch) const noexcept
    -> detail::scaled_v_expr<page_size, geometry.head_size>
  requires(book_t::template declares_geometry<geometry>())
{
  return detail::scaled_v_expr<page_size, geometry.head_size>(
      scales, kv_block<geometry>(slot, kv_head).v.as_view(), count(), scratch);
}

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
TRON(nodiscard, inline, pure)
auto page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::scaled_v(
    kv_slot_id slot,
    size_t kv_head,
    const tensor<page_size>& scales,
    tensor<head_size>& scratch) const noexcept
    -> detail::scaled_v_expr<page_size, head_size>
  requires(layout_t::uniform_geometry)
{
  return scaled_v<layout_t::primary_geometry>(slot, kv_head, scales, scratch);
}

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
template <kv_geometry geometry, typename Source, bool Dma>
TRON(inline)
void page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::set_v(
    kv_slot_id slot,
    size_t kv_head,
    size_t i_page,
    const_v_row_view<Source, geometry.head_size, Dma> src)
  requires(
      book_t::template declares_geometry<geometry>() && geometry.head_size % 32 == 0)
{
  append_v_row(kv_block<geometry>(slot, kv_head).v.as_view(), i_page, src);
}

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
template <kv_geometry geometry, typename Destination, bool Dma>
TRON(inline)
void page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::get_v(
    kv_slot_id slot,
    size_t kv_head,
    size_t i_page,
    v_row_view<Destination, geometry.head_size, Dma> dst) const noexcept
  requires(
      book_t::template declares_geometry<geometry>() && geometry.head_size % 32 == 0)
{
  load_row(kv_block<geometry>(slot, kv_head).v.as_view(), i_page, dst);
}

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
template <typename Source, bool Dma>
TRON(inline)
void page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::set_v(
    kv_slot_id slot,
    size_t kv_head,
    size_t i_page,
    const_v_row_view<Source, head_size, Dma> src)
  requires(layout_t::uniform_geometry && head_size % 32 == 0)
{
  set_v<layout_t::primary_geometry>(slot, kv_head, i_page, src);
}

template <size_t n_layers,
    size_t n_kv_heads,
    size_t head_size,
    size_t x_bytes,
    typename layout_policy_t>
template <typename Destination, bool Dma>
TRON(inline)
void page<n_layers, n_kv_heads, head_size, x_bytes, layout_policy_t>::get_v(
    kv_slot_id slot,
    size_t kv_head,
    size_t i_page,
    v_row_view<Destination, head_size, Dma> dst) const noexcept
  requires(layout_t::uniform_geometry && head_size % 32 == 0)
{
  get_v<layout_t::primary_geometry>(slot, kv_head, i_page, dst);
}

}  // namespace tron
