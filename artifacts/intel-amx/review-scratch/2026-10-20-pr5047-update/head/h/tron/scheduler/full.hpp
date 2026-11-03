#pragma once

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <limits>
#include <list>
#include <memory>
#include <mutex>
#include <optional>
#include <span>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include <spdlog/spdlog.h>

#include "common/indexed.hpp"
#include "common/perfetto.hpp"
#include "common/trace_passes.hpp"
#include "common/util.hpp"
#include "libtron.hpp"
#include "pos/config.hpp"
#include "pos/lib.hpp"
#include "tron/generation/token_stream_monitor.hpp"
#include "tron/gof.hpp"
#include "tron/hardware/attention_slots.hpp"
#ifndef TRON_SCHEDULER_RUNTIME_ONLY
#include "tron/models/load.hpp"
#endif
#include "tron/models/common.hpp"
#include "tron/models/hw_attn_config.hpp"
#include "tron/models/ranged_mask.hpp"
#include "tron/scheduler/token_tree.hpp"
#include "tron/shard.hpp"

using namespace perfetto;

namespace tron {  // perfetto.hpp works only inside namespace tron

TRON(inline)
size_t defrag_books_depth() {
  static const size_t defrag_books_depth_ = [] {
    const char* env = std::getenv("TRON_DEFRAG_BOOKS_DEPTH");
    return env ? std::atoi(env) : 0;  // Disabled by default.
  }();
  return defrag_books_depth_;
}

TRON(inline)
size_t book_max_tokens() {
  static const size_t val = [] {
    const char* env = std::getenv("TRON_BOOK_MAX_TOKENS");
    return env ? size_t(std::max(1, std::atoi(env))) : size_t(1600);
  }();
  return val;
}

TRON(inline)
size_t book_initial_tokens() {
  static const size_t val = [] {
    const char* env = std::getenv("TRON_BOOK_INITIAL_TOKENS");
    return env ? size_t(std::max(1, std::atoi(env))) : size_t(1600);
  }();
  return val;
}

TRON(inline)
float book_growth_factor() {
  static const float val = [] {
    const char* env = std::getenv("TRON_BOOK_GROWTH_FACTOR");
    return env ? std::max(1.0f, std::stof(env)) : 2.0f;
  }();
  return val;
}

template <typename K, typename V>
class ordered_map {
  std::vector<std::tuple<K, V>> data;

public:
  V& operator[](const K& key) noexcept {
    auto it = find(key);
    if (it != data.cend()) {
      return std::get<1>(*it);
    }
    // If key not found, insert a new key-value pair and return the value
    data.push_back(std::make_tuple(key, V()));
    return std::get<1>(data.back());
  }

  // This insert assumes you know the key is not present
  // and skips the traversal.
  TRON(inline)
  void insert_new(const K& key, const V& value) noexcept {
    data.push_back(std::make_tuple(key, value));
  }

  void erase(const K& key) noexcept {
    auto it = find(key);
    if (it != data.end()) {
      data.erase(it);
    }
  }

  void clear() {
    data.clear();
  }

  std::vector<std::tuple<K, V>>::iterator find(const K& key) {
    return std::ranges::find_if(data.begin(), data.end(),
        [key](const auto& pr) { return std::get<0>(pr) == key; });
  }

  std::vector<std::tuple<K, V>>::const_iterator find(const K& key) const {
    return std::ranges::find_if(data.cbegin(), data.cend(),
        [key](const auto& pr) { return std::get<0>(pr) == key; });
  }

  bool contains(const K& key) const noexcept {
    return find(key) != data.cend();
  }

  size_t count(const K& key) const noexcept {
    size_t result = 0;
    for (const auto& kv : data) {
      if (std::get<0>(kv) == key) {
        ++result;
      }
    }
    return result;
  }

  TRON(inline)
  size_t size() const noexcept {
    return data.size();
  }

  TRON(inline)
  bool empty() const noexcept {
    return data.empty();
  }

  TRON(inline)
  auto begin() noexcept {
    return data.begin();
  }

  TRON(inline)
  auto begin() const noexcept {
    return data.begin();
  }

  TRON(inline)
  auto end() noexcept {
    return data.end();
  }

  TRON(inline)
  auto end() const noexcept {
    return data.end();
  }

  void swap_to_front(const K& key) noexcept {
    if (std::get<0>(data.front()) == key) return;
    for (size_t i = 1; i < data.size(); ++i) {
      if (std::get<0>(data[i]) == key) {
        std::swap(data[i], data[0]);
        return;
      }
    }
  }
};

// Operating metrics
// Couldn't use a struct nested inside `scheduler` due to reference cycle.
struct scheduler_metrics_t {
  std::atomic<int64_t> novel_tokens_seen;
  std::atomic<int64_t> tokens_reused;
  int64_t dma_bytes_reserved;  // Ignoring deallocations
  // Growth inside an already linked book is accounted separately from newly
  // anchored books. Weak anchors let a failed persistent/ephemeral append
  // discard provisional books while still accounting growth that survives in
  // the request's original prefix. Drained by token_cache_t after each add.
  std::vector<std::pair<std::weak_ptr<node_base>, int64_t>> pending_book_growth;
  int64_t tokens_processed;
  int64_t forward_passes;
  int64_t logits_delivered;
  std::atomic<int64_t> kv_reclamation_books_scanned{0};
  std::atomic<int64_t> kv_reclamation_books_released{0};
  std::atomic<int64_t> kv_reclamation_bytes_released{0};
  std::atomic<int64_t> kv_reclamation_books_restored{0};
  std::atomic<int64_t> kv_reclamation_bytes_restored{0};
  std::atomic<int64_t> kv_reclamation_restoration_requests{0};
  std::atomic<int64_t> kv_reclamation_replayed_tokens{0};

  uint64_t snapshot_time;
  int64_t snapshot_tokens_processed;
  int64_t snapshot_forward_passes;
  int64_t snapshot_logits_delivered;
  scheduler_metrics_t()
  : novel_tokens_seen(0)
  , tokens_reused(0)
  , dma_bytes_reserved(0)
  , tokens_processed(0)
  , forward_passes(0)
  , logits_delivered(0)
  , snapshot_time(0)
  , snapshot_tokens_processed(0)
  , snapshot_forward_passes(0)
  , snapshot_logits_delivered(0) {}

  void ensure_clock() noexcept {
    if (snapshot_time == 0) {
      snapshot_time = tron::hardware::system::rdtsc();
    }
  }

  void report_performance() noexcept {
    uint64_t current_time = tron::hardware::system::rdtsc();
    double ns_elapsed =
        tron::hardware::system::cycles_to_ns(current_time - snapshot_time);
    double seconds_elapsed = ns_elapsed / 1e9;
    static const float interval_sec = [] {
      const char* env = std::getenv("TRON_PERF_INTERVAL_SEC");
      return env ? std::stof(env) : 0.0f;
    }();
    if (interval_sec == 0 || seconds_elapsed < interval_sec) return;
    double tokens_per_second =
        (tokens_processed - snapshot_tokens_processed) / seconds_elapsed;
    spdlog::info("Completed {} passes with {} tokens for {} logits in {} s.  "
                 "Throughput {:.3f} tok/s.",
        forward_passes - snapshot_forward_passes,
        tokens_processed - snapshot_tokens_processed,
        logits_delivered - snapshot_logits_delivered, seconds_elapsed,
        tokens_per_second);
    snapshot_time = current_time;
    snapshot_tokens_processed = tokens_processed;
    snapshot_forward_passes = forward_passes;
    snapshot_logits_delivered = logits_delivered;
  }
};

// Base class for all the different templatings
struct node_base : std::enable_shared_from_this<node_base> {
  // Add an absolute token sequence to the tree
  //
  // Implementations handle:
  // - KV cache allocation and management
  // - Metrics tracking (tokens reused, DMA bytes allocated)
  // - Page boundary handling for KV allocation
  //
  // Parameters:
  //   _tokens: Array of tokens comprising the entire sequence
  //   ntokens: number of tokens in _tokens
  //   metrics: Scheduler metrics to update (tokens reused, DMA bytes, etc.)
  //
  // Returns: The final node after adding all tokens, or nullptr if a
  // cache-growth KV allocation could not be satisfied (the KV-cache OOM backstop,
  // memory_pressure_governor §8). The function is noexcept, so this null return
  // is the sole failure channel; callers must check it before dereferencing and
  // leave scheduler metrics unchanged for the failed add (the implementation
  // rolls back any speculative metric writes).
  //
  virtual std::shared_ptr<node_base> add_tokens(const ::token_t* _tokens,
      unsigned int ntokens,
      scheduler_metrics_t& metrics) noexcept = 0;
  virtual ~node_base() noexcept {};
  // Listeners persist from the time of an extend_request to the (possibly much
  // later) time that request is serviced. Element 0 of these arrays is used for
  // most models; element 1 is used for EAGLE models who share the node tree.
  std::array<std::vector<logits_buffer_t>, 2> listener_buffers;
  std::array<std::vector<std::function<void()>>, 2> listeners;

  // For the LRU cache
  uint64_t usage_time = 0;  // ephemeral by default
  int n_children = 0;
  token_batching_affinity_id live_group =
      token_batching_affinity_id{0};  // temporary used during compute_forward_args()
  bool live = false;                  // temporary used during compute_forward_args()
  // Am I currently in the eviction queue or not?
  // The cache needs to know because the eviction queue keeps a shared_ptr to me, whose
  // use_count the cache wants to inspect.
  bool in_evictable_queue = false;
  // Note [Tracking Node Users]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~
  // A node is `used` iff it is the root or some *pin* lies within its subtree.
  // `subtree_pins` counts the pins over this node's whole subtree, *inclusive of
  // this node itself* (so a directly pinned leaf has subtree_pins == 1, not 0),
  // and `used()` derives from it. Pins have three owners, each with balanced
  // acquisition and release:
  //   1. a client `seq_tip` directly holding this node (retained locations and
  //      in-flight tips), pinned via seq_tip::set_node / released on the worker;
  //   2. a pending listener attached to this node (in-flight work that a forward
  //      pass must still service), pinned at attach and released when it fires;
  //   3. a `reclaimed_kv_restore` receipt protecting its matched path through
  //      cache growth, released via token_cache_t::release_temporary_pin_locked
  //      when extend_request resolves the attempt or its failure.
  // Source 2 keeps `compute_forward_args` from skipping a subtree that still
  // owes a request a token; t_token_tree_stress guards this with its used-set
  // invariant (every uncancelled request stays serviceable).
  //
  // Because the count is inclusive, a pin sits *exactly at* a node (rather than
  // deeper) iff the node's subtree_pins exceeds the total over its children --
  // for a single-child node, iff its subtree_pins > child->subtree_pins. That is
  // how coalesce_if_unpinned_single_child distinguishes a directly pinned prefix
  // (a client still holds it, so it cannot merge away) from an idle pass-through
  // intermediate (every pin is in the child -> safe to merge). A pin names a
  // node position, not a token: it says nothing about the node's edge length.
  // See also Note [Deferred Coalescing Under Listener].
  //
  // Maintenance is via adjust_pins(), which walks to the root.
  int subtree_pins = 0;

  // Absolute positions belong to pin owners, not mutable node boundaries.
  // Appending or splitting an edge must not advance a retained handle's
  // position. Duplicate positions represent distinct pins. Splits leave these
  // direct pins on the original child; coalescing removes only intermediates
  // without direct pins. All accesses hold tree_lock.
  std::vector<tron::token_pos_ht> direct_pin_positions;
  std::array<std::vector<tron::token_pos_ht>, 2> listener_pin_positions;

  // An append can grow a book before its byte delta is published. Allocation
  // retry may evict a sibling and trigger compaction meanwhile. Keep this
  // anchor and its book identity stable until token_cache settles every
  // receipt; a weak receipt may expire only when the provisional book dies.
  // This is a compaction barrier, not a lifetime pin. Accesses hold tree_lock.
  size_t pending_book_growth = 0;

  // Tombstone support
  std::shared_ptr<node_base> tombstone_next = nullptr;  // Points to replacement node
  mutable std::mutex mtx;

  tron::token_pos_ht abs_ht;  // See Note [Token Position Types]
  uint32_t logical_kv_slots = 0;
  uint32_t storage_kv_slots = 0;
  bool support_eagle = false;

  node_base(tron::token_pos_ht abs_ht,
      uint32_t logical_kv_slots,
      uint32_t storage_kv_slots,
      bool support_eagle)
  : abs_ht(abs_ht)
  , logical_kv_slots(logical_kv_slots)
  , storage_kv_slots(storage_kv_slots)
  , support_eagle(support_eagle) {}

  virtual std::shared_ptr<node_base> parent() const noexcept = 0;
  virtual int64_t reserved_dma_bytes() const noexcept = 0;
  // Same value as reserved_dma_bytes(), but assumes the caller already holds
  // mtx. reserved_dma_bytes() takes mtx, so calling it from adjust_pins (which
  // already holds mtx) would self-deadlock the non-recursive mutex; this
  // no-lock variant lets a 0<->1 pin crossing read the anchor's book bytes in
  // place. See Note [Pinned/Opportunistic Split].
  virtual int64_t reserved_dma_bytes_locked() const noexcept = 0;
  virtual int used_children() noexcept = 0;
  virtual void defrag_books(size_t depth) noexcept = 0;
  // If this node has exactly one contiguous child and carries no pin or listener
  // of its own, merge it into that child. "No pin of its own" is read off the
  // counter (subtree_pins == child's); see Note [Tracking Node Users]. Called
  // from the release and listener-fire paths to flatten single-child
  // intermediates that the ~node() 2->1 trigger never sees (split-born, or made
  // idle only after a listener cleared).
  // Caller must hold the global tree_lock (the release and listener-fire paths
  // both hold it). See Note [Token Tree Mutation Lock].
  virtual void _coalesce_if_unpinned_single_child_locked() noexcept {}

  // Navigation helpers.
  std::shared_ptr<node_base> tree_parent() const {
    return parent();
  }
  tron::token_pos_ht tree_height() const {
    return abs_ht;
  }
  bool tree_is_root() const {
    return abs_ht == tron::token_pos_ht(0);
  }

  // GOF/shard interface — implemented in node<book>.
  virtual std::shared_ptr<hardware::shard> find_shard(uint32_t base_tok_ix) = 0;
  virtual void add_shard(std::shared_ptr<hardware::shard> s) = 0;
  // Drop the shard at `base_tok_ix`, if present. Only used to discard a shard
  // that holds no HBM so a fresh one can take its place; see Note [HBM
  // exhaustion degrades to software attention].
  virtual void remove_shard(uint32_t base_tok_ix) = 0;

  // Return the gals on this node's edge.
  virtual std::span<const std::unique_ptr<hardware::gal>> tree_edge_gals() const = 0;

  // See Note [Tracking Node Users]. `used` is derived, never stored.
  TRON(nodiscard, inline)
  bool used() const noexcept {
    return subtree_pins > 0 || is_root();
  }

  // Add `delta` pins at this node and propagate the subtree count up to the
  // root, locking one node at a time (releasing each before acquiring its
  // parent, so two node mutexes are never held at once).
  //
  // The public adjust_pins/pin/unpin acquire the global tree_lock first, so the
  // whole up-walk is serialized against the off-thread OOM-rescue eviction and
  // against the concurrent split/coalesce that transfers subtree_pins between
  // nodes. _adjust_pins_locked is the caller-holds body the worker / listener
  // mutation paths use (they already hold the lock). The per-node mtx still
  // guards the parent-pointer read on each hop; subtree_pins stays a plain int
  // because every writer now holds tree_lock. See Note [Token Tree Mutation
  // Lock] and Note [Tracking Node Users].
  void _adjust_pins_locked(int delta) noexcept {
    TRON_ASSERT(
        tron::tree_lock_held_by_this_thread(), "_adjust_pins_locked without tree_lock");
    std::shared_ptr<node_base> n = shared_from_this();
    while (n) {
      std::shared_ptr<node_base> parent;
      // Pinned/opportunistic split: detect a 0<->1 used() crossing of an
      // anchor and move its book bytes between the buckets. Captured under the
      // lock, applied after releasing it. See Note [Pinned/Opportunistic Split].
      int64_t crossed_bytes = 0;
      bool now_used = false, crossed = false;
      {
        std::lock_guard<std::mutex> lock(n->mtx);
        int before = n->subtree_pins;
        n->subtree_pins += delta;
        TRON_ASSERT(
            n->subtree_pins >= 0, "subtree_pins underflow at ht={}", n->abs_ht.i);
        bool was_used = before > 0 || n->is_root();
        now_used = n->subtree_pins > 0 || n->is_root();
        if (was_used != now_used) {
          crossed_bytes = n->reserved_dma_bytes_locked();  // 0 unless an anchor
          crossed = crossed_bytes != 0;
        }
        parent = n->parent_locked();
      }
      // Out of the node lock: the bridge may touch the token_cache() singleton.
      if (crossed) note_anchor_pin_transition(crossed_bytes, now_used);
      n = parent;
    }
  }

  // Public form: acquire the global tree_lock, then run the up-walk.
  void adjust_pins(int delta) noexcept {
    tron::tree_lock guard;
    _adjust_pins_locked(delta);
  }

  void pin() noexcept {
    adjust_pins(+1);
  }
  void unpin() noexcept {
    adjust_pins(-1);
  }
  // Caller-holds-tree_lock pin/unpin for the worker mutation paths (set_node via
  // canonicalize, extend_request, release). See Note [Token Tree Mutation Lock].
  void _pin_locked() noexcept {
    _adjust_pins_locked(+1);
  }
  void _unpin_locked() noexcept {
    _adjust_pins_locked(-1);
  }

  void _pin_at_locked(tron::token_pos_ht position) noexcept {
    TRON_ASSERT(
        tron::tree_lock_held_by_this_thread(), "_pin_at_locked without tree_lock");
    direct_pin_positions.push_back(position);
    _pin_locked();
  }

  // Remove only the position record. The caller immediately performs the
  // existing lifetime unpin under the same tree_lock, through release_node or
  // the listener batch, preserving their cache accounting and coalescing.
  void _forget_pin_position_locked(tron::token_pos_ht position) noexcept {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "_forget_pin_position_locked without tree_lock");
    auto const found =
        std::find(direct_pin_positions.begin(), direct_pin_positions.end(), position);
    TRON_ASSERT(found != direct_pin_positions.end(),
        "Releasing an unregistered pin position {}", position.i);
    direct_pin_positions.erase(found);
  }

  // Anonymous pins (including provisional KV restore receipts) retain the
  // conservative book-start bound. A precise minimum is safe only when every
  // direct pin has a recorded position; descendant pins are excluded by the
  // caller's subtree-count subtraction.
  std::optional<tron::token_pos_ht> earliest_direct_pin_position_locked(
      size_t direct_pin_count) const noexcept {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "earliest_direct_pin_position_locked without tree_lock");
    if (direct_pin_count == 0 || direct_pin_positions.size() != direct_pin_count)
      return std::nullopt;
    return *std::min_element(direct_pin_positions.begin(), direct_pin_positions.end());
  }

  bool is_root() const noexcept {
    return abs_ht == tron::token_pos_ht(0);
  }

protected:
  // Get parent while lock is held. Derived classes implement based on their storage.
  virtual std::shared_ptr<node_base> parent_locked() const noexcept = 0;
  // Count used children while lock is held on this node.
  virtual int used_children_locked() const noexcept = 0;

