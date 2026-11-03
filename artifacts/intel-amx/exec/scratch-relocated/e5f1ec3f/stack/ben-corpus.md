
# PR 3879: 13 inline, 2 review bodies, 0 issue comments

## review 5116532748 CHANGES_REQUESTED 2026-09-04T18:56:33Z
In general I'm a bit surprised that we are giving this such a general name given that it is really a kernel implementing one very specific attention shape. I feel future us and, especially, newcomers to the codebase, will feel this in the future and it really seems like we should be more forward-looking.

Similarly, referring the K mirror as just the "mirror" is setting us up for confusion. This state is very specifically present to serve the the 128x4 AMX attention kernel. we should at least call it `amx_k_mirror` or similar to make that clear to the reader. The attention kernel is already non-trivial to reason about; I am worried that if we aren't careful it will become nearly impossible for a newcomer to wade into.

I trust that the AMX kernel itself is sound and didn't look too carefully at the math itself.

## review 5198888443 APPROVED 2026-09-14T14:25:46Z
This looks good. Thanks for your patience and refactoring, @jhan-positron !

## inline 3936807517 2026-09-04T18:19:46Z h/tron/kernels/amx_attn_iface.hpp:39 (reply_to None)
```
+//   3. process runtime: available() = CPUID 7.0 EDX bits 22 (AMX-BF16) +
+//      24 (AMX-TILE), XCR0[18:17] (OS tile state), and
+//      arch_prctl(ARCH_REQ_XCOMP_PERM) - a per-PROCESS grant (Linux xstate
+//      rules); result cached. Non-AMX hosts (including AMD: feature bits,
+//      not vendor strings) run the AVX path.
+//   4. kill switch: TRON_AMX_DISABLE=1 forces available() false - used for
```
I will offer my usual complaint when it comes to environment variables: where is this documented other than the source? This sort of thing is incredibly poor in discoverability and ultimately either we should have be better way to expose the configuration surface (e.g. a command-line flag) or document these variables centrally.

## inline 3936847383 2026-09-04T18:25:01Z h/tron/kernels/page_share_counters.hpp:27 (reply_to None)
```
+inline std::atomic<uint64_t> width_hist[7];
+inline std::atomic<uint64_t> page_visits;     // total (page, kv_head) visits
+inline std::atomic<uint64_t> visible_tokens;  // sum of n_visible = work weight
+inline std::atomic<uint64_t> shared_visits;   // visits with n_visible >= 2
+inline std::atomic<uint64_t> shared_tokens;   // work weight on shared visits
+inline std::atomic<uint64_t> pending_visits;  // visits in the pending phase
```
Why are these global `inline`? What is this supposed to do? I would have thought these would be `extern`.

## inline 3936949728 2026-09-04T18:38:00Z h/tron/models/self_attention.hpp:1369 (reply_to None)
```
+      // buffer contract (vector routes over-aligned elements through the
+      // aligned operator new).
+      struct alignas(64) amx_qpack_slot {
+        uint16_t v[amx_attn::Q_PACK_ELEMS_2048];
+      };
+      thread_local std::vector<amx_qpack_slot> amx_qpack;
```
If I'm not mistaken, this is going to result in a runtime allocation. Usually this is frowned upon but the facts that

1. it's `thread_local`
2. attention workers are a long-lived pool
3. batch sizes are bounded

collectively mean that this allocation will be amortized over many operations, which makes it probably okay.

Still, I do wonder why we don't just handle this consistently with the other intermediates needed by attention and attach it to `attn_accum`. Moreover, we know `max_minibatch_size` statically so surely this should just be an `array`.

## inline 3936963481 2026-09-04T18:39:58Z h/tron/models/self_attention.hpp:1451 (reply_to None)
```
+                amx_packed_mask[batch_job_ix >> 6] |= 1ull << (batch_job_ix & 63);
+              }
+              amx_qp = q_packed;
+            }
+          }
+#endif
```
Can we not move this out into a distinct helper? This function is already coming up on 200 LoC; let's not make a bad situation even worse.

## inline 3936968255 2026-09-04T18:40:37Z h/tron/models/self_attention.hpp:1374 (reply_to None)
```
+      thread_local std::vector<amx_qpack_slot> amx_qpack;
+      // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
+      // is already packed into amx_qpack": word batch_job_ix / 64, bit
+      // batch_job_ix % 64. Sized for the largest legal minibatch
+      // (items.size() <= max_minibatch_size).
+      uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
```
Why not use `mask_t` here?