public:
  virtual size_t get_edge_token_count() const = 0;
  virtual std::vector<::token_t> get_edge_tokens() const = 0;
  virtual std::vector<std::shared_ptr<node_base>> get_children() const = 0;
  bool is_tombstoned_node() const {
    return tombstone_next != nullptr;
  }
  tron::token_pos_ht get_height() const {
    return abs_ht;
  }

  // Follow tombstone chain to get the valid node after coalescing
  std::shared_ptr<node_base> follow_tombstones() const {
    auto current = std::const_pointer_cast<node_base>(shared_from_this());
    while (true) {
      std::shared_ptr<node_base> next;
      {
        std::lock_guard<std::mutex> lock(current->mtx);
        if (!current->tombstone_next) return current;
        next = current->tombstone_next;
      }
      current = next;
    }
  }

  // Updates the usage time to now, making this node and its ancestors persistent.
  void touch() noexcept {
    std::lock_guard<std::mutex> lock(mtx);
    // No need to read the current value b/c it's guaranteed to be in the past.
    // However, if a user sends the same prompt twice, this may already be in
    // the `evictable` queue.  That's why it's a priority-increasable queue: to
    // handle the possibility that this assignment will change the priority of
    // an existing queued element, rather than merely setting the usage_time
    // of a node that hasn't been enqueued as evictable yet.
    usage_time = tron::hardware::system::rdtsc();
  }
};

// Follow tombstone chain and cast to specific node type
template <typename book>
std::shared_ptr<node<book>> follow_tombstones(std::shared_ptr<node_base> n) {
  if (!n) return nullptr;
  auto valid = n->follow_tombstones();
  return std::dynamic_pointer_cast<node<book>>(valid);
}

// Overload for already-typed input - static cast suffices since
// tombstone chains preserve type
template <typename book>
std::shared_ptr<node<book>> follow_tombstones(std::shared_ptr<node<book>> n) {
  if (!n) return nullptr;
  return std::static_pointer_cast<node<book>>(n->follow_tombstones());
}

// A node represents a prefix.  If the represented prefix
// is not empty, the node will have a back-pointer, and
// the last token, and a kv_cache book where that token
// appears.
template <typename book>
struct node : node_base {
  // Invariants of KV book arrangement that we are trying to maintain
  // - Every token lives in a unique entry in a unique kv book
  // - As nodes are added, they are placed in consecutive entries
  //   of the same kv book if possible
  // - Branching creates new kv books; a branch can start off an
  //   incomplete book if necessary
  // - Deletion after branching can leave a book under-utilized; that's ok
  // - All kv books (for this `full_scheduler` instance) are owned by
  //   the tree
  // - The valid tokens of a book are always the first tokens in the book (no gaps)
  // - The live tokens of a book are always laid out consecutively
  //   by the traversal (this should be true because each next live
  //   token should be the first child of the previous ones)
  // - We keep the book's token count correct as we add and remove nodes; we
  //   write `page.lo` and `page.hi` fields of the pages during the traversal.

  // Using multi-token edge from token_tree_v2 (empty for root node)
  tron::detail::parent_edge<book> parent_edge;
  // Elsewhere we rely on this being insertion-ordered
  ordered_map<::token_t, std::weak_ptr<node>> children;

private:
  std::shared_ptr<node> align_with_existing_node(std::shared_ptr<node> child,
      const ::token_t* tokens,
      size_t num_tokens,
      scheduler_metrics_t& metrics) {
    TRON_ASSERT(child, "Child node must not be null here");
    TRON_ASSERT(!child->is_tombstoned_node(), "Child node must not be tombstoned here");
    TRON_ASSERT(!child->parent_edge.is_empty(), "Child node must have a parent_edge");
    const auto& edge = child->parent_edge;

    // find how many tokens match
    const ::token_t* tokens_end = tokens + std::min(num_tokens, edge.token_count());
    const ::token_t* tok_ptr = tokens;
    for (auto ei = edge.token_entries.begin();
        tok_ptr != tokens_end && ei->token == *tok_ptr; ++tok_ptr, ++ei) {
    }
    size_t matching_tokens = static_cast<size_t>(tok_ptr - tokens);

    if (edge.token_count() == num_tokens && matching_tokens == num_tokens) {
      // Exact match found. The caller will pin this node when it becomes the
      // request's tip (seq_tip::set_node) or when its listener attaches; we do
      // not force `used` here. See Note [Tracking Node Users].
      metrics.tokens_reused += num_tokens;
      return child;
    }
    if (matching_tokens < edge.token_count()) {
      if (matching_tokens > 0) {
        // Need to split the edge
        metrics.tokens_reused += matching_tokens;

        // Split the edge at matching_tokens position
        auto split_result = split_edge(child, matching_tokens);

        // Now add remaining tokens from split point
        if (matching_tokens < num_tokens) {
          // Use add_tokens to properly handle chunking and page boundaries
          auto added = std::dynamic_pointer_cast<node>(split_result->add_tokens(
              tokens + matching_tokens, num_tokens - matching_tokens, metrics));
          // the divergent branch's KV book allocation may have failed
          // (null) AFTER split_edge already committed the split, leaving
          // split_result a single-child contiguous intermediate -- which
          // verify_tree Check 6 rejects and which would otherwise only flatten on
          // a later release. Heal it now with the same primitive the release path
          // uses; the tree_lock is held here, so it is lock-correct. No-ops unless
          // the merge is actually safe (unpinned, no listener, single child).
          if (!added) split_result->_coalesce_if_unpinned_single_child_locked();
          return added;
        }
        return split_result;
      }
    } else {
      // Because of the `min` calculation above, matching_tokens
      // cannot be greater than edge.token_count(), thus in this case
      // matching_tokens == edge.token_count()
      // Furthermore, due to prior 'if' conditions, it is guaranteed that
      // matching_tokens < num_tokens. The entire edge matches but we have more tokens
      // to add. Always count the matched tokens as reused
      metrics.tokens_reused += matching_tokens;

      return std::dynamic_pointer_cast<node>(child->add_tokens(
          tokens + matching_tokens, num_tokens - matching_tokens, metrics));
    }
    // This point should not be reached as all branches return. Add an assert or throw.
    TRON_ASSERT(false, "align_with_existing_node should always return");
    return nullptr;  // Should not be reached
  }

  std::shared_ptr<node> create_child_at_location(::token_t first_token,
      const ::token_t* tokens,
      size_t num_tokens,
      scheduler_metrics_t& metrics,
      std::shared_ptr<book> kv_book,
      size_t kv_first_entry_nr) {
    TRON_ASSERT(kv_book, "Cannot create a child without a KV book");
    TRON_ASSERT(!children.contains(first_token), "Child already exists");
    bool const leaf_becomes_internal = children.empty();
    kv_book->increment_tokens_used(num_tokens);
    metrics.novel_tokens_seen += num_tokens;

    // Clear KV completion bits for the new page offsets.
    for (size_t i = 0; i < num_tokens; ++i) {
      size_t entry = kv_first_entry_nr + i;
      kv_book->page_of(entry)->clear_kv_complete_at(entry % book::page_size);
    }

    // Create token_kv_pairs
    using token_info = tron::token_info<book>;
    std::vector<token_info> token_entries;
    for (size_t i = 0; i < num_tokens; ++i) {
      token_entries.emplace_back(token_info{tokens[i], false, false});
    }

    // Create edge and node with KV cache info set atomically
    tron::detail::parent_edge<book> new_edge(
        std::dynamic_pointer_cast<node>(this->shared_from_this()),
        std::move(token_entries), kv_book, kv_first_entry_nr);

    auto new_child = std::make_shared<node>(std::move(new_edge));

    // Partial shards belong to leaves. When a child turns this leaf into an
    // internal node, move crossing shards to the continuing child. Sibling
    // paths must allocate their own copy.
    if (leaf_becomes_internal && !parent_edge.is_empty()) {
      tron::detail::move_shards_crossing_boundary(
          parent_edge.shards, new_child->parent_edge.shards, abs_ht.i);
      parent_edge.edge_shard_cache_valid_ = false;
      new_child->parent_edge.edge_shard_cache_valid_ = false;
      for (auto const& sh : parent_edge.shards) {
        TRON_ASSERT(sh->base_tok_ix + tron::hardware::shard_tokens <= abs_ht.i,
            "internal edge owns partial shard: node height {} shard base {}", abs_ht.i,
            sh->base_tok_ix);
      }
    }

    // Calculate DMA bytes if this is a new book
    int64_t total_dma_bytes = 0;
    if (kv_first_entry_nr == 0) {
      total_dma_bytes = kv_book->dma_size_bytes();
    }
    metrics.dma_bytes_reserved += total_dma_bytes;

    children.insert_new(first_token, new_child);
    n_children++;

    return new_child;
  }

  std::shared_ptr<node> create_child(
      const ::token_t* tokens, size_t num_tokens, scheduler_metrics_t& metrics) {
    auto [kv_book, kv_first_entry_nr] = kv_location_for_tokens(num_tokens);
    // Cache-growth DMA allocation failed. See Note [KV cache-growth OOM backstop]
    // in rinzler/kv-oom-response.hpp. Nothing is committed yet; propagate the null
    // sentinel to token_cache's metric rollback.
    if (!kv_book) return nullptr;
    if (!reserve_book_tokens(kv_book, kv_first_entry_nr, num_tokens, metrics))
      return nullptr;
    return create_child_at_location(
        tokens[0], tokens, num_tokens, metrics, std::move(kv_book), kv_first_entry_nr);
  }

  std::shared_ptr<node> create_children(::token_t first_token,
      const ::token_t* tokens,
      size_t num_tokens,
      scheduler_metrics_t& metrics) {
    TRON_ASSERT_EQ(first_token, tokens[0]);
    size_t const max_pages = max_book_pages_for_dma_allocation();
    size_t const needed_pages = pages_for_tokens(num_tokens);
    if (max_pages == 0) return nullptr;
    if (needed_pages <= max_pages) return create_child(tokens, num_tokens, metrics);

    // Reserve the whole novel suffix before mutating the tree. See Note
    // [DMA-sized KV books]. Partition exactly the page capacity the unsplit
    // growth policy requested; do not reapply that policy to each segment.
    size_t const requested_pages = requested_num_pages(num_tokens);
    size_t book_count = requested_pages / max_pages +
                        static_cast<size_t>(requested_pages % max_pages != 0);
    // Every tree edge is non-empty. An extreme growth preference can request
    // more bounded books than this chunk has tokens, so defer only that
    // unrepresentable empty-book tail.
    book_count = std::min(book_count, num_tokens);
    size_t max_materialized_pages = std::numeric_limits<size_t>::max();
    if (book_count <= std::numeric_limits<size_t>::max() / max_pages)
      max_materialized_pages = book_count * max_pages;
    size_t const pages_to_reserve = std::min(requested_pages, max_materialized_pages);
    std::vector<std::shared_ptr<book>> books;
    books.reserve(book_count);
    size_t pages_reserved = 0;
    size_t tokens_reserved = 0;
    while (pages_reserved < pages_to_reserve) {
      size_t const pages = std::min(max_pages, pages_to_reserve - pages_reserved);
      TRON_ASSERT_GT(pages, 0);
      auto kv_book = try_create_book_with_retry(pages);
      if (!kv_book) return nullptr;
      size_t const books_after = book_count - books.size() - 1;
      size_t const segment_tokens = std::min(
          kv_book->token_capacity(), num_tokens - tokens_reserved - books_after);
      if (!reserve_book_tokens(kv_book, 0, segment_tokens, metrics)) return nullptr;
      tokens_reserved += segment_tokens;
      books.push_back(std::move(kv_book));
      pages_reserved += pages;
    }
    TRON_ASSERT_EQ(pages_reserved, pages_to_reserve);
    TRON_ASSERT_EQ(books.size(), book_count);
    TRON_ASSERT_EQ(tokens_reserved, num_tokens);

    auto current = std::dynamic_pointer_cast<node>(this->shared_from_this());
    size_t offset = 0;
    for (size_t i = 0; i < books.size(); ++i) {
      auto& kv_book = books[i];
      size_t const books_after = books.size() - i - 1;
      TRON_ASSERT_GT(num_tokens - offset, books_after);
      size_t const segment_tokens =
          std::min(kv_book->token_capacity(), num_tokens - offset - books_after);
      TRON_ASSERT_GT(segment_tokens, 0);
      current = current->create_child_at_location(tokens[offset], tokens + offset,
          segment_tokens, metrics, std::move(kv_book), /*kv_first_entry_nr=*/0);
      offset += segment_tokens;
    }
    TRON_ASSERT_EQ(offset, num_tokens);
    return current;
  }

  // Append tokens to this leaf's own parent_edge instead of spawning a
  // new child node. Caller must have already verified:
  //   - !parent_edge.is_empty()   (not the root)
  //   - children.empty()          (no branching below)
  //   - parent_edge.kv_book has room for `num_tokens` more entries
  //     contiguously past kv_last_entry_nr()
  //
  // Rationale: a pure linear decode would otherwise spawn one node per
  // generated token, turning the tree into a chain and making
  // compute_forward_args' per-node overhead dominate. With this path,
  // successive tokens land on the same edge as long as the sequence
  // doesn't branch.
  std::shared_ptr<node> extend_leaf_edge(
      const ::token_t* tokens, size_t num_tokens, scheduler_metrics_t& metrics) {
    TRON_ASSERT(!parent_edge.is_empty(), "extend_leaf_edge called on root");
    TRON_ASSERT(children.empty(), "extend_leaf_edge called on non-leaf");
    TRON_ASSERT(parent_edge.kv_book, "extend_leaf_edge: edge has no kv_book");
    auto& kv_book = parent_edge.kv_book;
    size_t first_new_index = parent_edge.kv_last_entry_nr() + 1;
    TRON_ASSERT(first_new_index + num_tokens <= kv_book->token_capacity(),
        "extend_leaf_edge: caller must verify KV capacity");
    if (!reserve_book_tokens(kv_book, first_new_index, num_tokens, metrics))
      return nullptr;

    // Clear KV completion bits for the freshly-allocated slots so a
    // prior use of this page's offsets (before eviction) doesn't leak
    // into this sequence.
    for (size_t i = 0; i < num_tokens; ++i) {
      size_t entry = first_new_index + i;
      kv_book->page_of(entry)->clear_kv_complete_at(entry % book::page_size);
    }

    // Append to the edge. Uses token_info default kv_ready/eagle_ready
    // = false so compute_forward_args schedules KV jobs for them.
    using token_info = tron::token_info<book>;
    parent_edge.token_entries.reserve(parent_edge.token_entries.size() + num_tokens);
    for (size_t i = 0; i < num_tokens; ++i) {
      parent_edge.token_entries.emplace_back(token_info{tokens[i], false, false});
    }
    kv_book->increment_tokens_used(num_tokens);

    // Edge content changed: force shard re-creation + drop per-edge
    // caches that indexed into the old token_entries.
    parent_edge.dirty = true;
    parent_edge.invalidate_append_cache();
    parent_edge.edge_shard_cache_valid_ = false;

    // Prefix grew.
    abs_ht = tron::token_pos_ht(abs_ht.i + num_tokens);
    metrics.novel_tokens_seen += num_tokens;

    return std::dynamic_pointer_cast<node>(this->shared_from_this());
  }

public:
  // root (parent_edge is default-constructed as empty)
  node(size_t logical_kv_slots, size_t storage_kv_slots, bool support_eagle) noexcept
  : node_base(tron::token_pos_ht(0),
        static_cast<uint32_t>(logical_kv_slots),
        static_cast<uint32_t>(storage_kv_slots),
        support_eagle) {}

  // child with multi-token edge
  // The parent_edge is required. Furthermore, the kv_book must already
  // be allocated.
  node(tron::detail::parent_edge<book> edge)
  : node_base(tron::token_pos_ht(edge.parent->abs_ht.i + edge.token_count()),
        edge.parent->logical_kv_slots,
        edge.parent->storage_kv_slots,
        edge.parent->support_eagle)
  , parent_edge(std::move(edge)) {
    TRON_ASSERT(!parent_edge.is_empty());
    TRON_ASSERT(parent_edge.parent);
    TRON_ASSERT(
        parent_edge.kv_book, "KV book must be initialized before node construction");
  }

  ~node() noexcept override {
    if (!parent_edge.is_empty()) {
      // Run the structural detach + coalesce under the global tree_lock. On the
      // eviction / release / worker paths the lock is already held -- reuse it,
      // so the body runs inline exactly as before (no use_count perturbation:
      // parent_edge.parent releases only when ~node returns, so evict_once's
      // is_evictable(parent) sees the true count). Only the rare off-worker
      // last-ref drop (app-pool prevent_dangle.reset, worker exit-drain
      // ~node_release_request) acquires here. The acquire is strictly OUTER to
      // parent_ptr->mtx below, preserving the mu_->node-mtx order; the dropping
      // thread holds no node mtx at that point. See Note [Token Tree Mutation
      // Lock].
      std::optional<tron::tree_lock> guard;
      if (!tron::tree_lock_held_by_this_thread()) guard.emplace();
      TRON_ASSERT(parent_edge.parent);
      // Use first token of edge as key in parent's children map
      ::token_t first_token = parent_edge.token_at(0);
      auto parent_ptr = parent_edge.parent.get();

      // Lock parent before modifying its children map to avoid data race
      // with concurrent readers (e.g., iterating children in other threads)
      std::shared_ptr<node> sibling;
      {
        std::lock_guard<std::mutex> parent_lock(parent_ptr->mtx);
        parent_ptr->children.erase(first_token);
        parent_ptr->n_children--;

        // Check if coalescing is possible while still holding lock
        if (parent_ptr->children.size() == 1) {
          auto it = parent_ptr->children.begin();
          sibling = std::get<1>(*it).lock();
        }
      }

      // Trigger coalescing outside lock if sibling was found
      if (sibling) {
        sibling->_defrag_books();
        tron::coalesce_nodes(parent_edge.parent, sibling);
      }

      // Verify edge has KV cache allocated
      TRON_ASSERT(parent_edge.kv_book != nullptr, "missing kv book for edge");
    }
  }

  // Note [DMA-sized KV books]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~
  // A KV book owns retained KV and EAGLE embeddings in whole-book buffers;
  // sliding KV uses independently reserved page-aligned chunks. Logical book
  // capacity is bounded by the total bytes in each retention group and the
  // embedding buffer. requested_num_pages computes capacity for the appended
  // token range. book_max_tokens caps policy-driven growth, but the append may
  // require more total capacity. create_children partitions that fixed total
  // across bounded books, applying the growth policy once for the whole append.
  //
  // The segmented path reserves every book before linking the first new node.
  // A DMA failure therefore leaves the token tree and scheduler metrics
  // untouched. One failed reservation may evict one opportunistic book and
  // retry once; that eviction is an independent, normally accounted cache
  // action. Alignment may split an existing edge before creating the divergent
  // suffix. If suffix reservation fails, it coalesces the single-child
  // intermediate.

  TRON(nodiscard)
  size_t max_book_pages_for_dma_allocation() const noexcept {
    return book::max_pages_for_dma_allocation(
        hardware::dma_max_allocation_bytes(), storage_kv_slots, support_eagle);
  }

  TRON(nodiscard)
  static size_t pages_for_tokens(size_t num_tokens) noexcept {
    return num_tokens / book::page_size +
           static_cast<size_t>(num_tokens % book::page_size != 0);
  }

  TRON(nodiscard)
  size_t preferred_num_pages() const {
    size_t bk_pages;
    size_t initial_pages =
        (book_initial_tokens() + book::page_size - 1) / book::page_size;
    // If this is the first book, make it big, assuming there will be a system prompt.
    if (parent_edge.is_empty()) bk_pages = initial_pages;
    // If we branched at the BOS token, make the new book big too, assuming there will
    // be a large user prompt.  LLMs produce useless junk if not thoroughly prompted.
    else if (parent_edge.parent->parent_edge.is_empty())
      bk_pages = initial_pages;
    // If the previous book was too short for the sequence, try harder to make it fit
    // (up to the configured limit).
    else if (children.size() == 0 && parent_edge.kv_book != nullptr) {
      bk_pages = size_t(
          std::ceil(parent_edge.kv_book->page_capacity() * book_growth_factor()));
    }
    // Otherwise we are in a branch, start short
    else
      bk_pages = 1;
    return bk_pages;
  }

  // The configured maximum clamps the growth preference, not the capacity
  // required by a caller's token chunk.
  TRON(nodiscard)
  size_t requested_num_pages(size_t num_tokens) const {
    size_t const configured_max =
        (book_max_tokens() + book::page_size - 1) / book::page_size;
    return std::max(
        std::min(configured_max, preferred_num_pages()), pages_for_tokens(num_tokens));
  }

  TRON(nodiscard)
  std::shared_ptr<book> try_create_book_with_retry(size_t pages) noexcept {
    auto result = book::try_create_lazy(pages, storage_kv_slots, support_eagle);
    if (result || reclaim_one_opportunistic_book_for_allocation_retry() <= 0)
      return result;
    return book::try_create_lazy(pages, storage_kv_slots, support_eagle);
  }

  bool reserve_book_tokens(std::shared_ptr<book> const& target,
      size_t begin,
      size_t count,
      scheduler_metrics_t& metrics) noexcept {
    std::shared_ptr<node> anchor;
    if (begin != 0) {
      anchor = std::dynamic_pointer_cast<node>(this->shared_from_this());
      while (anchor->parent_edge.kv_first_entry_nr != 0)
        anchor = anchor->parent_edge.parent;
      TRON_ASSERT(anchor->parent_edge.kv_book == target,
          "KV growth must be charged to its book anchor");
      // Retry eviction can defragment this book before any allocation succeeds.
      // Preserve its identity and the caller's already computed token offset.
      ++anchor->pending_book_growth;
    }
    finally reservation_barrier([&] {
      if (anchor) --anchor->pending_book_growth;
    });
    auto reserved = target->reserve_token_range(begin, begin + count);
    if (!reserved && reclaim_one_opportunistic_book_for_allocation_retry() > 0)
      reserved = target->reserve_token_range(begin, begin + count);
    if (anchor && (!reserved || *reserved != 0)) {
      // A failed retry may also have deferred compaction. Settle its zero-byte
      // receipt at the normal rollback boundary, after the caller stops using
      // the captured book location.
      metrics.pending_book_growth.emplace_back(anchor, reserved.value_or(0));
      ++anchor->pending_book_growth;
    }
    return reserved.has_value();
  }

  // Multi-token KV location allocation for new children. Returns the kv_book and
  // starting index for the tokens, or the {nullptr, 0} sentinel when the
  // cache-growth allocation fails; callers propagate the null book
  // up the add_tokens recursion.
  std::pair<std::shared_ptr<book>, size_t> kv_location_for_tokens(
      size_t num_tokens) noexcept {
    std::shared_ptr<book> current_book;
    size_t next_index = 0;

    // Check if we can continue from parent's book
    if (!parent_edge.is_empty() && parent_edge.kv_book != nullptr && children.empty()) {
      current_book = parent_edge.kv_book;
      next_index = parent_edge.kv_last_entry_nr() + 1;

      // Check capacity
      size_t remaining_capacity = current_book->token_capacity() - next_index;

      if (remaining_capacity < num_tokens) {
        // Need new book
        current_book = nullptr;
      }
    }

    // Allocate new book if needed
    if (!current_book) {
      size_t const max_pages = max_book_pages_for_dma_allocation();
      size_t const needed_pages = pages_for_tokens(num_tokens);
      if (needed_pages > max_pages) return {nullptr, 0};
      size_t const bk_pages = std::min(requested_num_pages(num_tokens), max_pages);
      current_book = try_create_book_with_retry(bk_pages);
      // Cache-growth DMA allocation failed. Return the {nullptr, 0}
      // failure sentinel WITHOUT advancing the token counter below.
      if (!current_book) return {nullptr, 0};
      next_index = 0;
    }

    return {current_book, next_index};
  }

  // Note [Split Child Pins]
  // ~~~~~~~~~~~~~~~~~~~~~~~~
  // Splitting child C's edge inserts an intermediate I between the parent and
  // C (parent -> I -> C). Under Note [Tracking Node Users] the intermediate must
  // start with subtree_pins == C->subtree_pins: I's only child is C, and I carries
  // no direct pins of its own, so its subtree pin count equals C's. The parent
  // chain above is unchanged (the same pins still sit below it).

  // Split an edge at the given position (alderaan-specific version)
  // This member function wraps the generic tron::split_edge_at and adds
  // alderaan-specific state management
  //
  // Parameters:
  //   child: The child node whose parent edge should be split
  //   first_part_len: the number of matching tokens common to both edges
  //      Must be in the range 1 to edge_length-1. AKA the number
  //      of tokens that will be in the first (intermediate) edge after the split.
  //
  // Returns: The intermediate node created by the split
  //
  // Invariants maintained:
  //   - All invariants from tron::split_edge_at (tree structure, tokens, KV cache)
  //   - Alderaan-specific state:
  //     * intermediate->subtree_pins = child->subtree_pins (see Note [Split Child
  //     Pins])
  //     * intermediate->abs_ht = parent_abs_ht + first_part_len
  //     * intermediate->logical_kv_slots = this->logical_kv_slots
  //     * intermediate->storage_kv_slots = this->storage_kv_slots
  //     * intermediate->support_eagle = this->support_eagle
  //     * intermediate->n_children = 1 (has the original child)
  //
  // Assumptions:
  //   - child has a parent edge (enforced by TRON_ASSERT)
  //   - first_part_len is valid: 0 < first_part_len < edge_length (enforced by
  //   TRON_ASSERT)
  //   - This is called in a context where splitting makes sense
  //     (typically during get_or_create_children when paths diverge)
  std::shared_ptr<node> split_edge(std::shared_ptr<node> child, size_t first_part_len) {
    TRON_ASSERT(
        !child->parent_edge.is_empty(), "Cannot split edge without parent edge");
    TRON_ASSERT(first_part_len > 0 && first_part_len < child->parent_edge.token_count(),
        "Invalid first_part_len: must be between 1 and edge_length-1");

    // Get parent height before modifying edge
    tron::token_pos_ht parent_abs_ht = child->parent_edge.parent->abs_ht;

    // Save gals and shards before split_edge_at overwrites
    // the edge. Lock child->mtx to synchronize, then release before
    // split_edge_at which also acquires child->mtx.
    auto& edge = child->parent_edge;
    decltype(edge.gals) saved_gals;
    decltype(edge.shards) saved_shards;
    {
      std::lock_guard<std::mutex> lock(child->mtx);
      saved_gals = std::move(edge.gals);
      saved_shards = std::move(edge.shards);
    }

    auto intermediate_base = tron::split_edge_at(edge, first_part_len);

    // Cast back to our node type
    auto intermediate = std::dynamic_pointer_cast<node>(intermediate_base);
    TRON_ASSERT(intermediate, "Failed to cast intermediate node");

    // See Note [Split Child Pins].
    intermediate->subtree_pins = child->subtree_pins;
    intermediate->abs_ht = tron::token_pos_ht(parent_abs_ht.i + first_part_len);
    intermediate->logical_kv_slots = logical_kv_slots;
    intermediate->storage_kv_slots = storage_kv_slots;
    intermediate->support_eagle = support_eagle;

    // Partition gals between intermediate and child edges by
    // comparing each gal's token_position to the split point.
    size_t split_abs = intermediate->abs_ht.i;
    for (auto& g : saved_gals) {
      if (g->token_position < split_abs) {
        intermediate->parent_edge.gals.push_back(std::move(g));
      } else {
        child->parent_edge.gals.push_back(std::move(g));
      }
    }
    // Fix for the out of order assert on repeated iterations.
    // If the shared portion of the prompt or the full prompt was >= 1024 tokens we
    // could see an ordering issue for shards on passes after the first.
    // This approach mirrors the gals partitioning logic to ensure consistent ordering
    // relative to the split point.
    // Partition shards between intermediate and child by coverage.
    // A shard entirely before split_abs goes to intermediate; anything that
    // reaches split_abs or beyond goes to child. Spanning shards go to child
    // only — the ascent logic propagates them to intermediate via children_shards.
    for (auto& s : saved_shards) {
      size_t shard_end = s->base_tok_ix + tron::hardware::shard_tokens;
      if (shard_end <= split_abs)
        intermediate->parent_edge.shards.push_back(std::move(s));
      else
        child->parent_edge.shards.push_back(std::move(s));
    }
    // n_children is set by tron::split_edge_at

    return intermediate;
  }

  // Get or create child with multiple tokens
  std::shared_ptr<node> get_or_create_children(
      const ::token_t* tokens, size_t num_tokens, scheduler_metrics_t& metrics) {
    TRON_ASSERT(num_tokens > 0, "Cannot create edge with zero tokens");

    // Check if child exists with first token
    ::token_t first_token = tokens[0];
    if (children.contains(first_token)) {
      if (auto child = children[first_token].lock()) {
        return align_with_existing_node(child, tokens, num_tokens, metrics);
      }
      // weak_ptr expired (child was evicted); erase stale entry before creating new
      children.erase(first_token);
      n_children--;
    }
    // Leaf-extension fast path: when no branching below us and there's
    // contiguous KV room, append to our own edge rather than spawning
    // a new child. Keeps linear decodes from fragmenting the tree.
    //
    // Gated on listeners being empty on BOTH slots (non-eagle and
    // eagle): a pending listener was registered for the current tip
    // position, so extending the edge would move the tip and fire the
    // listener with logits for a later token (wrong buffer).
    if (!parent_edge.is_empty() && children.empty() && parent_edge.kv_book != nullptr &&
        listeners[0].empty() && listeners[1].empty()) {
      size_t next_index = parent_edge.kv_last_entry_nr() + 1;
      if (next_index + num_tokens <= parent_edge.kv_book->token_capacity()) {
        return extend_leaf_edge(tokens, num_tokens, metrics);
      }
    }
    return create_children(first_token, tokens, num_tokens, metrics);
  }

  // Concrete implementation of node_base::add_tokens for alderaan nodes
  //
  // This implementation adds alderaan-specific behavior on top of basic tree
  // manipulation, including:
  // - KV cache allocation with page boundary awareness
  // - Metrics tracking (tokens reused, DMA bytes reserved)
  // - Height calculation and maintenance
  // - Support for EAGLE model optimizations
  // - Node usage tracking (marking nodes as used)
  //
  // The implementation reuses existing paths when possible (tracking reused
  // tokens in metrics) and handles edge splitting when paths diverge.
  //
  // See node_base::add_tokens for parameters and general behavior.
  // See tron::add_tokens for the underlying tree manipulation logic.
  std::shared_ptr<node_base> add_tokens(const ::token_t* _tokens,
      unsigned int ntokens,
      scheduler_metrics_t& metrics) noexcept override {
    TRACE_EVENT("scheduler", "add_tokens");
    auto n = std::dynamic_pointer_cast<node>(this->shared_from_this());
    return n->get_or_create_children(_tokens, ntokens, metrics);
  }

  TRON(nodiscard, inline, pure)
  std::shared_ptr<node_base> parent() const noexcept override {
    std::lock_guard<std::mutex> lock(mtx);
    return parent_edge.is_empty() ? nullptr : parent_edge.parent;
  }

  TRON(nodiscard, inline, pure)
  int64_t reserved_dma_bytes() const noexcept override {
    std::lock_guard<std::mutex> lock(mtx);
    return reserved_dma_bytes_locked();
  }

  // Caller must hold mtx. See node_base::reserved_dma_bytes_locked.
  TRON(nodiscard, inline, pure)
  int64_t reserved_dma_bytes_locked() const noexcept override {
    if (parent_edge.is_empty()) return 0;
    // We only need to check if this edge starts a new book
    if (parent_edge.kv_first_entry_nr == 0) {
      TRON_ASSERT(parent_edge.kv_book != nullptr);
      return parent_edge.kv_book->dma_size_bytes();
    }

    return 0;
  }

  TRON(nodiscard, inline, pure)
  int used_children() noexcept override final {
    std::lock_guard<std::mutex> lock(mtx);
    return used_children_locked();
  }

protected:
  std::shared_ptr<node_base> parent_locked() const noexcept override {
    return parent_edge.is_empty() ? nullptr : parent_edge.parent;
  }

  int used_children_locked() const noexcept override {
    int count = 0;
    for (const auto& [key, weak_child] : children) {
      if (auto child = weak_child.lock()) {
        count += child->used();
      }
    }
    return count;
  }

public:
  void defrag_books(size_t depth) noexcept override {
    TRON_ASSERT(
        tron::tree_lock_held_by_this_thread(), "defrag_books without tree_lock");
    std::lock_guard<std::mutex> lock(mtx);
    if (depth == 0) return;
    if (parent_edge.is_empty()) return;  // I have no source book.
    // My parent has no destination book.
    // Collect ancestors back to at most the given depth.
    if (parent_edge.parent->parent_edge.is_empty()) return;
    std::vector<node*> ancestry;
    ancestry.reserve(depth);
    ancestry.push_back(this);
    for (size_t i = 1; i < depth; ++i) {
      node* node = ancestry.back()->parent_edge.parent.get();
      // The parent has no destination book.
      if (node->parent_edge.parent->parent_edge.is_empty()) break;
      ancestry.push_back(node);
    }
    // Consolidate from oldest to youngest.
    for (node* n : ancestry | std::views::reverse)
      n->_defrag_books();
  }

  // See node_base::coalesce_if_unpinned_single_child and Note [Tracking Node Users].
  // "Directly pinned" is derivable from the pin counter alone: a single-child
  // node whose subtree_pins exceeds its child's has a pin of its own (a seq_tip at
  // exactly this prefix), so it cannot be coalesced until that client releases.
  // Equal counts mean every pin lies in the child's subtree -> safe to merge.
  void _coalesce_if_unpinned_single_child_locked() noexcept override {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "_coalesce_if_unpinned_single_child_locked without tree_lock");
    std::shared_ptr<node> child;
    {
      std::lock_guard<std::mutex> lock(mtx);
      if (parent_edge.is_empty()) return;  // root has nothing to merge into
      if (!listeners[0].empty() || !listeners[1].empty()) return;  // in-flight work
      if (children.size() != 1) return;
      child = std::get<1>(*children.begin()).lock();
      if (!child) return;
      if (subtree_pins != child->subtree_pins)
        return;  // subtree_pins > child => direct pin
    }
    // Mirror ~node(): give defrag a chance to make the child's book contiguous,
    // then coalesce. coalesce_nodes no-ops if the books still cannot merge.
    child->_defrag_books();
    tron::coalesce_nodes(
        std::dynamic_pointer_cast<node>(shared_from_this()), std::move(child));
  }

  size_t get_edge_token_count() const override {
    std::lock_guard<std::mutex> lock(mtx);
    return parent_edge.is_empty() ? 0 : parent_edge.token_count();
  }

  std::vector<::token_t> get_edge_tokens() const override {
    std::lock_guard<std::mutex> lock(mtx);
    std::vector<::token_t> res;
    if (!parent_edge.is_empty()) {
      res.reserve(parent_edge.token_count());
      for (size_t i = 0; i < parent_edge.token_count(); ++i) {
        res.push_back(parent_edge.token_at(i));
      }
    }
    return res;
  }

  std::vector<std::shared_ptr<node_base>> get_children() const override {
    // First, collect strong refs to children while holding lock.
    // Then follow tombstones without lock to avoid deadlock with adjust_pins'
    // up-walk (which locks child then parent, opposite of our
    // parent-then-child order).
    std::vector<std::shared_ptr<node<book>>> locked_children;
    {
      std::lock_guard<std::mutex> lock(mtx);
      for (const auto& [k, wc] : children) {
        if (auto c = wc.lock()) {
          locked_children.push_back(c);
        }
      }
    }
    // Now follow tombstones without holding our lock
    std::vector<std::shared_ptr<node_base>> res;
    for (auto& c : locked_children) {
      auto valid = tron::follow_tombstones<book>(c);
      if (valid) res.push_back(std::static_pointer_cast<node_base>(valid));
    }
    return res;
  }

  // Place a shard on this node's edge, keeping shards[] ascending by
  // base_tok_ix. That order is load-bearing, not cosmetic: descent pushes the
  // shard stack in shards[] order, and relative_hw_tok_ix walks a pass's shards
  // accumulating shard_tokens until it reaches the boundary token -- it breaks
  // on the first shard starting past that token, so a lower base appearing
  // after a higher one yields a wrong relative index for hardware attention.
  // Creation happens in ascending order, so this is a no-op for that path; it
  // matters when a degraded shard is rebuilt and re-added mid-list. See Note
  // [Retrying a degraded shard].
  void add_shard(std::shared_ptr<tron::hardware::shard> s) override {
    std::lock_guard<std::mutex> lock(mtx);
    TRON_ASSERT(!parent_edge.is_empty(), "Cannot add shard to root node");
    auto& v = parent_edge.shards;
    auto at = std::lower_bound(v.begin(), v.end(), s->base_tok_ix,
        [](auto const& lhs, uint32_t base) { return lhs->base_tok_ix < base; });
    v.insert(at, std::move(s));
    // Positions shift on insert, and edge_shards() pairs cached offsets with
    // shards[] positionally.
    parent_edge.invalidate_shard_cache();
  }

  // Drop the shard at `base_tok_ix`. The caller holds the last other reference
  // only after a forward pass has finished with it, so the shard destructs (and
  // releases any HBM) when this drops the edge's reference.
  void remove_shard(uint32_t base_tok_ix) override {
    std::lock_guard<std::mutex> lock(mtx);
    if (parent_edge.is_empty()) return;
    auto& v = parent_edge.shards;
    v.erase(std::remove_if(v.begin(), v.end(),
                [base_tok_ix](auto const& s) { return s->base_tok_ix == base_tok_ix; }),
        v.end());
    parent_edge.invalidate_shard_cache();
  }

  // Find a shard on this node's edge by base token index.
  std::shared_ptr<tron::hardware::shard> find_shard(uint32_t base_tok_ix) override {
    std::lock_guard<std::mutex> lock(mtx);
    if (parent_edge.is_empty()) return nullptr;
    for (auto& s : parent_edge.shards) {
      if (s->base_tok_ix == base_tok_ix) return s;
    }
    return nullptr;
  }

  std::span<const std::unique_ptr<tron::hardware::gal>>
  tree_edge_gals() const override {
    // No lock: the returned span aliases parent_edge.gals, so a lock
    // here would be released before the caller iterates and could not
    // protect against concurrent mutation anyway. The tree is owned
    // by the single scheduler work_queue thread (token_cache is not
    // thread-safe; see src/tron/scheduler/full.cpp), which also owns
    // every mutator of gals. If that invariant ever changes, switch
    // this back to a callback-while-locked pattern.
    return parent_edge.gals;
  }