## inline 3936986164 2026-09-04T18:43:09Z h/tron/models/self_attention.hpp:1505 (reply_to None)
```
         token_job_id job_ix,
         const token_range* range_hint,
         int sliding_window_size,
-        bool run_visible_in_software) {
+        bool run_visible_in_software,
+        const uint16_t* amx_q_packed = nullptr) {
```
The surgery in this function is quite brutal, leading to essentially two distinct control flow paths. This suggests to me that there should be two distinct functions, possibly with commonalities factored out into helpers.

## inline 3937013971 2026-09-04T18:47:04Z src/tron/kernels/amx_attn.cpp:17 (reply_to None)
```
+#include "tron/kernels/amx_attn_iface.hpp"
+
+#ifndef ARCH_REQ_XCOMP_PERM
+#define ARCH_REQ_XCOMP_PERM 0x1023
+#endif
+#define XFEATURE_XTILEDATA 18
```
These syscall constants deserve a short comment.

## inline 3937077542 2026-09-04T18:56:01Z h/tron/models/kv_cache.hpp:487 (reply_to None)
```
   int64_t new_bytes = old_bytes + delta_bytes;
-  if (std::abs(new_bytes - last_print_bytes.load(std::memory_order_release)) <
-      granularity)
+  int64_t new_mirror = old_mirror + delta_mirror_bytes;
+  if (std::abs(new_bytes + new_mirror -
+               last_print_bytes.load(std::memory_order_release)) < granularity)
```
I know you didn't write this but what is this memory order doing here? AFAIK release on a load has absolutely no use.

## inline 3937150401 2026-09-04T19:06:54Z h/tron/kernels/page_share_counters.hpp:27 (reply_to 3936847383)
```
+inline std::atomic<uint64_t> width_hist[7];
+inline std::atomic<uint64_t> page_visits;     // total (page, kv_head) visits
+inline std::atomic<uint64_t> visible_tokens;  // sum of n_visible = work weight
+inline std::atomic<uint64_t> shared_visits;   // visits with n_visible >= 2
+inline std::atomic<uint64_t> shared_tokens;   // work weight on shared visits
+inline std::atomic<uint64_t> pending_visits;  // visits in the pending phase
```
Looking at this again, it appears that this is a C++17 feature. Sigh, leave it to the C++ standards committee to inexplicably reuse a perfectly sensible keyword.

## inline 3937239431 2026-09-04T19:19:16Z h/tron/models/self_attention.hpp:1419 (reply_to None)
```
@@ -1368,10 +1416,46 @@ struct self_attention {
           token_scratchpad_ref<geometry> sp =
               token_scratchpad_ref_at<geometry>(scratchpad, batch_job_ix);
           bool was_valid = sp.is_valid_for(kv_head);
+          const uint16_t* amx_qp = nullptr;
```
Isn't this `tron::bf16`?

## inline 3973407196 2026-09-09T22:01:45Z h/tron/models/self_attention.hpp:1451 (reply_to 3936963481)
```
+                amx_packed_mask[batch_job_ix >> 6] |= 1ull << (batch_job_ix & 63);
+              }
+              amx_qp = q_packed;
+            }
+          }
+#endif
```
Thank you for the refactoring! This looks better; let's just make sure that we shouldn't be handling `range_hint` in the AMX path as well.