private:
  void _defrag_books() noexcept {
    TRON_ASSERT(
        tron::tree_lock_held_by_this_thread(), "_defrag_books without tree_lock");
    // Check whether I anchor a book that could be contiguously spliced into my parent's
    // book.
    if (parent_edge.is_empty()) return;              // root node excluded
    if (parent_edge.kv_first_entry_nr != 0) return;  // I am not anchoring a book
    if (pending_book_growth != 0) return;
    std::shared_ptr<node<book>> parent = parent_edge.parent;
    if (parent->parent_edge.is_empty()) return;  // my parent is root, we're done
    std::shared_ptr<book> parent_book = parent->parent_edge.kv_book;
    if (parent_edge.kv_book->has_reclaimed_kv_storage() ||
        parent_book->has_reclaimed_kv_storage() ||
        parent_edge.kv_book->reclaimable_kv_restore_attempt() != 0 ||
        parent_book->reclaimable_kv_restore_attempt() != 0)
      return;
    size_t splice_ix = parent->parent_edge.kv_first_entry_nr +
                       parent->parent_edge.token_entries.size();
    if (splice_ix != parent_book->size()) return;  // Splicing would be invalid.
    size_t my_cost = parent_edge.kv_book->size();
    size_t parent_budget = parent_book->token_capacity() - splice_ix;
    if (my_cost > parent_budget) return;  // My book is too big for my parent's book.
    // Compaction must not turn an otherwise infallible relocation into a lazy
    // allocation or copy into a reclaimed sliding chunk.
    if (!parent_book->token_range_has_storage(splice_ix, splice_ix + my_cost)) return;
    // Move my book's data into my parent's book. Hold a reference
    // while relocating.
    std::shared_ptr<book> my_book = parent_edge.kv_book;
    TRON_ASSERT(my_book != parent_book);  // Since I am anchoring my book.
    // Releasing my_book removes its resident bytes from the live set. Capture
    // the current byte count and pinned/opportunistic category before _relocate
    // repoints the anchor. note_book_relocated removes this snapshot from arena
    // accounting; legacy accounting is unaffected.
    // See Note [Pinned/Opportunistic Split].
    bool was_used = used();
    int64_t freed_book_bytes = my_book->dma_size_bytes();
    parent_book->append(*my_book);
    // Relocate me and my descendents to point to the parent's book.
    // Pretend this child was inserted first.
    TRON_ASSERT(!parent_edge.token_entries.empty());
    parent->children.swap_to_front(parent_edge.token_entries.front().token);
    _relocate(my_book, parent_book, splice_ix);
    // my_book is about to be dropped. Every gal in this subtree that captured a
    // page from it must be rebuilt against parent_book first, or gof::populate
    // will dereference freed memory. Runs after _relocate so the walk sees the
    // final kv_book/kv_first_entry_nr. See Note [GOF Page Relocation].
    _repair_gals_in_subtree(my_book);
    note_book_relocated(freed_book_bytes, was_used);
  }

  // Note [GOF Page Relocation]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~
  // A gal's page_info captures a bare page* plus an offset into the book that
  // owns the page. defrag() splices a child book into its parent and drops the
  // child, and _relocate() then repoints every affected edge at the new book
  // and shifts kv_first_entry_nr. Both of those invalidate a gal's captures:
  // the page* is freed with the old book, and the offset names a different
  // token once the entries shift. The edge's own append cache is invalidated
  // for exactly this reason; the gals need the same treatment, except they must
  // be repaired rather than dropped because their GOFs hold staged
  // hwcacheblocks. _repair_gal_pages() recomputes each affected page_info
  // against the new book via gal::make_page_info, the same factory that built
  // it. Without this, gof::populate() dereferences freed memory.
  //
  // A gal's four tokens can straddle an edge boundary, so some of its
  // page_infos may point into an ancestor edge's book rather than this edge's.
  // Repair therefore resolves each token by walking up from this node, and only
  // touches page_infos whose owner is the book being moved.
  //
  // That straddling is also why repair cannot piggyback on _relocate's
  // recursion. _relocate descends only into children still on the old book, but
  // a gal referencing the moved book can live on a descendant edge that anchors
  // a *different* book -- e.g. a gal at token_position 1471 sits on the child
  // edge while three of its four tokens (1468-1470) belong to the parent edge
  // that just moved. Repair therefore walks the whole subtree under the book's
  // anchor, unconditionally, and runs after all relocation is finished so that
  // _resolve_page_for_abs observes final kv_book/kv_first_entry_nr values.

  // Resolve an absolute token position to its page, walking up from this node.
  bool _resolve_page_for_abs(size_t abs_pos,
      typename book::page_t*& pg,
      size_t& pg_offset,
      std::shared_ptr<book>& owner) const noexcept {
    for (const node<book>* path = this; path && !path->parent_edge.is_empty();
        path = path->parent_edge.parent.get()) {
      auto const& e = path->parent_edge;
      size_t base = e.parent->abs_ht.i;
      size_t end = path->abs_ht.i;
      if (abs_pos < base || abs_pos >= end) continue;
      if (!e.kv_book) return false;
      size_t kv_ix = e.kv_entry_nr(abs_pos - base);
      pg = e.kv_book->page_of(kv_ix);
      pg_offset = kv_ix % book::page_size;
      owner = e.kv_book;
      return pg != nullptr;
    }
    return false;
  }

  // Rebuild this edge's gal page_infos that referenced moved_book. Call after
  // kv_book and kv_first_entry_nr have been updated. See Note [GOF Page
  // Relocation].
  void _repair_gal_pages(const std::shared_ptr<book>& moved_book) noexcept {
    for (auto& g : parent_edge.gals) {
      if (!g || !g->make_page_info) continue;
      for (auto& pi : g->pages) {
        if (pi.owner_book.lock().get() != moved_book.get()) continue;
        typename book::page_t* pg = nullptr;
        size_t off = 0;
        std::shared_ptr<book> owner;
        if (!_resolve_page_for_abs(pi.position, pg, off, owner)) {
          spdlog::error("gal page repair: could not re-resolve token {} after book "
                        "relocation; its page_info is left stale",
              pi.position);
          continue;
        }
        g->make_page_info(
            pi, pi.position, pg, off, std::static_pointer_cast<void>(owner));
      }
    }
  }

  // Repair this node and every descendant, regardless of which book each edge
  // now anchors. See Note [GOF Page Relocation] for why the walk cannot be
  // limited to edges that were on moved_book.
  void _repair_gals_in_subtree(const std::shared_ptr<book>& moved_book) noexcept {
    if (!parent_edge.is_empty()) _repair_gal_pages(moved_book);
    for (auto& child_pair : children) {
      auto child = std::get<1>(child_pair).lock();
      if (child) child->_repair_gals_in_subtree(moved_book);
    }
  }

  void _relocate(std::shared_ptr<book>& old_book,
      std::shared_ptr<book>& new_book,
      size_t shift) noexcept {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(), "_relocate without tree_lock");
    parent_edge.kv_book = new_book;
    parent_edge.kv_first_entry_nr += shift;
    // Page pointers and page offsets change when the book shifts.
    parent_edge.invalidate_append_cache();
    for (auto& child_pair : children) {
      auto child = std::get<1>(child_pair).lock();
      if (child && !child->parent_edge.is_empty() &&
          child->parent_edge.kv_book == old_book)
        child->_relocate(old_book, new_book, shift);
    }
  }
};

enum class reclaimed_kv_restore_result {
  unchanged,
  prepared,
  failed,
};

// Move-only receipt for one provisional restore. Once preparation reaches a
// required arena, the receipt owns one temporary token-tree pin until
// extend_request resolves the attempt or its failure.
struct reclaimed_kv_restore final {
  reclaimed_kv_restore_result result = reclaimed_kv_restore_result::unchanged;
  std::shared_ptr<node_base> pinned_tip;
  uint64_t attempt = 0;
  size_t matched_begin = 0;
  size_t matched_end = 0;
  size_t initial_demand = 0;
  int64_t margin = 0;

  reclaimed_kv_restore() noexcept = default;
  reclaimed_kv_restore(reclaimed_kv_restore const&) = delete;
  reclaimed_kv_restore& operator=(reclaimed_kv_restore const&) = delete;
  reclaimed_kv_restore(reclaimed_kv_restore&& other) noexcept {
    *this = std::move(other);
  }
  reclaimed_kv_restore& operator=(reclaimed_kv_restore&& other) noexcept {
    TRON_ASSERT(!pinned_tip, "Overwriting an unresolved KV restore receipt");
    result = other.result;
    pinned_tip = std::move(other.pinned_tip);
    attempt = other.attempt;
    matched_begin = other.matched_begin;
    matched_end = other.matched_end;
    initial_demand = other.initial_demand;
    margin = other.margin;
    return *this;
  }
  ~reclaimed_kv_restore() noexcept {
    TRON_ASSERT(!pinned_tip, "Destroying an unresolved KV restore receipt");
  }
};

// The virtual method dispatch is over the model_t template parameter.
struct scheduler : ::tron::noncopyable<scheduler> {
  scheduler(bool is_eagle, bool is_speculator) noexcept
  : metrics{}
  , token_stream_monitor{std::make_shared<TokenStreamMonitor>()}
  , eagle_child(nullptr)
  , is_eagle(is_eagle)
  , is_speculator(is_speculator)
  , trace_passes(make_trace_pass_counter(is_speculator)) {}

  virtual ~scheduler() noexcept {
    if (trace_passes) set_application_tracing_enabled(false);
  };
  virtual std::shared_ptr<node_base> get_root() noexcept = 0;
  // Returns whether it's done, i.e., true if all requested tokens were processed
  virtual bool forward() noexcept = 0;
  virtual size_t vocab_size() const noexcept = 0;
  virtual void validate_kv_books() const = 0;
  // Restore preparation may reject one request on DMA exhaustion. A prepared
  // attempt remains private until add_tokens succeeds. Reclamation runs only
  // at worker safe points under pressure. Non-book schedulers keep no-op defaults.
  virtual reclaimed_kv_restore prepare_reclaimed_kv_restore(
      node_base*, std::span<::token_t const>, int64_t) noexcept {
    return {};
  }
  virtual void commit_reclaimed_kv_restore(reclaimed_kv_restore&) noexcept {}
  virtual void abort_reclaimed_kv_restore(reclaimed_kv_restore&) noexcept {}
  virtual void reclaim_out_of_window_kv() noexcept {}
  // Check the token-tree structural invariants from the root. Returns false and
  // fills *error_msg on the first violation. Reads the tree without locking, so
  // call only on the worker thread at a pass boundary (e.g. from
  // pre_forward_hook).
  virtual bool verify_tree(std::string* error_msg) const = 0;
  // Check that the set of `used` nodes is exactly the upward closure (to the
  // root) of the nodes pinned by `pinned` locations, plus the root itself.
  // Only meaningful at a quiescent point where `pinned` is the complete set of
  // live external holders -- during generation the scheduler holds in-flight
  // tips that are not in `pinned`. Reads the tree without locking; called on the
  // worker thread (e.g. from a work_barrier callback).
  virtual bool verify_used_set(
      std::vector<location_t> const& pinned, std::string* error_msg) const = 0;

  // Hook run on the worker thread by forward(), once per pass, just before
  // `state.forward`.  Useful for single-stepping through forward passes
  // e.g. in tests.
  std::function<void()> pre_forward_hook;

  // Note [Trace pass window boundary]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~
  // The capture window for pass N spans select_trace_pass(N) to
  // select_trace_pass(N+1): the gate flips only at selection points, never in
  // complete_trace_pass. Post-forward work (logits delivery, response events)
  // belongs to the pass that produced it, and the response-slice BEGIN/END
  // pairing in stream_generate relies on the gate holding steady between
  // selects. Two consequences: pre-select scheduler work for pass N+1
  // (compute_forward_args, HW-plan setup) is attributed to pass N's window,
  // and a no-work forward() returns before selection, leaving the gate
  // untouched. Window WIDTH is exact: a spec naming K passes captures exactly
  // K forward slices.
  void select_trace_pass() noexcept {
    if (trace_passes)
      set_application_tracing_enabled(trace_passes->next_pass_enabled());
  }

  void complete_trace_pass() noexcept {
    // Deliberately does not close the gate. See Note [Trace pass window boundary].
    if (trace_passes) trace_passes->complete_pass();
  }

  // Operating metrics
  using metrics_t = scheduler_metrics_t;
  metrics_t metrics;
  std::shared_ptr<TokenStreamMonitor> token_stream_monitor;
  // EAGLE schedulers come in (parent,child) pairs, where the parent is the
  // exact model and the child is the EAGLE draft model.
  std::shared_ptr<scheduler> eagle_child;
  const bool is_eagle;  // true for the EAGLE child
  // true for either EAGLE models or other small models used as speculators
  const bool is_speculator;
  std::optional<trace_pass_counter> trace_passes;
  // Per-session handle_id, set by extend_request from seq_tip.
  uint64_t active_handle_id = 0;
};

#ifndef TRON_SCHEDULER_RUNTIME_ONLY
// gof_job is defined in tron/gof.hpp.
using hardware::gof_job;

namespace detail {

TRON(nodiscard, inline, pure)
int64_t checked_kv_position(size_t position) noexcept {
  TRON_ASSERT_LE(position, static_cast<size_t>(std::numeric_limits<int64_t>::max()));
  return static_cast<int64_t>(position);
}

struct kv_restore_dependency_scan final {
  size_t window;
  int64_t margin;
  size_t nearest_demand;
  size_t predecessor_tokens_needed = 0;

  void include_demand(size_t position) noexcept {
    nearest_demand = std::min(nearest_demand, position);
  }

  bool arena_is_required(bool arena_missing, size_t book_path_end) const noexcept {
    if (!arena_missing || book_path_end == 0) return false;
    int64_t const demand_position = checked_kv_position(nearest_demand);
    int64_t const newest_token = checked_kv_position(book_path_end - 1);
    return predecessor_tokens_needed != 0 || demand_position - newest_token < margin;
  }

  void include_restored_book() noexcept {
    predecessor_tokens_needed = window;
  }

  bool needs_predecessor_tokens() const noexcept {
    return predecessor_tokens_needed != 0;
  }

  void include_resident_book(bool ready, size_t token_entries) noexcept {
    TRON_ASSERT(predecessor_tokens_needed != 0,
        "Resident KV book visited without a predecessor requirement");
    if (!ready) {
      predecessor_tokens_needed = window;
    } else if (token_entries >= predecessor_tokens_needed) {
      predecessor_tokens_needed = 0;
    } else {
      predecessor_tokens_needed -= token_entries;
    }
  }

  bool can_stop_before(
      size_t next_book_path_end, bool matched_range_remains) const noexcept {
    if (predecessor_tokens_needed != 0 || matched_range_remains) return false;
    TRON_ASSERT(next_book_path_end != 0, "KV restore walk reached an empty book");
    int64_t const next_newest = checked_kv_position(next_book_path_end) - 1;
    return checked_kv_position(nearest_demand) - next_newest >= margin;
  }
};

}  // namespace detail

template <typename model_t>
struct full_scheduler : scheduler {
  using cache_t = typename model_t::cache_t;
  using book = cache_t;
  using page = typename model_t::page;
  using state_t = typename model_t::state;
  using node_t = node<book>;

  // A reference to the model (which persists for the life of the process)
  std::shared_ptr<model_t> llm;
  size_t max_layers;
  const size_t active_reclaimable_window_size;
  // Persistently-allocated scratch space
  state_t state;

  static size_t resolve_max_layers(bool is_eagle, model_config const* cfg) noexcept {
    size_t resolved = is_eagle                ? 1
                      : cfg->max_layers == -1 ? model_t::n_layers
                                              : static_cast<size_t>(cfg->max_layers);
    // A model cannot run more layers than it has. cfg.max_layers only ever
    // *caps* the layer count (and defaults to model_t::n_layers); it must not
    // exceed it. Forcing it higher undersizes the per-layer KV structures that
    // are fixed at compile time by the plugin's n_layers (page::kv_saves_,
    // plugin.layers), which silently reads/writes out of bounds. See cache.hpp
    // ("Do not attempt to run a model with more layers than were loaded").
    TRON_ASSERT(resolved <= model_t::n_layers,
        "max_layers {} exceeds model n_layers {}", resolved, model_t::n_layers);
    return resolved;
  }

  full_scheduler(std::shared_ptr<model_t> const& llm,
      model_config* cfg,
      std::shared_ptr<node_base> shared_root = {}) noexcept
  : scheduler(
        /*is_eagle=*/shared_root != nullptr,
        /*is_speculator=*/shared_root != nullptr || cfg->is_speculator)
  , llm(llm)
  , max_layers(resolve_max_layers(is_eagle, cfg))
  , active_reclaimable_window_size(cache_t::max_reclaimable_window_size(
        cache_t::logical_slot_count_for_layers(max_layers)))
  , state(*llm, std::move(cfg->with_max_layers(max_layers)))
  , n_live_tokens(0)
  , live_token_limit([this]() -> int {
    int env_limit = std::getenv("TRON_LIVE_TOKEN_LIMIT")
                        ? std::atoi(std::getenv("TRON_LIVE_TOKEN_LIMIT"))
                        : 100000000;
    if (state.cfg.max_minibatches > 0) {
      int capacity = state.cfg.max_minibatches * model_t::max_minibatch_size;
      return std::min(env_limit, capacity);
    }
    return env_limit;
  }())
  , capacity_limit([this]() -> int {
    int limit = (int)ranged_mask::capacity;
    if (state.cfg.max_minibatches > 0) {
      int mb_limit = state.cfg.max_minibatches * model_t::max_minibatch_size;
      limit = std::min(mb_limit, limit);
    }
    return limit;
  }())
  , next_live_group(0) {
    TRON_ASSERT_EQ(is_eagle, llm->plugin.is_eagle);
    if (shared_root) {
      root = std::dynamic_pointer_cast<node_t>(shared_root);
      TRON_ASSERT(root, "incompatible shared_root");
    } else {
      const size_t logical_kv_slots =
          cache_t::logical_slot_count_for_layers(max_layers);
      const size_t storage_kv_slots =
          cache_t::storage_slot_count_for_layers(max_layers, cfg->support_eagle);
      root = std::make_shared<node_t>(
          logical_kv_slots, storage_kv_slots, cfg->support_eagle);
    }
  }

  ~full_scheduler() noexcept override {}

  // Persistent KV cache and token store
  std::shared_ptr<node_t> root;
  uint64_t next_kv_restore_attempt_ = 1;

  std::shared_ptr<node_base> get_root() noexcept override {
    return std::static_pointer_cast<node_base>(root);
  }

  bool verify_tree(std::string* error_msg) const override {
    return tron::verify_tree<book>(root, error_msg);
  }

  bool verify_used_set(
      std::vector<location_t> const& pinned, std::string* error_msg) const override {
    auto set_error = [&](std::string const& m) {
      if (error_msg) *error_msg = m;
      return false;
    };

    // Expected = {root} U the path-to-root of every pinned location's node.
    // follow_tombstones maps a (possibly coalesced) retained node to its live
    // survivor in the tree.
    std::unordered_set<node_base const*> expected;
    expected.insert(root.get());
    for (location_t const& loc : pinned) {
      if (!loc || !loc->node) continue;
      std::shared_ptr<node_t> n = follow_tombstones<book>(loc->node);
      while (n) {
        expected.insert(n.get());
        n = follow_tombstones<book>(n->parent_edge.parent);
      }
    }

    // Walk the tree: every `used` node must be expected, and (by count) every
    // expected node must be used. Used nodes are always reachable from root --
    // a used node is pinned, hence alive, as are all its (used) ancestors.
    size_t used_seen = 0;
    std::vector<node_t const*> extra;  // used but not in expected
    // At a quiescent point no node may still hold a pending listener -- one
    // that survives here is a stranded request.
    std::vector<node_t const*> stranded;
    std::vector<node_t*> stack{root.get()};
    while (!stack.empty()) {
      node_t* n = stack.back();
      stack.pop_back();
      if (n->used()) {
        ++used_seen;
        if (!expected.contains(n)) extra.push_back(n);
      }
      if (!n->listeners[0].empty() || !n->listeners[1].empty()) stranded.push_back(n);
      for (auto const& [tok, wchild] : n->children)
        if (std::shared_ptr<node_t> child = wchild.lock())
          stack.push_back(follow_tombstones<book>(child).get());
    }
    if (extra.empty() && stranded.empty() && used_seen == expected.size()) return true;

    std::string m = "used-set mismatch: " + std::to_string(used_seen) + " used, " +
                    std::to_string(expected.size()) + " expected (pinned closure), " +
                    std::to_string(extra.size()) + " used-but-unpinned, " +
                    std::to_string(stranded.size()) + " with-pending-listener";
    for (size_t i = 0; i < extra.size() && i < 8; ++i) {
      node_t const* n = extra[i];
      node_t const* parent =
          n->parent_edge.is_empty() ? nullptr : n->parent_edge.parent.get();
      m += "\n  used-but-unpinned @ht=" + std::to_string(n->abs_ht.i) +
           " n_children=" + std::to_string(n->n_children) +
           " subtree_pins=" + std::to_string(n->subtree_pins) +
           " in_evictable_queue=" + std::to_string(n->in_evictable_queue) +
           " parent_ht=" + (parent ? std::to_string(parent->abs_ht.i) : "none");
    }
    for (size_t i = 0; i < stranded.size() && i < 8; ++i) {
      node_t const* n = stranded[i];
      m += "\n  pending-listener @ht=" + std::to_string(n->abs_ht.i) +
           " subtree_pins=" + std::to_string(n->subtree_pins) +
           " used=" + std::to_string(n->used());
    }
    return set_error(m);
  }

  // Locations for per-invocation arguments
  int n_live_tokens;
  int64_t replay_tokens_in_forward_ = 0;
  int live_token_limit;  // Soft limit for performance (can be exceeded in some cases)
  int capacity_limit;    // Hard limit based on minibatch capacity (never exceeded)
  uint8_t next_live_group;
  indexed_vector<page_id, page*> kv_pages;
  std::unordered_set<book*> kv_books;
  indexed_vector<token_id, ::token_t> tokens;
  indexed_vector<token_id, uint32_t> token_positions;
  indexed_vector<token_id, page*> token_pages;
  indexed_vector<token_id, token_batching_affinity_id> live_groups;
  indexed_vector<token_id, typename model_t::activation_scalar const*> eagle_x_in;
  indexed_vector<token_id, typename model_t::activation_scalar*> eagle_x_out;
  indexed_vector<token_job_id, token_id> token_jobs;
  indexed_vector<token_job_id, uint8_t> token_jobs_do_kv;
  bool current_page_has_kv;
  indexed_vector<listener_id, token_id> listener_index;
  indexed_vector<listener_id, std::vector<logits_buffer_t>> listener_buffers;
  indexed_vector<listener_id, std::function<void()>> listener_notifications;
  // Ranged mask for HW/SW attention partitioning.
  // See doc/hw-kv-ranged-mask.md for full design.
  ranged_mask query_mask;
  // Stacks for stack-based range building during tree traversal.
  // See Note [Stack-Based Range Building] in ranged_mask.hpp.
  std::vector<shard_stack_entry> shard_stack;
  std::vector<query_stack_entry> query_stack;
  std::vector<hw_plan_entry> hw_plan;
  // Flat per-query GOF dispatch info.
  // Populated during descent for queries that complete a GOF.
  indexed_vector<token_job_id, gof_job> gof_jobs;
  // Round-robin device index for shard allocation.
  size_t next_shard_dev_ix = 0;

  // Clear temporaries (between calls to `forward`)
  void clear_tmp() noexcept {
    metrics.tokens_processed += n_live_tokens;
    n_live_tokens = 0;
    replay_tokens_in_forward_ = 0;
    next_live_group = 0;
    kv_pages.clear();
    kv_books.clear();
    tokens.clear();
    token_positions.clear();
    token_pages.clear();
    live_groups.clear();
    eagle_x_in.clear();
    eagle_x_out.clear();
    token_jobs.clear();
    token_jobs_do_kv.clear();
    current_page_has_kv = false;
    listener_index.clear();
    listener_buffers.clear();
    listener_notifications.clear();
    query_mask.clear();
    shard_stack.clear();
    query_stack.clear();
    hw_plan.clear();
    gof_jobs.clear();
  }

  // Debugging helper
  void report_tmp() const noexcept {
    TRON_ASSERT_EQ(tokens.size(), token_positions.size());
    spdlog::info("Tokens {}", tokens.items);
    spdlog::info("Token positions {}", token_positions.items);
    for (size_t i = 0; i < kv_pages.size(); ++i) {
      kv_pages.items[i]->report_coverage(i);
    }
    for (size_t i = 0; i < token_jobs.size(); ++i) {
      spdlog::info(
          "Token job {} do_kv={}", token_jobs.items[i].i, token_jobs_do_kv.items[i]);
    }
  }

  bool forward() noexcept override {

    // We wait to initialize the clock until we're on the work queue thread,
    // to avoid cross-core rdtsc skew.
    metrics.ensure_clock();
    bool scheduled_everything = true;
    for (auto const& poll : state.on_forward_poll)
      poll();
    {
      TRACE_EVENT("scheduler", "compute_forward_args");
      // The tree walk (compute_forward_args reads children/edges and writes the
      // per-node live/live_group scratch) is serialized against off-thread
      // OOM-rescue eviction by the global tree_lock. Tight scope: released at the
      // end of this block, BEFORE the forward dispatch and the workers/listeners
      // rendezvous, so an app-pool listener blocking on mu_ can never deadlock the
      // parked worker (the forward fence). A forward-pass allocation failing while
      // this lock is held makes the rescue thunk decline (reentrancy gate) rather
      // than evict mid-walk. See Note [Token Tree Mutation Lock].
      tron::tree_lock tree_guard;
      // Start fresh traversal from root
      size_t nodes_traversed = 0;
      auto [ok, root_masks_ptr, root_ranges, root_shards] =
          compute_forward_args(root.get(), nodes_traversed);
      scheduled_everything = ok;
      TRACE_EVENT("scheduler", "finalize_ranges");
      query_mask.ranges = finalize_ranges(std::move(root_ranges), tokens.size());
      TRACE_EVENT_INSTANT("scheduler", "forward args", "nodes_traversed",
          nodes_traversed, "tokens", tokens.size(), "token_jobs", token_jobs.size(),
          "kv_pages", kv_pages.size(), "listeners", listener_notifications.size());
    }
    auto num_listener_notifs = listener_notifications.size();
    if (token_jobs.empty()) {
      // Nothing at all to do.  Forget our state and exit.
      clear_tmp();
      TRON_ASSERT(
          scheduled_everything, "Scheduler stuck: no work scheduled but not finished");
      return true;
    }
    static_assert(sizeof(page*) == sizeof(std::unique_ptr<page>));
    TRON_ASSERT_EQ(listener_index.size(), num_listener_notifs);
    TRON_ASSERT_EQ(listener_buffers.size(), num_listener_notifs);

    // Note [Prompt HW-attention entries]
    // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    // build_edge_ranges may produce HW entries whose query masks contain many
    // prompt/prefill query tokens. Keep those entries HW-eligible: the entry's
    // last_token_ix is the shared HBM-resident K/V boundary, while any newer
    // per-query causal tail remains SW work in later ranges. construct_hw_plan
    // splits multi-query entries into worker-supported request shapes.
    //
    // HW mask reconciliation: mask propagation via subtree_masks can leave
    // hw_mask set (but sw_mask clear) for ranges that HW must not own. Short
    // queries below the HW-attention minimum are always SW-only. Causal tails
    // above an entry's HBM-resident boundary are also SW work; split finalized
    // ranges that straddle that boundary before moving the query bits.
    auto split_range_at = [&](token_id boundary) {
      auto& ranges = query_mask.ranges;
      for (auto it = ranges.begin(); it != ranges.end(); ++it) {
        if (!(it->tok_lo < boundary && boundary < it->tok_hi)) continue;
        token_range tail(boundary, it->tok_hi, it->sw_mask(), it->hw_mask());
        it->tok_hi = boundary;
        ranges.insert(it + 1, std::move(tail));
        return;
      }
    };
    for (const auto& entry : hw_plan) {
      mask_t<ranged_mask_capacity> short_query_bits;
      for (auto job_ix : entry.query_mask) {
        token_job_id job(job_ix);
        if (token_positions[token_jobs[job]] < tron::hw_attn_engagement_point())
          short_query_bits.insert(job_ix);
      }
      if (!short_query_bits.empty()) {
        for (auto& range : query_mask.ranges) {
          auto bits = range.hw_mask() & short_query_bits;
          if (!bits.empty()) {
            range.sw_mask() |= bits;
            for (auto job_ix : bits)
              range.hw_mask().erase(job_ix);
          }
        }
      }

      if (entry.query_mask.count() <= 1) continue;
      token_id tail_lo(entry.last_token_ix.i + 1);
      split_range_at(tail_lo);
      for (auto& range : query_mask.ranges) {
        if (range.tok_lo < tail_lo) continue;
        auto tail_bits = range.hw_mask() & entry.query_mask;
        if (!tail_bits.empty()) {
          range.sw_mask() |= tail_bits;
          for (auto job_ix : tail_bits)
            range.hw_mask().erase(job_ix);
        }
      }
    }
    sort_listeners();
    state.active_handle_id = active_handle_id;
    // Pass HW plan entries to model state for construct_hw_plan.
    // Empty when HW attention is gated off, so construct_hw_plan sees no
    // entries and the SW path runs end-to-end.
    state.hw_plan_entries =
        state.self_attn_state.hw_attn_eligible && model_t::use_hw_attn_for_this_model()
            ? std::span<const hw_plan_entry>(hw_plan.data(), hw_plan.size())
            : std::span<const hw_plan_entry>{};
    // Pass gof_jobs to model state for tree-unaware GOF dispatch.
    if (state.self_attn_state.hw_attn_eligible && !gof_jobs.empty()) {
      state.gof_jobs_span = gof_jobs;
      state.gof_rodeo_fn = [&state = this->state](size_t job_ix, size_t target_ix,
                               kv_slot_id slot, model_layer_id layer) {
        state.gof_rodeo_impl(job_ix, target_ix, slot, layer);
      };
    } else {
      state.gof_jobs_span = {};
      state.gof_rodeo_fn = nullptr;
    }
    if (is_eagle)
      // Temporarily select the extra physical EAGLE cache view.
      for (auto* b : kv_books)
        b->set_storage_view(b->eagle_storage_offset());
    select_trace_pass();  // See Note [Trace pass window boundary]
    if (pre_forward_hook) pre_forward_hook();
    state.forward(kv_pages, tokens, token_positions, token_pages, live_groups,
        eagle_x_in, eagle_x_out, token_jobs, token_jobs_do_kv, listener_index,
        listener_buffers, listener_notifications, query_mask);
    if (replay_tokens_in_forward_ != 0) {
      metrics.kv_reclamation_replayed_tokens.fetch_add(
          replay_tokens_in_forward_, std::memory_order_relaxed);
      note_kv_reclamation_replay(replay_tokens_in_forward_);
    }
    if (is_eagle)
      for (auto* b : kv_books)
        b->reset_storage_view();
    metrics.forward_passes++;
    complete_trace_pass();
    metrics.logits_delivered += listener_notifications.size();
    clear_tmp();
    metrics.report_performance();
    if (memory_pressure_requires_reclamation()) memory_pressure_recheck();
    return scheduled_everything;
  }

  // Returns whether the token was scheduled for KV (i.e., there was enough room)
  bool attempt_kv_job(token_id token_ix) noexcept {
    if (current_page_has_kv) {
      // This page already has KV work; only the hard capacity limit applies.
      if (n_live_tokens < capacity_limit) {
        token_jobs.push_back(token_ix);
        token_jobs_do_kv.push_back(1);
        return true;
      }
      return false;
    }
    // First KV token on this page: both soft and hard limits apply.
    if (n_live_tokens < std::min(live_token_limit, capacity_limit)) {
      token_jobs.push_back(token_ix);
      token_jobs_do_kv.push_back(1);
      current_page_has_kv = true;
      return true;
    }
    return false;
  }

  void ensure_listener(node_t* node) noexcept {
    TRON_ASSERT(!node->parent_edge.is_empty());
    auto prevent_dangle = node->shared_from_this();
    auto& node_listeners = node->listeners[is_eagle];
    auto& node_listener_buffers = node->listener_buffers[is_eagle];
    auto& node_listener_positions = node->listener_pin_positions[is_eagle];
    listener_index.push_back(token_id(tokens.size() - 1));
    listener_buffers.push_back(node_listener_buffers);
    listener_notifications.push_back(
        [prevent_dangle, &node_listeners, &node_listener_buffers,
            &node_listener_positions]() mutable {
          int fired = static_cast<int>(node_listeners.size());
          for (auto& lst : node_listeners)
            lst();
          node_listeners.clear();
          node_listener_buffers.clear();
          // Release the listener pins added at extend time (one per listener).
          // After this the node is still `used` if a seq_tip holds it or a
          // descendant carries a pin. See Note [Tracking Node Users].
          if (fired > 0) {
            // App-pool thread: one tree_lock over the listener-pin drop + the
            // coalesce, using the _locked primitives. The worker never holds
            // tree_lock across this rendezvous (run_requests completes before
            // run_executors->forward()), so the app-pool acquire cannot deadlock.
            // See Note [Token Tree Mutation Lock].
            tron::tree_lock guard;
            TRON_ASSERT_EQ(node_listener_positions.size(), static_cast<size_t>(fired));
            for (auto position : node_listener_positions)
              prevent_dangle->_forget_pin_position_locked(position);
            node_listener_positions.clear();
            prevent_dangle->_adjust_pins_locked(-fired);
            // Dropping the listener pin may have left this node an idle
            // single-child intermediate. coalesce_nodes refuses to coalesce a
            // node with a pending listener, so the ~node()/release paths can
            // skip it while a listener is live; re-check here once the listener
            // is gone, or it could linger un-coalesced (verify_tree check 6).
            prevent_dangle->_coalesce_if_unpinned_single_child_locked();
          }
          // Outside the guard: if this is the last ref, ~node acquires its own
          // tree_lock (it holds none here). See Note [Token Tree Mutation Lock].
          prevent_dangle.reset();
        });
  }

  // Sorts listeners so that all logits requests are at the end.
  void sort_listeners() noexcept {
    // Check whether all or no listeners request logits.
    auto requests_logits = [](std::vector<logits_buffer_t> const& buffers) {
      return std::any_of(buffers.begin(), buffers.end(), [](auto const& buffer) {
        return !std::holds_alternative<std::monostate>(buffer);
      });
    };
    size_t n_requests = 0;
    for (auto& buffers : listener_buffers)
      n_requests += requests_logits(buffers);
    if (n_requests == 0 || n_requests == listener_buffers.size())
      return;  // already sorted
    // Stable sort.
    std::vector<uint32_t> indices;
    indices.reserve(listener_buffers.size());
    for (size_t i = 0; i < listener_buffers.size(); ++i)
      if (!requests_logits(listener_buffers.items[i])) indices.push_back(i);
    for (size_t i = 0; i < listener_buffers.size(); ++i)
      if (requests_logits(listener_buffers.items[i])) indices.push_back(i);
    auto permute = [&](auto& items) {
      std::vector<std::decay_t<decltype(items[0])>> permuted;
      permuted.reserve(items.size());
      for (size_t i : indices)
        permuted.emplace_back(std::move(items[i]));
      items = std::move(permuted);
    };
    permute(listener_index.items);
    permute(listener_buffers.items);
    permute(listener_notifications.items);
  }

  // Returns (scheduled_everything, subtree_masks_ptr, range_list).
  // The masks propagate up the tree so the parent can union children
  // and emit ranges. The range list is this subtree's token_ranges in
  // sorted order.
  // subtree_masks are heap-allocated to keep per-frame size small during deep
  // traversal (mask_t<4096> is ~576 bytes each).
  using forward_result_t = std::tuple<bool,
      std::unique_ptr<subtree_masks>,
      std::list<token_range>,
      std::vector<std::shared_ptr<tron::hardware::shard>>>;