## inline 3973410716 2026-09-09T22:02:12Z h/tron/models/self_attention.hpp:1369 (reply_to 3936949728)
```
+      // buffer contract (vector routes over-aligned elements through the
+      // aligned operator new).
+      struct alignas(64) amx_qpack_slot {
+        uint16_t v[amx_attn::Q_PACK_ELEMS_2048];
+      };
+      thread_local std::vector<amx_qpack_slot> amx_qpack;
```
I'm still not convinced that this couldn't (and, indeed, shouldn't) live in `attn_accum`. Let's figure out whether this is really the case.

## inline 3991475816 2026-09-11T16:54:35Z h/tron/models/self_attention.hpp:289 (reply_to None)
```
+      // The AMX QK kernel cannot read a token's 4 query heads as they are
+      // stored; it needs them copied to its tile layout (a "pack"). Element
+      // batch_job_ix of this vector is the pack of the token at position
+      // batch_job_ix of the minibatch, so the vector is indexed like the
+      // arrays above.
+      std::vector<amx_qpack_slot> amx_qpack;
```
While technically this could rather be a statically-sized `std::array` I suppose `vector` is defensible given that we may not use this storage at all. A single allocation seems like a fine trade-off.

# PR 4424: 1 inline, 1 review bodies, 1 issue comments

## review 5270587330 COMMENTED 2026-09-21T18:53:47Z
I do wonder whether we can't better encapsulate the VNNI representation. Specifically, my concern is that there are a lot of pointers floating around currently that provide no hints as to the layout of the data to which they point.

I think the way I would approach this is to follow the precedent already present in `tron`: we currently have types like `tensor` and `dtensor` which provide a uniform interface based upon `expr`. This allows us to very naturally talk about tensors of various types and convert/slice/compute them freely. Perhaps we could follow this same model:

* Introduce a `vnni_tensor` type which represents a VNNI-packed, rank-2 tensor
* Give that type the usual operations that we expect of `tensor` types and, in particular, the row-wise load/store operations that we need here.

The key here is that we really don't want `bf16_t*` values floating around without any indication of how they are laid out.

## issue comment 5765866077 2026-09-21T18:58:31Z
On discussing this with our overlords, Claude and I came up with the following straw-man (FWIW, I'm not entirely convinced of the necessity of separate `k_vnni_layout` from `vnni_view` but regardless, it's a starting point):

I would separate **layout**, **storage**, and **views**. The layout defines the byte mapping; storage owns those bytes; views carry their type into kernels.

Below is an API sketch, not a compiled implementation.

## 1. Layouts describe the existing representations

Both use logical coordinates `(token, dimension)`. Their physical mappings differ.

```cpp
// h/tron/tensor/vnni.hpp

template <size_t Tokens, size_t Dims>
struct k_vnni_layout {
  static_assert(Tokens > 0 && Tokens % 16 == 0);
  static_assert(Dims > 0 && Dims % 32 == 0);

  static constexpr size_t tokens = Tokens;
  static constexpr size_t dims = Dims;
  static constexpr size_t elements = Tokens * Dims;

  static constexpr size_t offset(size_t token, size_t dim) noexcept {
    const size_t step = dim / 32;
    const size_t block = token / 16;
    const size_t pair = (dim % 32) / 2;
    const size_t lane = token % 16;

    return ((((step * (Tokens / 16) + block) * 16 + pair)
                * 16 + lane)
               * 2)
           + dim % 2;
  }
};

template <size_t Tokens, size_t Dims>
struct v_vnni_layout {
  static_assert(Tokens > 0 && Tokens % 2 == 0);
  static_assert(Dims > 0);

  static constexpr size_t tokens = Tokens;
  static constexpr size_t dims = Dims;
  static constexpr size_t elements = Tokens * Dims;

  static constexpr size_t offset(size_t token, size_t dim) noexcept {
    return (token / 2) * (2 * Dims) + 2 * dim + token % 2;
  }
};
```

These restrictions describe storage. Kernels can impose stricter restrictions. For example, representing `k_vnni_layout<128, 256>` would not imply that the current AMX kernel supports it.

## 2. A view carries layout and constness

```cpp
template <typename Layout>
class vnni_tensor;

namespace detail {
struct vnni_access;
}

template <typename T, typename Layout>
class vnni_view {
  static_assert(std::same_as<std::remove_const_t<T>, bf16>);

 public:
  using layout_type = Layout;

  static constexpr size_t tokens = Layout::tokens;
  static constexpr size_t dims = Layout::dims;

  // Permit mutable-to-const conversion only.
  template <typename U>
    requires(std::is_const_v<T> && std::same_as<U, bf16>)
  vnni_view(vnni_view<U, Layout> other) noexcept
      : data_(other.data_) {}

  T& at(size_t token, size_t dim) const noexcept {
    TRON_ASSERT_LT(token, tokens);
    TRON_ASSERT_LT(dim, dims);
    return data_[Layout::offset(token, dim)];
  }

 private:
  explicit vnni_view(T* data) noexcept : data_(data) {}

  T* data_;

  template <typename, typename>
  friend class vnni_view;
  friend class vnni_tensor<Layout>;
  friend struct detail::vnni_access;
};
```

The private constructor prevents routine callers from relabelling an arbitrary row-major pointer as packed data. Views normally come from typed storage.

There is no `data()`, pointer conversion, or `operator[]` that suggests a contiguous row. `at()` is useful for inspection and scalar access; hot paths use the bulk operations below.

As with `std::span`, a const view object does not make its elements const. `vnni_view<const bf16, Layout>` does.

## 3. Storage is an aligned array, not another allocation

```cpp
template <typename Layout>
class alignas(64) vnni_tensor {
 public:
  auto as_view() & noexcept {
    return vnni_view<bf16, Layout>{data_.data()};
  }

  auto as_view() const & noexcept {
    return vnni_view<const bf16, Layout>{data_.data()};
  }

  auto as_view() && = delete;
  auto as_view() const && = delete;

 private:
  std::array<bf16, Layout::elements> data_;
};
```

The implementation would preserve the cache’s existing initialization policy. In particular, introducing this class must not remove V’s zero-initialization invariant or add implicit clearing to hot allocation paths.

The page arena must construct the actual storage type. We should not obtain “typed storage” by casting an existing SIMD array to `vnni_tensor*`.

## 4. Bulk operations preserve the optimized paths

Use overloads for the two layouts, rather than a generic scalar loop in the hot path:

```cpp
template <size_t Tokens, size_t Dims>
void store_row(
    vnni_view<bf16, k_vnni_layout<Tokens, Dims>> dst,
    size_t token,
    std::span<const bf16, Dims> src) noexcept;

template <size_t Tokens, size_t Dims>
void load_row(
    vnni_view<const bf16, k_vnni_layout<Tokens, Dims>> src,
    size_t token,
    std::span<bf16, Dims> dst) noexcept;

// Corresponding overloads for v_vnni_layout.
```

For K, these contain the existing scatter/gather implementation. A typed `store_block()` retains the existing masked 16-token transpose/store path.

For V, the overloads contain the existing interleave/deinterleave operations, including the required BF16, FP16, and float conversions.

The layout header need not include attention kernels. Physical-address access stays in a small internal helper used by SIMD and AMX implementations:

```cpp
namespace detail {
struct vnni_access {
  template <typename T, typename Layout>
  static T* packed_data(vnni_view<T, Layout> view) noexcept {
    return view.data_;
  }
};
}
```

This is an explicit internal escape hatch, not an absolute access-control boundary. Ordinary cache and attention code should not use it.

## 5. Type the cache storage and kernel boundaries

Conceptually, `kv_block` selects its storage at compile time:

```cpp
using k_storage = std::conditional_t<
    k_vnni::layout_on<head_size>,
    vnni_tensor<k_vnni_layout<page_size, head_size>>,
    existing_row_major_k_storage>;

k_storage k;
```

The V selection follows the existing `TRON_CHUNK_SIZE` condition. Both packed and unpacked configurations retain their current bytes and alignment.

Page accessors then return typed views:

```cpp
auto k_packed(kv_slot_id slot, size_t head) const noexcept {
  return kv_block<geometry>(slot, head).k.as_view();
}
```

Kernel signatures state precisely what they accept:

```cpp
using packed_k_page =
    vnni_view<const bf16, k_vnni_layout<64, 128>>;

using packed_v_page =
    vnni_view<const bf16, v_vnni_layout<64, 128>>;

void qk_vnni_128x4(
    packed_k_page k,
    const bf16* q_rows,
    /* output arguments */) noexcept;

void weights_times_v_128x4(
    packed_v_page v,
    /* weight and output arguments */) noexcept;
```

The AVX-512 fallback also takes `packed_k_page`. Internally, kernels extract the pointer once and retain the existing instruction sequence.

Consequently:

```cpp
qk_vnni_128x4(page.k_packed(...), ...);  // OK
qk_vnni_128x4(page.v_packed(...), ...);  // Compile error
qk_vnni_128x4(row_major_pointer, ...);   // Compile error
```

## inline 4065141577 2026-09-21T18:24:52Z ingest/src/TronCpp.hs:2338 (reply_to None)
```
+  AttentionStmt attention -> case attentionKvWrite attention of
+    Nothing -> []
+    Just kvWrite ->
+      withTrace stmt $
+        attentionRuntimeCall
+          "save_k_helper"
```
Why do we need to introduce a new function for this? Why not simply extend `save_k` itself with a `worker_ix` argument and call it consistently from both the main thread and the helpers?

# PR 4557: 9 inline, 1 review bodies, 0 issue comments

## review 5352791816 CHANGES_REQUESTED 2026-09-29T14:56:29Z
Looks good. Just a few minor tweaks needed.

## inline 4133613638 2026-09-29T12:47:21Z h/tron/tensor/kv_cache_fwd.hpp:25 (reply_to None)
```
+struct const_view;
+
+// Values for the aligned and dma template flags of view and const_view
+// (view.hpp, and views.hpp for the dma flag).
+inline constexpr bool VIEW_ALIGNED_TRUE = true;
+inline constexpr bool VIEW_DMA_FALSE = false;
```
A better solution for naming these may just be to make the arguments proper `enum`s.

## inline 4133643149 2026-09-29T12:50:33Z h/tron/tensor/v_vnni.hpp:31 (reply_to None)
```
+#include "tron/simd/types.hpp"
+#include "tron/tensor/kv_cache_fwd.hpp"
+#include "tron/tensor/seq.hpp"
+#include "tron/tensor/view.hpp"
+
+// Note [Packed V layout]
```
Can we rename this to say VNNI:


```suggestion
// Note [VNNI Packed V layout]
```

## inline 4133772400 2026-09-29T13:04:19Z h/system/memory.hpp:175 (reply_to None)
```
+// memory it returns ([intro.object]). The objects created are the ones the
+// program goes on to use. This covers implicit-lifetime types only ([class.prop]):
+// for example scalars, arrays, and classes with a trivial constructor and
+// destructor. dma_allocate_aligned is an ordinary function, so its memory holds
+// no objects. So try_make_unique_dma_for_overwrite gets its memory through the
+// wrapper below. The wrapper writes no bytes.
```
I'm not sure I understand what Claude is trying to say here. Can you clarify?

## inline 4133869073 2026-09-29T13:14:23Z h/system/memory.hpp:175 (reply_to 4133772400)
```
+// memory it returns ([intro.object]). The objects created are the ones the
+// program goes on to use. This covers implicit-lifetime types only ([class.prop]):
+// for example scalars, arrays, and classes with a trivial constructor and
+// destructor. dma_allocate_aligned is an ordinary function, so its memory holds
+// no objects. So try_make_unique_dma_for_overwrite gets its memory through the
+// wrapper below. The wrapper writes no bytes.
```
Alright, reading again I think I am beginning to see. It looks like Claude is (rightly) playing language lawyer. The C++ spec states that an implicitly-created object's  (that is, one not introduced by a `new` expression) lifetime must begin in an `operator new`. Consequently, the previous implementation was strictly-speaking incorrect: it allocated storage but failed to actually begin the lifetime of the object residing in that storage.

Previously this was perhaps okay since the storage held POD, but now it contains a `v_vnni_tensor`, requiring that we be a bit more careful.

I think it would be good to reword the Note more clearly.

## inline 4134028988 2026-09-29T13:30:28Z h/tron/models/kv_cache.hpp:1462 (reply_to None)
```
+  // kv_block that lives there ([expr.static.cast], [basic.life], [ptr.launder]).
+  //
+  // Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr
+  // steps through V with vector pointers, fill_storage_slot walks one bf16
+  // pointer across K and V, and the 8-lane V accessors read the bf16s (SIMD
+  // vector) array v as bf16 values.
```
Oof, this seems unfortunate. We should open a ticket to fix this. Leaving the bounds of the specified language is fraught with peril, especially in a language filled with as many sharp edges as C++

## inline 4134076112 2026-09-29T13:35:11Z h/tron/tensor/v_vnni.hpp:104 (reply_to None)
```
+// Only v_vnni_view::operator[] constructs rows. A row keeps its pair address
+// and parity by value. So a row stays usable after the matrix view it came from
+// is gone, for as long as the owner lives. A const row (or a row of const bf16)
+// yields read-only elements.
+template <typename T, size_t Cols>
+struct v_vnni_row final : expr<v_vnni_row<T, Cols>, Cols> {
```
It is a bit unfortunate that we grow this 100 LoC without any obvious users, but on the other hand it does seem useful.

## inline 4134925164 2026-09-29T14:56:08Z h/tron/scheduler/full.hpp:2764 (reply_to None)
```
                       pg_ptr->template get_v<model_t::hardware_attention_geometry.kv>(
-                          slot, kv_head, off, dest);
+                          slot, kv_head, off,
+                          view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,
+                              seq<model_t::hardware_attention_geometry.kv.head_size>,
+                              sseq<1>>{dest});
```
This is a rather subtle pattern that is repeated quite a few times. I have opened #4697 to deduplicate this. Feel free to merge or adapt to taste.

## inline 4134933234 2026-09-29T14:56:56Z h/tron/tensor/kv_cache_fwd.hpp:25 (reply_to 4133613638)
```
+struct const_view;
+
+// Values for the aligned and dma template flags of view and const_view
+// (view.hpp, and views.hpp for the dma flag).
+inline constexpr bool VIEW_ALIGNED_TRUE = true;
+inline constexpr bool VIEW_DMA_FALSE = false;
```
To be clear, I don't consider this to be a blocker. It would make a good follow-up, however.

## inline 4158908727 2026-10-01T18:21:11Z h/tron/tensor/kv_cache_fwd.hpp:25 (reply_to 4133613638)
```
+struct const_view;
+
+// Values for the aligned and dma template flags of view and const_view
+// (view.hpp, and views.hpp for the dma flag).
+inline constexpr bool VIEW_ALIGNED_TRUE = true;
+inline constexpr bool VIEW_DMA_FALSE = false;
```
Absolutely, let's do this in a follow-up.