  // Note [Iterative Tree Traversal]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  // compute_forward_args performs a post-order DFS over the token tree using explicit
  // heap-backed frames. Keeping traversal state off the call stack avoids overflowing
  // on deep contexts while preserving the recursive traversal order.
  //
  // Each frame_t holds the per-node state that must survive across the
  // child-visiting phase: edge progress, shard state, subtree masks, completed child
  // ranges/shards, and the next child cursor.
  //
  // token_got_kv is allocated outside of the loop and reused via assign() each descent,
  // to avoid heap allocation on each edge.
  //
  // edge.gals lookup uses a linear scan because edges typically have 0-1 entries.
  forward_result_t compute_forward_args(
      node_t* initial_n, size_t& nodes_traversed) noexcept {
    using shard_sp = std::shared_ptr<tron::hardware::shard>;

    if (initial_n == nullptr)
      return std::make_tuple(true, std::unique_ptr<subtree_masks>{},
          std::list<token_range>{}, std::vector<shard_sp>{});

    // placed here to avoid extra mallocs. Used via assign() each descent.
    std::vector<uint8_t> token_got_kv;
    token_got_kv.reserve(tron::hardware::shard_tokens);

    struct frame_t {
      node_t* n;
      std::shared_ptr<node_t> child_ref;  // keeps active child alive
      shard_sp current_shard;
      bool shard_push_stopped;
      bool skip;  // unused non-listener node
      bool descended;
      token_id subtree_query_lo;
      size_t processed_tokens;
      bool scheduled_everything;
      std::unique_ptr<subtree_masks> masks;
      std::list<token_range> children_ranges;
      std::vector<shard_sp> children_shards;
      size_t next_child_idx;
    };

    // Define and initialize our replacement stack with the root node.
    std::vector<frame_t> stk;
    stk.reserve(1024);  // Allocate the capacity of a single shard to begin
    stk.push_back({initial_n, nullptr, nullptr, false, false, false, token_id(0), 0,
        true, std::make_unique<subtree_masks>(), {}, {}, 0});

    // Begin our iterative traversal loop, which continues until we've fully processed
    // the root node and all its descendants.
    while (!stk.empty()) {
      frame_t& f = stk.back();
      node_t* n = f.n;

      // ── Descent (runs once per frame) ──────────────────────────────────
      if (!f.descended) {
        f.descended = true;
        ++nodes_traversed;

        if (!n->used()) {
          // Skip this subtree for this traversal: it holds no pin, so no
          // descendant owes a request a token. A pending listener pins its
          // node and every ancestor (Note [Tracking Node Users]), so an
          // unused node cannot carry one; the assert makes that load-bearing,
          // which is what keeps the skip from dropping live work (the
          // lost-wakeup fix).
          TRON_ASSERT(n->listeners[is_eagle].empty(),
              "compute_forward_args skipping an unused node that still has a "
              "listener (ht={})",
              n->abs_ht.i);
          TRON_ASSERT(!n->parent_edge.is_empty(), "Root node unexpectedly unused");
          if (!n->parent_edge.is_empty()) {
            auto& edge = n->parent_edge;
            TRON_ASSERT(edge.kv_book != nullptr);
            TRON_ASSERT(edge.kv_first_entry_nr < edge.kv_book->size(),
                "Unused node points to unallocated KV space");
          }
          f.skip = true;
        }

        if (!f.skip) {
          n->live = false;
          n->live_group = token_batching_affinity_id{0};
          bool last_token_in_jobs = false;
          f.scheduled_everything = true;
          f.processed_tokens = 0;
          f.subtree_query_lo = token_id(tokens.size());

          if (!n->parent_edge.is_empty()) {
            auto& edge = n->parent_edge;
            node_t& parent = *edge.parent;

            if (state.self_attn_state.hw_attn_eligible)
              edge.stamp_handle_id(active_handle_id);

            // Process all tokens in the edge
            size_t edge_start_idx = tokens.size();  // Remember where this edge starts

            // Check if all tokens are KV ready
            bool all_ready = is_eagle ? edge.all_eagle_ready() : edge.all_kv_ready();
            // Per-token record of which tokens got KV jobs in this pass.
            token_got_kv.assign(edge.token_count(), 0);

            // Populate the per-token page*/page_offset cache on first touch;
            // idempotent O(1) when already valid. See Note [Edge Append Cache].
            TRON_ASSERT(edge.kv_book,
                "Edge missing KV book - this should not happen with atomic creation");
            edge.ensure_append_cache();
            auto const* cached_pages = edge.cached_token_pages_.data();
            auto const* cached_offsets = edge.cached_page_offsets_.data();
            auto& kv_book = edge.kv_book;

            // Process tokens in the edge
            size_t i;
            for (i = 0; i < edge.token_count(); ++i) {
              // Check if we've hit the token limit
              if (n_live_tokens >= live_token_limit) {
                f.scheduled_everything = false;
                break;
              }
              tokens.push_back(edge.token_at(i));
              auto& token_entry = edge.token_entries[i];

              // Absolute token index = parent's height + offset within edge
              // See Note [Token Position Types]
              auto abs_tok_ix = static_cast<uint32_t>(parent.abs_ht.i + i);
              token_positions.push_back(abs_tok_ix);
              live_groups.push_back(token_batching_affinity_id{0});

              auto page = cached_pages[i];
              uint16_t page_offset = cached_offsets[i];
              // This token is the current last token of this page.  Any future tokens
              // that may be encountered are later because of the traversal order, so
              // it's safe to just set this and overwrite later if there are more
              // tokens.
              page->set_offset_bound(page_offset + 1);

              if (page_offset == 0) {
                // This is the first token in its page; insert that page into the
                // traversal order
                kv_pages.push_back(page);
                kv_books.insert(kv_book.get());
                current_page_has_kv = false;
                // The page's influence begins with its own first token, inclusive
                page->set_lo(0, tokens.size() - 1);
              }
              token_pages.push_back(kv_pages.back());

              // Check if this specific token needs KV processing
              last_token_in_jobs = false;
              bool& kv_ready =
                  is_eagle ? token_entry.eagle_ready : token_entry.kv_ready;
              if (!kv_ready && !all_ready) {
                // The KV will be ready when `forward` completes, if we had room to add
                // it. Only attempt if we have a KV book allocated
                if (attempt_kv_job(token_id(tokens.size() - 1))) {
                  token_got_kv[i] = 1;
                  last_token_in_jobs = true;
                  kv_ready = true;
                  if (!is_eagle && token_entry.kv_replay_pending) {
                    ++replay_tokens_in_forward_;
                    token_entry.kv_replay_pending = false;
                  }
                  query_stack.push_back({
                      token_id(tokens.size() - 1),
                      token_job_id(token_jobs.size() - 1),
                  });
                  n_live_tokens++;
                  n->live = true;
                  n->live_group = parent.live
                                      ? parent.live_group
                                      : token_batching_affinity_id{next_live_group++};
                }
                f.scheduled_everything &= last_token_in_jobs;
              }
            }
            f.processed_tokens = i;

            // Extra bookkeeping for eagle children.
            using scalar = typename model_t::activation_scalar;
            if (is_eagle) {
              // Only process eagle bookkeeping for tokens we actually added
              for (size_t j = 0; j < i; ++j) {
                // Point to eagle model inputs.
                eagle_x_in.push_back(nullptr);
                if (j == 0) {
                  if (!parent.parent_edge.is_empty())
                      [[likely]] {  // parent is not root
                    // Use the last token from parent's edge
                    const auto& parent_edge_ref = parent.parent_edge;
                    TRON_ASSERT(parent_edge_ref.kv_book != nullptr);
                    size_t parent_last_index = parent_edge_ref.kv_last_entry_nr();
                    auto page = parent_edge_ref.kv_book->page_of(parent_last_index);
                    eagle_x_in.back() =
                        page->template x<scalar>(parent_last_index % page::page_size);
                  }
                } else {
                  // Use the previous token from the current edge
                  TRON_ASSERT(edge.kv_book != nullptr);
                  size_t prev_kv_entry_ix = edge.kv_entry_nr(j - 1);
                  auto page = edge.kv_book->page_of(prev_kv_entry_ix);
                  eagle_x_in.back() =
                      page->template x<scalar>(prev_kv_entry_ix % page::page_size);
                }
                eagle_x_out.push_back(nullptr);
                auto& token_entry = edge.token_entries[j];
                bool is_speculated = !token_entry.kv_ready;
                if (token_got_kv[j] && is_speculated) {
                  TRON_ASSERT(edge.kv_book != nullptr);
                  size_t kv_entry_ix = edge.kv_entry_nr(j);
                  auto page = edge.kv_book->page_of(kv_entry_ix);
                  eagle_x_out.back() =
                      page->template x<scalar>(kv_entry_ix % page::page_size);
                }
              }
            }
            // Extra bookkeeping for eagle parents.
            if (eagle_child) {
              // Only process eagle bookkeeping for tokens we actually added
              for (size_t j = 0; j < i; ++j) {
                // Point to eagle model outputs, to be consumed by the child.
                eagle_x_out.push_back(nullptr);
                if (token_got_kv[j]) {
                  auto& token_entry = edge.token_entries[j];
                  token_entry.eagle_ready =
                      false;  // the exact model invalidates the child cache
                  TRON_ASSERT(edge.kv_book != nullptr);
                  size_t kv_entry_ix = edge.kv_entry_nr(j);
                  auto page = edge.kv_book->page_of(kv_entry_ix);
                  eagle_x_out.back() =
                      page->template x<scalar>(kv_entry_ix % page::page_size);
                }
              }
            }
            // Only handle listeners if we processed the entire edge. Listeners are
            // registered at the node position (after all edge tokens), so partial
            // processing would record the wrong token index.
            if (f.processed_tokens == edge.token_count() &&
                !n->listeners[is_eagle].empty()) {
              if (last_token_in_jobs) {
                // Last token already has a KV job; piggyback the listener.
                ensure_listener(n);
              } else if (n_live_tokens < std::min(live_token_limit, capacity_limit)) {
                // We have room for this token (within both soft and hard limits).
                token_jobs.push_back(token_id(tokens.size() - 1));
                token_jobs_do_kv.push_back(0);
                query_stack.push_back({
                    token_id(tokens.size() - 1),
                    token_job_id(token_jobs.size() - 1),
                });
                ensure_listener(n);
                n_live_tokens++;
                n->live = true;
                n->live_group = parent.live
                                    ? parent.live_group
                                    : token_batching_affinity_id{next_live_group++};
              } else {
                f.scheduled_everything = false;
              }
            }

            // Create missing shards on dirty edges using trailing boundaries.
            // A shard's trailing boundary is the last token index in its range:
            // base + shard_tokens - 1. We create a shard when its trailing
            // boundary falls within this edge's token range.
            // Skip when no devices available (host-only / fake scheduler).
            //
            // Skip for the EAGLE child: it shares this edge with the exact
            // scheduler. EAGLE runs SW-only here, until we have HW support for it.
            auto* devs = pos_list_devices();
            bool have_devices = devs && !devs->empty();
            if (edge.dirty && state.self_attn_state.hw_attn_eligible && have_devices &&
                !is_eagle) {
              using tron::hardware::gof_tokens;
              using tron::hardware::shard_tokens;
              size_t edge_base = parent.abs_ht.i;
              size_t edge_end = edge_base + f.processed_tokens;

              // First trailing boundary at or after edge_base:
              // align_down(edge_base) + shard_tokens - 1.
              size_t first_trailing =
                  (edge_base / shard_tokens) * shard_tokens + shard_tokens - 1;

              // Find or create a shard at the given base. Searches
              // edge.shards first; allocates + backfills if missing.
              // Note [Retrying a degraded shard]
              // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
              // A shard that lost the race for HBM holds none and its range
              // runs software attention. Reusing it forever would make the
              // degradation permanent for this range, so node eviction and the
              // per-device shard LRU could return HBM that nothing is able to
              // claim -- the reclaim lever would be connected at one end only.
              //
              // So a degraded shard is rebuilt when a device can plausibly host
              // one. Two things keep that from thrashing. The capacity gate
              // skips hopeless attempts -- under sustained exhaustion every
              // device is short (observed in the field when all four cards had less
              // than the 64 KiB needed for one KV-slot region), so blind retries
              // would cause an allocation storm and a warning per KV slot every
              // forward pass. And the
              // replacement is built *before* the old shard is dropped, so a
              // rebuild that degrades anyway leaves the original in place. That
              // second part is what makes correctness independent of the gate,
              // which cannot predict fragmentation: a shard needs one contiguous
              // block per K and V region, and no aggregate figure proves those
              // are available.
              //
              // Scope: this runs from the dirty-edge path, so it revisits an
              // edge that gains tokens. A stable ancestor edge holding a
              // degraded shard is not swept, and stays on software attention
              // until it goes dirty again. A general sweep belongs with the
              // per-device shard LRU in governor §P1b part (b), which has to
              // walk shards by age regardless.
              const size_t shard_bytes = tron::hardware::shard_hbm_bytes(
                  state.self_attn_state.hw_attn_cfg,
                  static_cast<uint32_t>(state.self_attn_state.hw_attn_kv_slot_extent));
              // One K or V region: the smallest allocation a shard makes, and so
              // the floor any largest-free-block figure has to clear.
              const size_t region_bytes =
                  tron::hardware::shard_hw_pages * hwkv_pchannel_page_size_B;
              // A device that could plausibly host a whole shard, or nullptr.
              // Advisory only: a shard needs one contiguous region_bytes block
              // per K and V region, so neither the total nor the largest block
              // proves it will fit. Both are necessary conditions, and checking
              // them avoids the hopeless attempts -- the caller must still cope
              // with a rebuild that fails anyway. Searches from the round-robin
              // position so placement stays spread, advancing only on success.
              auto capable_device = [&]() -> ::PosDevice* {
                for (size_t i = 0; i < devs->size(); ++i) {
                  ::PosDevice* cand = (*devs)[tron::hardware::process_device_id{
                      (next_shard_dev_ix + i) % devs->size()}];
                  if (tron::hardware::kv_weights_free_bytes(cand) >= shard_bytes &&
                      tron::hardware::kv_weights_free_max_bytes(cand) >= region_bytes) {
                    next_shard_dev_ix += i + 1;
                    return cand;
                  }
                }
                return nullptr;
              };
              auto find_or_create_shard = [&](uint32_t shard_base,
                                              [[maybe_unused]] const char* label) {
                shard_sp degraded;
                for (auto const& sh : edge.shards) {
                  if (sh->base_tok_ix != shard_base) continue;
                  if (sh->hw_usable()) {
                    f.current_shard = sh;
                    return;
                  }
                  degraded = sh;
                  break;
                }

                ::PosDevice* dev = capable_device();
                if (dev == nullptr) {
                  // Keep an existing degraded shard rather than churning: it is
                  // the marker that stops the shard-push chain, and nothing has
                  // room for a replacement. See Note [Retrying a degraded
                  // shard].
                  if (degraded) {
                    f.current_shard = degraded;
                    return;
                  }
                  // No shard here yet, so one must exist even if it degrades.
                  // Round-robin keeps degraded ranges spread across cards.
                  dev = (*devs)[tron::hardware::process_device_id{
                      next_shard_dev_ix++ % devs->size()}];
                }
                // spdlog::debug("{}:{} allocating {} shard base {} "
                //               "on dev{}/{} ({})",
                //     __FUNCTION__, __LINE__, label, shard_base, dev->idx,
                //     devs->size(), dev->addr());
                auto sh = std::make_shared<tron::hardware::shard>(dev, shard_base,
                    static_cast<uint32_t>(state.self_attn_state.hw_attn_kv_slot_extent),
                    &state.self_attn_state.hw_attn_cfg);
                if (degraded && !sh->hw_usable()) {
                  // The rebuild degraded too, so keep the shard already here
                  // and discard this one -- it holds no HBM, so dropping the
                  // last reference costs nothing. Swapping regardless would
                  // churn a shard per pass whenever the capacity gate is
                  // defeated by fragmentation.
                  f.current_shard = degraded;
                  return;
                }
                if (degraded) {
                  // Log the all-clear, not just the degradation: without it a
                  // log shows ranges falling back and never returning, which
                  // reads as permanent. Info rather than warning -- this is the
                  // good outcome -- and rinzler logs info by default, so the
                  // pair stays visible together. Tying it to the originating
                  // query id needs request context the shard has no access to;
                  // that arrives with governor §P1b part (b).
                  spdlog::info("shard base tok_ix {} on dev {}: HBM available "
                               "again, rebuilt with HW attention",
                      shard_base, dev->idx);
                  n->remove_shard(shard_base);
                }
                n->add_shard(sh);
                tron::hardware::backfill_shard(sh, n, *state.dma_tracker);
                f.current_shard = sh;
              };

              // Create shards whose trailing boundary overlaps this edge.
              for (size_t trailing = first_trailing; trailing < edge_end;
                  trailing += shard_tokens) {
                TRON_ASSERT(trailing >= shard_tokens - 1);
                find_or_create_shard(
                    static_cast<uint32_t>(trailing - (shard_tokens - 1)), "boundary");
              }

              // Leaf trailing shard: tokens past the last full shard
              // boundary that contain at least one complete GOF.
              if (n->children.empty()) {
                size_t last_full_base =
                    first_trailing >= shard_tokens - 1
                        ? first_trailing - (shard_tokens - 1) + shard_tokens
                        : 0;
                if (first_trailing >= edge_end) {
                  last_full_base = (edge_base / shard_tokens) * shard_tokens;
                }
                if (edge_end > last_full_base) {
                  size_t trailing_tokens = edge_end - last_full_base;
                  if (trailing_tokens >= gof_tokens) {
                    find_or_create_shard(
                        static_cast<uint32_t>(last_full_base), "leaf trailing");
                  }
                }
              }

              edge.dirty = false;
              edge.edge_shard_cache_valid_ = false;
            }

            // Ensure current_shard reflects this edge's shards (covers
            // clean edges whose shards were created on a prior pass).
            if (!edge.shards.empty()) f.current_shard = edge.shards.back();

            // Populate gof_jobs for query tokens that participate in a GOF.
            // GOF creation is keyed by the GOF-ending position, but any mate
            // saving in this forward can cause the GAL to be created. This is
            // important for split edges such as [0] + [1..], where GOF 0's
            // completing token is on the child edge but token 0 is an ancestor
            // job in the same forward.
            //
            // Skip for the EAGLE child: it shares this edge with the exact
            // scheduler, and trips the TRON_ASSERT on 'has_gal_at_pos'.
            // Supporting HW attention for both peers on a shared edge requires
            // reconciling gal ownership, save_count, and per-owner GOF dispatch.
            // For now, EAGLE runs SW-only.
            if constexpr (model_t::model_shape_is_hwattn_eligible()) {
              if (state.self_attn_state.hw_attn_eligible && !is_eagle) {
                using tron::hardware::gof_tokens;
                size_t edge_base = parent.abs_ht.i;
                size_t edge_end = edge_base + f.processed_tokens;
                size_t kv_slot_extent = state.self_attn_state.hw_attn_kv_slot_extent;
                std::vector<uint32_t> gof_ends;

                // owning_book reports which book the page* came from, which may be
                // an ancestor edge's book rather than this edge's. page_info
                // records it so relocation can find what to rebuild.
                // See Note [GOF Page Relocation].
                auto find_page_for_abs =
                    [&](size_t abs_pos, page*& pg, size_t& pg_offset,
                        std::shared_ptr<book>* owning_book = nullptr) -> bool {
                  if (abs_pos >= edge_base && abs_pos < edge_end) {
                    size_t edge_off = abs_pos - edge_base;
                    size_t kv_ix = edge.kv_entry_nr(edge_off);
                    pg = edge.kv_book->page_of(kv_ix);
                    pg_offset = kv_ix % page::page_size;
                    if (owning_book) *owning_book = edge.kv_book;
                    return true;
                  }
                  for (node_t* path = n; path && !path->parent_edge.is_empty();
                      path = path->parent_edge.parent.get()) {
                    auto& path_edge = path->parent_edge;
                    size_t path_base = path_edge.parent->abs_ht.i;
                    size_t path_end = path->abs_ht.i;
                    if (abs_pos < path_base || abs_pos >= path_end) continue;
                    path_edge.ensure_append_cache();
                    size_t edge_off = abs_pos - path_base;
                    pg = path_edge.cached_token_pages_[edge_off];
                    pg_offset = path_edge.cached_page_offsets_[edge_off];
                    if (owning_book) *owning_book = path_edge.kv_book;
                    return true;
                  }
                  return false;
                };

                auto find_mate_job = [&](uint32_t mate_pos) -> size_t {
                  page* mate_page = nullptr;
                  size_t mate_page_offset = 0;
                  if (!find_page_for_abs(mate_pos, mate_page, mate_page_offset)) {
                    return SIZE_MAX;
                  }
                  const size_t this_edge_lo = edge_start_idx;
                  const size_t this_edge_hi = edge_start_idx + f.processed_tokens;
                  for (size_t jj = 0; jj < token_jobs.size(); ++jj) {
                    auto tid = token_jobs.items[jj];
                    if (token_positions.items[tid.i] != mate_pos) continue;
                    if (token_pages[tid] != mate_page) continue;
                    if (mate_page->offset_for(tid) != mate_page_offset) continue;
                    if (mate_pos >= edge_base) {
                      if (tid.i < this_edge_lo || tid.i >= this_edge_hi) continue;
                    }
                    return jj;
                  }
                  return SIZE_MAX;
                };

                auto ensure_gal_for_gof = [&](uint32_t gof_end,
                                              bool& created) -> tron::hardware::gal* {
                  created = false;
                  for (auto const& eg : edge.gals) {
                    if (eg->token_position == gof_end) return eg.get();
                  }

                  auto g =
                      std::make_unique<tron::hardware::gal>(gof_end, kv_slot_extent);
                  // See Note [GOF Page Relocation]. This is the single place a
                  // page_info is built; _relocate calls it again when the backing
                  // book moves, so the two paths cannot drift apart.
                  g->make_page_info = [](tron::hardware::page_info& pi,
                                          uint32_t abs_pos, void* pg_void, size_t off,
                                          const std::shared_ptr<void>& owning_book) {
                    auto* pg_ptr = static_cast<page*>(pg_void);
                    pi.position = abs_pos;
                    pi.owner_book = owning_book;
                    pi.kv_complete_fn = [pg_ptr, off](kv_slot_id slot) -> bool {
                      return pg_ptr->is_kv_complete(slot, off);
                    };
                    pi.k_head_fn = [pg_ptr, off](kv_slot_id slot, size_t kv_head,
                                       bf16* dest) -> bf16* {
                      constexpr kv_geometry hw_kv =
                          model_t::hardware_attention_geometry.kv;
                      pg_ptr->template get_k_row<hw_kv>(
                          slot, kv_head, off, k_destination_row<hw_kv.head_size>(dest));
                      return dest;
                    };
                    pi.v_head_fn = [pg_ptr, off](kv_slot_id slot, size_t kv_head,
                                       bf16* dest) -> bf16* {
                      // dest is page_info's caller-owned, 64-byte-aligned
                      // scratch: the packed row is unpacked into it (get_v ->
                      // load_row) and returned from there.
                      pg_ptr->template get_v<model_t::hardware_attention_geometry.kv>(
                          slot, kv_head, off,
                          v_destination_row<
                              model_t::hardware_attention_geometry.kv.head_size>(dest));
                      return dest;
                    };
                  };
                  size_t gof_base = gof_end - (gof_tokens - 1);
                  for (size_t k = 0; k < gof_tokens; ++k) {
                    size_t abs_pos = gof_base + k;
                    page* pg = nullptr;
                    size_t pg_offset = 0;
                    std::shared_ptr<book> owning_book;
                    (void)find_page_for_abs(abs_pos, pg, pg_offset, &owning_book);
                    TRON_ASSERT(pg, "GOF: no page for abs_pos {}", abs_pos);
                    g->make_page_info(g->pages[k], static_cast<uint32_t>(abs_pos), pg,
                        pg_offset, std::static_pointer_cast<void>(owning_book));
                  }
                  g->gofs.resize(kv_slot_extent);
                  // Keep only HW-slot GOFs. Their staging is allocated and populated
                  // when gof_rodeo_impl() calls prepare_for_dma().
                  for (size_t slot_ix = 0; slot_ix < kv_slot_extent; ++slot_ix) {
                    kv_slot_id const slot(slot_ix);
                    if (hardware::slot_uses_hw(
                            state.self_attn_state.hw_attn_cfg, slot)) {
                      g->gofs[slot.i] = std::make_shared<tron::hardware::gof>(
                          hardware::HW_BAKED_HEAD_SIZE, hardware::deferred_staging);
                    }
                  }
                  edge.gals.push_back(std::move(g));
                  created = true;
                  return edge.gals.back().get();
                };

                for (size_t ti = 0; ti < f.processed_tokens; ++ti) {
                  if (ti >= token_got_kv.size() || !token_got_kv[ti]) continue;
                  size_t abs = edge_base + ti;
                  uint32_t gof_base =
                      static_cast<uint32_t>((abs / gof_tokens) * gof_tokens);
                  uint32_t gof_end = static_cast<uint32_t>(gof_base + gof_tokens - 1);
                  // This edge owns the GAL for GOFs whose ending token is in
                  // the materialized part of this edge. If the ending token is
                  // still in the future, a later edge/pass will create it.
                  if (gof_end < edge_base || gof_end >= edge_end) continue;
                  if (std::find(gof_ends.begin(), gof_ends.end(), gof_end) ==
                      gof_ends.end()) {
                    gof_ends.push_back(gof_end);
                  }
                }

                for (uint32_t gof_end : gof_ends) {
                  bool gal_created = false;
                  auto* gal_ptr = ensure_gal_for_gof(gof_end, gal_created);
                  uint32_t gof_base = static_cast<uint32_t>(gof_end - (gof_tokens - 1));

                  // Wire every saving mate to the same GAL, including ancestor
                  // mates already added to token_jobs before this edge. Mates
                  // that will not save in this forward are preloaded once when
                  // the GAL is created if their K/V is already complete.
                  for (size_t mk = 0; mk < gof_tokens; ++mk) {
                    uint32_t mate_pos = static_cast<uint32_t>(gof_base + mk);
                    size_t mate_jid = find_mate_job(mate_pos);
                    bool will_save =
                        mate_jid != SIZE_MAX && token_jobs_do_kv.items[mate_jid];
                    if (will_save) {
                      if (gof_jobs.size() <= mate_jid) gof_jobs.resize(mate_jid + 1);
                      gof_job& mate_gof_job = gof_jobs[token_job_id(mate_jid)];
                      mate_gof_job.hw_params = &state.self_attn_state.hw_attn_cfg;
                      mate_gof_job.add_target(gof_end, gal_ptr);
                    } else if (gal_created) {
                      // kv_complete_fn dispatches to page::is_kv_complete,
                      // and kv_slot_extent is bounded by the configured cache.
                      for (size_t slot_ix = 0; slot_ix < kv_slot_extent; ++slot_ix) {
                        kv_slot_id const slot(slot_ix);
                        auto const& gof = gal_ptr->gofs[slot.i];
                        if (gof && gal_ptr->pages[mk].kv_complete_fn(slot)) {
                          gof->save_count.fetch_add(2, std::memory_order_relaxed);
                        }
                      }
                    }
                  }
                }
              }
            }

            // Push shard events for this edge, filtered by DMA eligibility.
            // Only eligible shards are pushed; once an ineligible shard is
            // encountered the chain stops for this subtree (shard_push_stopped).
            if (!f.shard_push_stopped) {
              for (auto& si : edge.edge_shards()) {
                auto const& sh = si.shard_ptr;
                bool is_first = (sh.base_tok_ix == 0);
                if (is_first) {
                  // First shard needs minimum GOFs for offload.
                  // Push position is the shard's DMA'd range (not the edge
                  // boundary) so the ranged mask aligns with what HW reads.
                  size_t complete_prefix_gofs = sh.count_complete_prefix_gofs();
                  if (complete_prefix_gofs >= hwkv_min_gofs_for_offload) {
                    size_t dma_last_abs =
                        sh.base_tok_ix +
                        complete_prefix_gofs * tron::hardware::gof_tokens - 1;
                    // HW requires a minimum context length.
                    if (dma_last_abs < tron::hw_attn_engagement_point()) {
                      f.shard_push_stopped = true;
                      break;
                    }
                    // Shard's DMA must reach this edge's start before it is
                    // useful here. A spanning shard (base_tok_ix < edge_base)
                    // may not have DMA'd into this edge's range yet.
                    if (dma_last_abs < parent.abs_ht.i) {
                      f.shard_push_stopped = true;
                      break;
                    }
                    // Convert to batch-relative: same as middle-shard formula.
                    size_t dma_last_rel =
                        f.subtree_query_lo.i + (dma_last_abs - parent.abs_ht.i);
                    shard_stack.push_back({token_id(dma_last_rel), si.shard_ptr});
                  } else {
                    f.shard_push_stopped = true;
                    break;
                  }
                } else if (sh.dma_complete()) {
                  // Middle shard: must be fully DMA-complete
                  shard_stack.push_back(
                      {token_id(f.subtree_query_lo.i + si.last_token_offset),
                          si.shard_ptr});
                } else {
                  // Check if partial leaf shard with at least 1 GOF
                  size_t complete_prefix_gofs = sh.count_complete_prefix_gofs();
                  if (complete_prefix_gofs >= 1) {
                    // Partial shard: push but stop chain.
                    // Use DMA progress (not edge extent) so rel_tok_ix in
                    // prepare_hw_attention matches actual HBM contents.
                    size_t dma_last_abs =
                        sh.base_tok_ix +
                        complete_prefix_gofs * tron::hardware::gof_tokens - 1;
                    // Only push if DMA has reached this edge; a spanning shard
                    // with dma_last_abs < edge_base has no data here yet.
                    if (dma_last_abs >= parent.abs_ht.i) {
                      size_t dma_last_rel =
                          f.subtree_query_lo.i + (dma_last_abs - parent.abs_ht.i);
                      shard_stack.push_back({token_id(dma_last_rel), si.shard_ptr});
                    }
                  }
                  f.shard_push_stopped = true;
                  break;
                }
              }
            }
            // Update live groups for all tokens we added from this edge
            for (size_t j = edge_start_idx; j < tokens.size(); ++j)
              live_groups[token_id(j)] = n->live_group;

          } else {
            TRON_ASSERT(n->listeners[is_eagle].empty(), "Root node has listeners");
          }
        }
      }  // end descent

      // ── Push next child ────────────────────────────────────────────────
      // Traverse children, then build ranges for this edge on ascent.
      // Each child builds its own range list; we splice them together,
      // then prepend this edge's ranges (lower kv indices).
      // We rely on insertion order here.  We want all tokens from a given
      // KV page to be inserted into the `tokens` array contiguously, because
      // `llama_model::state::forward` relies on that for correctness in a
      // couple of places.  This requires us to traverse the first-inserted child
      // (which is the one that shares the KV page) first.  The other children
      // can go in any order.
      if (!f.skip) {
        bool should_visit = n->parent_edge.is_empty() ||
                            f.processed_tokens == n->parent_edge.token_count();
        if (should_visit) {
          bool pushed_child = false;
          while (f.next_child_idx < n->children.size()) {
            size_t idx = f.next_child_idx++;
            auto child = std::get<1>(*(n->children.begin() + idx)).lock();
            if (child) {
              child = follow_tombstones(child);
              if (child) {
                f.child_ref = child;  // keep alive while child frame is on stack
                stk.push_back({child.get(), nullptr, f.current_shard,
                    f.shard_push_stopped, false, false, token_id(0), 0, true,
                    std::make_unique<subtree_masks>(), {}, {}, 0});
                pushed_child = true;
                break;
              }
            }
          }
          if (pushed_child) continue;
        }
      }

      // ── Ascent (all children done) ─────────────────────────────────────
      {
        std::list<token_range> my_ranges;
        // Shards propagated to parent from this subtree.
        std::vector<shard_sp> my_shards;

        if (!f.skip) {
          if (n->parent_edge.is_empty()) {
            my_ranges.splice(my_ranges.end(), f.children_ranges);
          } else {
            // Ascent: compute shards_getting_gofs for this edge and wire
            // into gof_jobs. Collects this edge's DMA-incomplete shards
            // plus children's shards that overlap this edge's token range.
            if (state.self_attn_state.hw_attn_eligible) {
              auto& edge = n->parent_edge;
              size_t edge_base = edge.parent->abs_ht.i;
              size_t edge_end = edge_base + f.processed_tokens;

              // This edge's DMA-incomplete shards. A degraded shard holds no
              // HBM and never completes, so it must not be enlisted as a DMA
              // target. See Note [HBM exhaustion degrades to software
              // attention].
              for (auto const& sh : edge.shards) {
                if (sh->hw_usable() && !sh->dma_complete()) my_shards.push_back(sh);
              }

              // Children's shards that overlap this edge's token range.
              for (auto& cs : f.children_shards) {
                size_t sh_base = cs->base_tok_ix;
                size_t sh_end = sh_base + tron::hardware::shard_tokens;
                if (sh_base < edge_end && sh_end > edge_base) {
                  // Assert not already present (each shard appears once).
                  TRON_ASSERT(std::find(my_shards.begin(), my_shards.end(), cs) ==
                                  my_shards.end(),
                      "duplicate shard in shards_getting_gofs");
                  my_shards.push_back(cs);
                }
              }

              // GOFs on this edge may belong to a shard owned by an
              // ancestor edge (e.g., decode-time edges whose tokens fall
              // inside the first shard's [0, shard_tokens) range but which
              // did not create the shard themselves). current_shard is
              // threaded through descent and points at that shard. Include
              // it when wiring gof_jobs, but don't propagate upward — the
              // ancestor's own ascent already owns it.
              std::vector<shard_sp> for_gofs = my_shards;
              if (f.current_shard && f.current_shard->hw_usable() &&
                  !f.current_shard->dma_complete()) {
                size_t sh_base = f.current_shard->base_tok_ix;
                size_t sh_end = sh_base + tron::hardware::shard_tokens;
                if (sh_base < edge_end && sh_end > edge_base &&
                    std::find(for_gofs.begin(), for_gofs.end(), f.current_shard) ==
                        for_gofs.end()) {
                  for_gofs.push_back(f.current_shard);
                }
              }

              // Wire shards_getting_gofs into gof_jobs on this edge.
              // Scope by gal identity — each gal lives on exactly one edge.
              // Position alone is ambiguous: sibling edges share the same
              // absolute range (both cover [parent.abs_ht.i, ...)), so a
              // positional match would rewrite a sibling's wiring on the
              // later ascent.
              // edge.gals is typically 0–1 entries; linear scan avoids hash
              // table allocation.
              for (auto& job : gof_jobs) {
                for (auto& target : job.targets) {
                  if (target.gal_ptr == nullptr) continue;
                  for (auto const& g : edge.gals) {
                    if (g.get() == target.gal_ptr) {
                      target.shards_getting_gofs = for_gofs;
                      break;
                    }
                  }
                }
              }
            }

            // Build per-entry ranges for this edge using stack-based ascent.
            // See Note [Stack-Based Range Building] in ranged_mask.hpp.
            // build_edge_ranges prepends ranges (sorted within edge).
            // Splice edge ranges before children's (parent has lower kv indices).
            std::list<token_range> edge_ranges;
            if (f.processed_tokens > 0) {
              build_edge_ranges(f.subtree_query_lo,
                  token_id(f.subtree_query_lo.i + f.processed_tokens), shard_stack,
                  query_stack, *f.masks, hw_plan, edge_ranges);
            }
            edge_ranges.splice(edge_ranges.end(), f.children_ranges);
            my_ranges.splice(my_ranges.end(), edge_ranges);
          }
        }

        bool ok = f.scheduled_everything;
        auto my_masks = std::move(f.masks);
        stk.pop_back();  // f is now invalid

        if (!stk.empty()) {
          auto& p = stk.back();
          p.scheduled_everything &= ok;
          if (my_masks) *p.masks |= *my_masks;
          p.children_ranges.splice(p.children_ranges.end(), my_ranges);
          for (auto& cs : my_shards)
            p.children_shards.push_back(std::move(cs));
          p.child_ref.reset();
        } else {
          return forward_result_t(
              ok, std::move(my_masks), std::move(my_ranges), std::move(my_shards));
        }
      }
    }

    TRON_ASSERT(false, "compute_forward_args: unreachable");
    return std::make_tuple(true, std::unique_ptr<subtree_masks>{},
        std::list<token_range>{}, std::vector<shard_sp>{});
  }

  size_t vocab_size() const noexcept override {
    return model_t::vocab_size;
  }

  // Note [Sliding-window KV reclamation]
  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  // A book owns page-aligned chunks for slots whose consumers use only finite
  // sliding windows. Each chunk is reserved before its first token is added,
  // and can leave DMA memory once it is older than every protected query's
  // widest window. Full-history slots and logical page identities remain.
  // The extra page covers queries already grouped into the next minibatch.
  //
  // Token-tree prefix matching keeps a reclaimed book reachable. Before a
  // matching add mutates the tree, a read-only preview identifies each matched
  // unready token plus the first novel or final listener query. A rootward walk
  // checks missing chunks against those demand windows, then restores all
  // missing populated chunks of each required book and closes each
  // requirement over a genuinely resident and ready predecessor window. A
  // reclaimed or invalid book in that halo moves the boundary older; a
  // contiguous reclaimed prefix can therefore restore to the root, while a
  // long ready gap is not rematerialized. Newly allocated blank KV is never
  // treated as a halo. Stored KV at each attention layer makes one
  // widest-operation window sufficient: replay of token T reads that layer's
  // cached predecessors while T's activation proceeds upward. Rare old-prefix
  // rematches can consequently allocate and replay O(prefix) bytes, and fail
  // cleanly if that memory cannot be recovered.
  //
  // A restore attempt tags each chunk it allocates and remains provisional
  // through cache growth. A temporary path pin keeps its matched nodes alive;
  // release uses the cache's normal release/requeue path because add-time
  // eviction can inspect that pin. Failed preparation or growth walks the same
  // ancestry and frees exactly that attempt, leaving readiness and GOF state
  // untouched. Successful growth invalidates every edge in each restored book
  // before publishing its chunks. Defrag skips tagged books. The book-chain
  // invariant makes the abort and commit walks allocation-free. Clearing
  // token-wide readiness and GOF lists at commit is deliberate: limiting replay
  // to reclaimed slots is unsafe while an existing partial hardware-attention
  // structure can still lack regenerated DMA.
  // Restore-allocation retry eviction happens only after a failed attempt
  // returns: walk-local references would otherwise make a cached leaf appear
  // non-evictable and silently remove it from the cache queue. The caller may
  // evict one book and retry once.
  //
  // A normal extension matches no cached child and returns before the restore
  // walk: its pinned source already owns a resident, ready halo. A cached-prefix
  // hit still compares the prefix in this preview, scans matched readiness and
  // the dependency halo, then compares the prefix again in the add path. Even
  // with all chunks resident, this adds work linear in the matched prefix.
  // Only books requiring restoration need full-chain certification, whose
  // child searches also depend on fork fanout.
  //
  // Pressure-only scans run between forwards under tree_lock, after unused
  // edges have been evicted, including before worker-side cache growth. The
  // governor rechecks live host usage at each released chunk
  // and stops as soon as its target is met. A weak scheduler registry includes
  // idle schedulers without extending their lifetime. Already reclaimed books
  // still need ancestry, readiness, and pin checks on later scans; full-chain
  // certification precedes chunk release.
  //
  // Direct pins are subtree pins minus child subtree pins. Client and listener
  // pins save their query positions independently of mutable edge boundaries.
  // Their minimum permits reclamation inside the tip's own book when every
  // subtree pin is direct and positioned. Anonymous pins and descendant pins
  // keep the conservative book-start bound. Defrag only moves storage into an
  // older book. An anchor with more pins than the scanned tip has another active
  // lineage, so reclamation stops before it. Unready books stop the walk too: a request
  // batch can install dependent extensions before any forward executes.
  // No reclamation tree walk is needed when pressure is absent.
  //
  // A book has one contiguous same-book chain, but a fork may put that chain's
  // continuation off the lineage being advanced. The anchor's pin count proves
  // that every such continuation is inactive; book-local invalidation follows
  // the unique continuation and covers it anyway. This load-bearing chain
  // invariant is also checked by verify_tree. These walks allocate no
  // recovery-path containers.

  struct book_path_segment final {
    std::shared_ptr<node_t> anchor;
    std::shared_ptr<node_t> older;
    size_t token_entries = 0;
  };

  book_path_segment inspect_book_path(std::shared_ptr<node_t> newest) noexcept {
    TRON_ASSERT(newest && !newest->parent_edge.is_empty(),
        "KV book path requires a non-root node");
    book* const target = newest->parent_edge.kv_book.get();
    TRON_ASSERT(target != nullptr, "KV book path has no book");
    book_path_segment result;
    for (std::shared_ptr<node_t> current = std::move(newest); current;
        current = current->parent_edge.parent) {
      auto const& edge = current->parent_edge;
      TRON_ASSERT(!edge.is_empty() && edge.kv_book.get() == target,
          "KV book path reached another book before its anchor");
      TRON_ASSERT_LE(edge.token_count(),
          std::numeric_limits<size_t>::max() - result.token_entries);
      result.token_entries += edge.token_count();
      if (edge.kv_first_entry_nr == 0) {
        result.anchor = current;
        result.older = edge.parent;
        return result;
      }
    }
    TRON_ASSERT(false, "KV book path has no anchor");
    return result;
  }

  bool book_path_is_ready(std::shared_ptr<node_t> newest) noexcept {
    book* const target = newest->parent_edge.kv_book.get();
    for (std::shared_ptr<node_t> current = std::move(newest); current;
        current = current->parent_edge.parent) {
      auto const& edge = current->parent_edge;
      TRON_ASSERT(!edge.is_empty() && edge.kv_book.get() == target,
          "KV readiness walk left its book");
      if (!edge.all_kv_ready()) return false;
      if (edge.kv_first_entry_nr == 0) return true;
    }
    TRON_ASSERT(false, "KV readiness walk has no book anchor");
    return false;
  }

  std::optional<size_t> first_unready_in_book_range(
      std::shared_ptr<node_t> newest, size_t begin, size_t end) noexcept {
    book* const target = newest->parent_edge.kv_book.get();
    std::optional<size_t> result;
    for (std::shared_ptr<node_t> current = std::move(newest); current;
        current = current->parent_edge.parent) {
      auto const& edge = current->parent_edge;
      TRON_ASSERT(!edge.is_empty() && edge.kv_book.get() == target,
          "KV readiness-range walk left its book");
      size_t const edge_begin = edge.parent->abs_ht.i;
      size_t const edge_end = current->abs_ht.i;
      size_t const scan_begin = std::max(begin, edge_begin);
      size_t const scan_end = std::min(end, edge_end);
      for (size_t position = scan_begin; position < scan_end; ++position) {
        if (!edge.token_entries[position - edge_begin].kv_ready) {
          result = result ? std::min(*result, position) : position;
          break;
        }
      }
      if (edge.kv_first_entry_nr == 0) return result;
    }
    TRON_ASSERT(false, "KV readiness-range walk has no book anchor");
    return std::nullopt;
  }

  // Visit exactly the reclaimed books required by matched replay or its
  // predecessor closure. `attempt` makes an arena allocated by an earlier
  // visit look reclaimed while the same allocation-free walk is repeated for
  // rollback or publication.
  template <typename Visitor>
  bool walk_required_kv_restores(std::shared_ptr<node_t> tip,
      size_t matched_begin,
      size_t matched_end,
      size_t initial_demand,
      int64_t margin,
      uint64_t attempt,
      Visitor&& visit,
      bool& required_any) noexcept {
    size_t const window = active_reclaimable_window_size;
    detail::kv_restore_dependency_scan dependency{
        .window = window,
        .margin = margin,
        .nearest_demand = initial_demand,
    };
    while (tip && !tip->parent_edge.is_empty()) {
      book_path_segment const segment = inspect_book_path(tip);
      book* const candidate = tip->parent_edge.kv_book.get();

      if (std::optional<size_t> const unready =
              first_unready_in_book_range(tip, matched_begin, matched_end))
        dependency.include_demand(*unready);

      size_t const book_path_end = std::min(matched_end, tip->abs_ht.i);
      size_t const book_begin = segment.anchor->parent_edge.parent->abs_ht.i;
      bool required = false;
      for (size_t chunk = 0; chunk < candidate->reclaimable_chunk_count(); ++chunk) {
        size_t const chunk_begin =
            book_begin + candidate->reclaimable_chunk_token_begin(chunk);
        if (chunk_begin >= book_path_end) break;
        size_t const chunk_end = std::min(
            book_path_end, book_begin + candidate->reclaimable_chunk_token_end(chunk));
        if (dependency.arena_is_required(
                candidate->reclaimable_chunk_needs_restore(chunk, attempt),
                chunk_end)) {
          required = true;
          break;
        }
      }
      if (required) {
        certify_book_chain(segment.anchor);
        required_any = true;
        if (!visit(segment, *candidate)) return false;
        dependency.include_restored_book();
      } else if (dependency.needs_predecessor_tokens()) {
        dependency.include_resident_book(
            book_path_is_ready(tip), segment.token_entries);
      }

      tip = segment.older;
      if (!tip || tip->parent_edge.is_empty()) break;
      bool const matched_range_remains = tip->abs_ht.i > matched_begin;
      if (dependency.can_stop_before(tip->abs_ht.i, matched_range_remains)) break;
    }
    return true;
  }

  std::shared_ptr<node_t> same_book_child(
      node_t& node, book const* target, size_t expected_first) noexcept {
    std::shared_ptr<node_t> result;
    for (auto const& [token, weak_child] : node.children) {
      std::shared_ptr<node_t> child = weak_child.lock();
      if (!child || child->parent_edge.is_empty() ||
          child->parent_edge.kv_book.get() != target)
        continue;
      TRON_ASSERT(!result, "KV book has more than one continuation");
      TRON_ASSERT(child->parent_edge.kv_first_entry_nr == expected_first,
          "KV book continuation is not contiguous");
      result = std::move(child);
    }
    return result;
  }

  void certify_book_chain(std::shared_ptr<node_t> anchor) noexcept {
    book* const target = anchor->parent_edge.kv_book.get();
    size_t expected_first = 0;
    for (std::shared_ptr<node_t> current = std::move(anchor); current;) {
      auto const& edge = current->parent_edge;
      TRON_ASSERT(!edge.is_empty() && edge.kv_book.get() == target,
          "KV book certification left its chain");
      TRON_ASSERT(edge.kv_first_entry_nr == expected_first,
          "KV book chain has a gap or overlap");
      TRON_ASSERT_LE(
          edge.token_count(), std::numeric_limits<size_t>::max() - expected_first);
      expected_first += edge.token_count();
      current = same_book_child(*current, target, expected_first);
    }
    TRON_ASSERT(expected_first == target->size(),
        "KV book chain does not cover its live entries");
  }

  void invalidate_restored_book(
      std::shared_ptr<node_t> anchor, uint64_t attempt) noexcept {
    book* const target = anchor->parent_edge.kv_book.get();
    TRON_ASSERT(target->reclaimable_kv_restore_attempt() == attempt,
        "Invalidating a book from another restore attempt");
    size_t expected_first = 0;
    for (std::shared_ptr<node_t> current = std::move(anchor); current;) {
      auto& edge = current->parent_edge;
      TRON_ASSERT(!edge.is_empty() && edge.kv_book.get() == target,
          "KV invalidation walk left its book");
      TRON_ASSERT(edge.kv_first_entry_nr == expected_first,
          "KV invalidation found a book-chain gap or overlap");
      for (size_t i = 0; i < edge.token_count(); ++i) {
        auto& entry_info = edge.token_entries[i];
        entry_info.kv_replay_pending |= entry_info.kv_ready;
        entry_info.kv_ready = false;
        size_t const entry = edge.kv_first_entry_nr + i;
        target->page_of(entry)->clear_kv_complete_at(entry % book::page_size);
      }
      edge.gals.clear();
      edge.dirty = true;
      edge.invalidate_shard_cache();
      TRON_ASSERT_LE(
          edge.token_count(), std::numeric_limits<size_t>::max() - expected_first);
      expected_first += edge.token_count();
      current = same_book_child(*current, target, expected_first);
    }
    TRON_ASSERT(expected_first == target->size(),
        "KV invalidation did not cover the complete book chain");
  }

  TRON(nodiscard, inline, pure)
  int64_t kv_reclamation_margin() const noexcept {
    constexpr size_t max_position =
        static_cast<size_t>(std::numeric_limits<int64_t>::max());
    static_assert(book::page_size < max_position);
    static_assert(
        book::max_reclaimable_window_size() <= max_position - 1 - book::page_size);
    return static_cast<int64_t>(active_reclaimable_window_size) + 1 +
           static_cast<int64_t>(book::page_size);
  }

  void scan_reclamation_boundary(std::shared_ptr<node_t> const& tip,
      std::shared_ptr<node_t> candidate,
      int64_t oldest_query_pos,
      int64_t margin) noexcept {
    while (candidate && !candidate->parent_edge.is_empty() &&
           memory_pressure_requires_reclamation()) {
      metrics.kv_reclamation_books_scanned.fetch_add(1, std::memory_order_relaxed);
      book_path_segment const segment = inspect_book_path(candidate);
      book* const candidate_book = candidate->parent_edge.kv_book.get();
      if (!book_path_is_ready(candidate)) break;
      if (segment.anchor->subtree_pins != tip->subtree_pins) break;
      size_t const book_begin = segment.anchor->parent_edge.parent->abs_ht.i;
      int64_t released = 0;
      bool certified = false;
      for (size_t chunk = 0; chunk < candidate_book->reclaimable_chunk_count() &&
                             memory_pressure_requires_reclamation();
          ++chunk) {
        size_t const begin = candidate_book->reclaimable_chunk_token_begin(chunk);
        if (begin < candidate_book->size()) {
          size_t const end = std::min(candidate_book->size(),
              candidate_book->reclaimable_chunk_token_end(chunk));
          int64_t const newest_token =
              detail::checked_kv_position(book_begin + end) - 1;
          if (oldest_query_pos - newest_token < margin) continue;
        }
        // Eviction can leave an unused resident tail. It protects no history
        // and may be released even when preceding populated chunks are needed.
        if (!certified) {
          certify_book_chain(segment.anchor);
          certified = true;
        }
        int64_t const bytes = candidate_book->free_reclaimable_kv_chunk(chunk);
        if (bytes != 0) {
          note_book_storage_delta(-bytes, segment.anchor->used());
          released += bytes;
        }
      }
      if (released > 0) {
        metrics.kv_reclamation_books_released.fetch_add(1, std::memory_order_relaxed);
        metrics.kv_reclamation_bytes_released.fetch_add(
            released, std::memory_order_relaxed);
        note_kv_reclamation_release(released);
      }
      candidate = segment.older;
    }
  }

  reclaimed_kv_restore prepare_reclaimed_kv_restore(node_base* from,
      std::span<::token_t const> tokens,
      int64_t from_position) noexcept override {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "prepare_reclaimed_kv_restore without tree_lock");
    size_t const window = active_reclaimable_window_size;
    if (window == 0) return {};
    if (from == nullptr) return {};
    auto from_node = std::static_pointer_cast<node_t>(from->shared_from_this());
    TRON_ASSERT_GE(from_position, 0);
    TRON_ASSERT(from_position == detail::checked_kv_position(from_node->abs_ht.i),
        "KV restore preview position does not match its source tip");
    auto tip = from_node;
    size_t token_offset = 0;
    while (token_offset < tokens.size()) {
      ::token_t const first = tokens[token_offset];
      if (!tip->children.contains(first)) break;
      std::shared_ptr<node_t> child = tip->children[first].lock();
      if (!child) break;
      auto const& edge = child->parent_edge;
      size_t const available = tokens.size() - token_offset;
      size_t const compared = std::min(available, edge.token_count());
      size_t matched = 0;
      while (matched < compared &&
             edge.token_entries[matched].token == tokens[token_offset + matched])
        ++matched;
      if (matched == 0) break;
      tip = std::move(child);
      token_offset += matched;
      if (matched != edge.token_count()) break;
    }
    // No cached edge can need restoration. A valid source tip pins a resident,
    // ready predecessor halo; matching at least one cached token is the only
    // way this request can enter an older reclaimed or invalidated branch.
    if (token_offset == 0) return {};
    if (tip->parent_edge.is_empty()) return {};
    int64_t const margin = kv_reclamation_margin();
    TRON_ASSERT_LE(
        token_offset, std::numeric_limits<size_t>::max() - from_node->abs_ht.i);
    size_t const matched_end = from_node->abs_ht.i + token_offset;
    TRON_ASSERT_LE(
        matched_end, static_cast<size_t>(std::numeric_limits<int64_t>::max()));
    size_t const initial_demand =
        token_offset < tokens.size() ? matched_end : matched_end - 1;

    TRON_ASSERT(next_kv_restore_attempt_ != std::numeric_limits<uint64_t>::max(),
        "KV restore attempt overflow");
    uint64_t const attempt = next_kv_restore_attempt_++;
    reclaimed_kv_restore restore;
    bool restored_any = false;
    bool required_any = false;
    bool const restored_all = walk_required_kv_restores(
        tip, from_node->abs_ht.i, matched_end, initial_demand, margin, attempt,
        [&](book_path_segment const&, book& candidate) noexcept {
          if (!restore.pinned_tip) {
            tip->_pin_locked();
            restore.pinned_tip = tip;
          }
          std::optional<int64_t> bytes =
              candidate.restore_reclaimable_kv_storage(attempt);
          if (!bytes) return false;
          TRON_ASSERT_GT(*bytes, 0);
          restored_any = true;
          return true;
        },
        required_any);

    if (!restored_all) {
      bool rollback_required = false;
      bool const rollback_complete = walk_required_kv_restores(
          tip, from_node->abs_ht.i, matched_end, initial_demand, margin, attempt,
          [&](book_path_segment const&, book& candidate) noexcept {
            if (candidate.reclaimable_kv_restore_attempt() == attempt) {
              int64_t const released = candidate.abort_reclaimable_kv_restore(attempt);
              TRON_ASSERT_GT(released, 0);
            }
            return true;
          },
          rollback_required);
      TRON_ASSERT(rollback_complete && rollback_required,
          "KV restore rollback could not reconstruct its attempt");
      restore.result = reclaimed_kv_restore_result::failed;
      return restore;
    }

    if (!restored_any) {
      TRON_ASSERT(!required_any, "KV restore requirement allocated no arena");
      return {};
    }
    TRON_ASSERT(restore.pinned_tip, "Prepared KV restore has no path pin");
    restore.result = reclaimed_kv_restore_result::prepared;
    restore.attempt = attempt;
    restore.matched_begin = from_node->abs_ht.i;
    restore.matched_end = matched_end;
    restore.initial_demand = initial_demand;
    restore.margin = margin;
    return restore;
  }

  void abort_reclaimed_kv_restore(reclaimed_kv_restore& restore) noexcept override {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "abort_reclaimed_kv_restore without tree_lock");
    TRON_ASSERT(restore.result == reclaimed_kv_restore_result::prepared &&
                    restore.pinned_tip && restore.attempt != 0,
        "Aborting an inactive KV restore");
    std::shared_ptr<node_t> tip = follow_tombstones<book>(restore.pinned_tip);
    TRON_ASSERT(tip, "KV restore path disappeared before abort");
    bool abort_required = false;
    bool const abort_complete = walk_required_kv_restores(
        tip, restore.matched_begin, restore.matched_end, restore.initial_demand,
        restore.margin, restore.attempt,
        [&](book_path_segment const&, book& candidate) noexcept {
          if (candidate.reclaimable_kv_restore_attempt() == restore.attempt) {
            int64_t const released =
                candidate.abort_reclaimable_kv_restore(restore.attempt);
            TRON_ASSERT_GT(released, 0);
          }
          return true;
        },
        abort_required);
    TRON_ASSERT(abort_complete && abort_required,
        "KV restore abort could not reconstruct its attempt");
    restore.result = reclaimed_kv_restore_result::unchanged;
    restore.attempt = 0;
  }

  void commit_reclaimed_kv_restore(reclaimed_kv_restore& restore) noexcept override {
    TRON_ASSERT(tron::tree_lock_held_by_this_thread(),
        "commit_reclaimed_kv_restore without tree_lock");
    TRON_ASSERT(restore.result == reclaimed_kv_restore_result::prepared &&
                    restore.pinned_tip && restore.attempt != 0,
        "Committing an inactive KV restore");
    std::shared_ptr<node_t> tip = follow_tombstones<book>(restore.pinned_tip);
    TRON_ASSERT(tip, "KV restore path disappeared before commit");
    bool published_any = false;
    bool publish_required = false;
    bool const published_all = walk_required_kv_restores(
        tip, restore.matched_begin, restore.matched_end, restore.initial_demand,
        restore.margin, restore.attempt,
        [&](book_path_segment const& segment, book& candidate) noexcept {
          if (candidate.reclaimable_kv_restore_attempt() != restore.attempt)
            return true;
          int64_t const restored = candidate.reclaimable_kv_storage_bytes();
          note_book_storage_delta(restored, segment.anchor->used());
          invalidate_restored_book(segment.anchor, restore.attempt);
          candidate.finish_reclaimable_kv_restore(restore.attempt);
          metrics.kv_reclamation_books_restored.fetch_add(1, std::memory_order_relaxed);
          metrics.kv_reclamation_bytes_restored.fetch_add(
              restored, std::memory_order_relaxed);
          note_kv_reclamation_restore(restored);
          published_any = true;
          return true;
        },
        publish_required);
    TRON_ASSERT(published_all && publish_required && published_any,
        "KV restore publication could not reconstruct its attempt");
    metrics.kv_reclamation_restoration_requests.fetch_add(1, std::memory_order_relaxed);
    note_kv_reclamation_request();
    restore.result = reclaimed_kv_restore_result::unchanged;
    restore.attempt = 0;
  }

  void reclaim_out_of_window_kv() noexcept override {
    TRON_ASSERT(
        tree_lock_held_by_this_thread(), "reclaim_out_of_window_kv without tree_lock");
    size_t const window = active_reclaimable_window_size;
    if (window == 0 || is_speculator || is_eagle) return;
    int64_t const margin = kv_reclamation_margin();

    std::vector<std::shared_ptr<node_t>> pending{root};
    while (!pending.empty() && memory_pressure_requires_reclamation()) {
      auto tip = std::move(pending.back());
      pending.pop_back();
      auto direct_pins = tip->subtree_pins;
      for (auto const& [token, weak_child] : tip->children) {
        if (auto child = weak_child.lock()) {
          TRON_ASSERT_GE(direct_pins, child->subtree_pins);
          direct_pins -= child->subtree_pins;
          if (child->subtree_pins != 0) pending.push_back(std::move(child));
        }
      }
      if (direct_pins == 0 || tip->parent_edge.is_empty() || !book_path_is_ready(tip))
        continue;
      // Saved client/listener positions survive appends and splits. Unknown
      // pins (including provisional restoration) keep the conservative bound.
      auto const tip_book = inspect_book_path(tip);
      auto const position = direct_pins == tip->subtree_pins
                                ? tip->earliest_direct_pin_position_locked(
                                      static_cast<size_t>(direct_pins))
                                : std::nullopt;
      size_t const query_begin =
          position ? position->i : tip_book.anchor->parent_edge.parent->abs_ht.i;
      scan_reclamation_boundary(
          tip, tip, detail::checked_kv_position(query_begin), margin);
    }
  }

  // Validation function for KV book consistency with multi-token edges
  // Only used in unit test.
  void validate_kv_books() const override {
    struct book_info {
      std::vector<std::pair<size_t, size_t>> used_ranges;  // (start, end) pairs
      size_t max_used_token = 0;
    };
    std::unordered_map<book*, book_info> book_usage;

    // Traverse tree and collect all token ranges
    std::function<void(node_t*)> traverse = [&](node_t* n) {
      if (!n || n->parent_edge.is_empty()) return;

      auto& edge = n->parent_edge;
      if (edge.kv_book != nullptr && n->used()) {
        auto* book_ptr = edge.kv_book.get();
        auto& info = book_usage[book_ptr];

        size_t start = edge.kv_first_entry_nr;
        size_t end = edge.kv_last_entry_nr();
        info.used_ranges.push_back({start, end});
        info.max_used_token = std::max(info.max_used_token, end);
      }

      for (auto& [token, weak_child] : n->children) {
        if (auto child = weak_child.lock()) {
          auto valid_child = follow_tombstones(child);
          if (valid_child) {
            traverse(valid_child.get());
          }
        }
      }
    };

    traverse(root.get());

    // Validate each book
    for (auto& [book_ptr, info] : book_usage) {
      // Sort ranges by start index (lexicographical sort of pairs does this)
      std::sort(info.used_ranges.begin(), info.used_ranges.end());

      if (!info.used_ranges.empty()) {
        TRON_ASSERT(info.used_ranges[0].first == 0, "Book used ranges must start at 0");
        // Check for overlapping ranges and gaps
        // Note: .second is inclusive (kv_last_entry_nr), so +1 for contiguity check
        for (size_t i = 1; i < info.used_ranges.size(); ++i) {
          TRON_ASSERT(info.used_ranges[i - 1].second + 1 == info.used_ranges[i].first,
              "Discontiguous token ranges in KV book (gap or overlap)");
        }
      }

      // Validate book's tok_ct
      // Note: tok_ct might be higher than max_used_token if there are unused
      // nodes at the end, which is fine
      TRON_ASSERT(info.max_used_token <= book_ptr->size() - 1,
          "Used token beyond book's tok_ct");
    }
  }
};
#endif  // TRON_SCHEDULER_RUNTIME_ONLY

/*
 * @brief Wait for all outstanding work to be completed.
 *
 * Before allowing work to continue, call the callback.
 *
 * @param cb The callback to call after all outstanding work is completed,
 * before allowing work to continue.
 */
void work_barrier(std::function<void()> cb);

#ifndef TRON_SCHEDULER_RUNTIME_ONLY
// Declare extern template instantiations of full_scheduler<> for each model.
// The definition in models_x.hpp must match this declaration.
#define TRON_PLUGIN(type, exec)                                                        \
  extern template struct full_scheduler<model<tron::named_models::type##_##exec>>;

#include "tron/model-definitions.i"

#undef TRON_PLUGIN
#endif  // TRON_SCHEDULER_RUNTIME_ONLY

}  // namespace tron

